import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.supplier import Supplier
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ActorType, EventType
from app.schemas.bid import BidCreate, RankedBidItem, RFQRankingResponse
from app.schemas.supplier import SupplierResponse
from app.schemas.auction import AuctionListItemResponse, AuctionDetailFullResponse
from app.schemas.rfq import RFQItemResponse
from app.schemas.buyer import BuyerResponse
from app.schemas.activity_log import ActivityLogResponse
from app.services.extension_service import evaluate_and_apply_extension

logger = logging.getLogger(__name__)


def create_bid(db: Session, bid_in: BidCreate, event_time: Optional[datetime] = None) -> Bid:
    """
    Atomically creates and records a supplier bid against an RFQ within a single database transaction.

    Workflow:
    1. Validates that the target RFQ exists.
    2. Validates that the RFQ is eligible for bidding.
    3. Validates that the bidding Supplier exists.
    4. If rfq_item_id is provided, validates that it belongs to the target RFQ.
    5. Retrieves (with row-level lock) or initializes the associated Auction and active AuctionRound.
    6. Validates auction lifecycle timing (before start_time, after forced_close, after close).
    7. Checks for existing duplicate bid for this supplier on this RFQ's auction.
    8. Captures current supplier rankings before the new bid is registered.
    9. Creates and flushes the Bid record with positive amount.
    10. Computes updated rankings and evaluates British Auction automatic time extension.
    11. If qualifying trigger occurs in the trigger window, updates auction close time (capped at forced close).
    12. Records ActivityLog events.
    13. Commits the transaction atomically or rolls back on failure.
    """
    # 1. Verify RFQ exists
    rfq = db.query(RFQ).filter(RFQ.id == bid_in.rfq_id).first()
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with id '{bid_in.rfq_id}' not found",
        )

    # 2. Verify RFQ status eligibility
    if rfq.status in [RFQStatus.CLOSED, RFQStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RFQ is not eligible for bidding (status: {rfq.status})",
        )

    # 3. Verify Supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == bid_in.supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with id '{bid_in.supplier_id}' not found",
        )

    # 4. Validate rfq_item_id if provided
    if bid_in.rfq_item_id is not None:
        item = (
            db.query(RFQItem)
            .filter(
                RFQItem.id == bid_in.rfq_item_id,
                RFQItem.rfq_id == rfq.id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RFQ item with id '{bid_in.rfq_item_id}' not found for this RFQ",
            )

    try:
        # 5. Retrieve or initialize Auction (locked FOR UPDATE to avoid race condition during rank calculation)
        auction = (
            db.query(Auction)
            .filter(Auction.rfq_id == rfq.id)
            .with_for_update()
            .first()
        )
        if not auction:
            auction = Auction(
                rfq_id=rfq.id,
                status=AuctionStatus.LIVE,
                current_round=1,
            )
            db.add(auction)
            db.flush()

        # Retrieve or initialize active AuctionRound
        current_round = (
            db.query(AuctionRound)
            .filter(
                AuctionRound.auction_id == auction.id,
                AuctionRound.round_number == auction.current_round,
            )
            .first()
        )
        if not current_round:
            current_round = AuctionRound(
                auction_id=auction.id,
                round_number=auction.current_round,
                status=AuctionRoundStatus.ACTIVE,
            )
            db.add(current_round)
            db.flush()

        # 6. Validate Auction Lifecycle & Timing
        if isinstance(event_time, datetime):
            event_dt = event_time.replace(tzinfo=timezone.utc) if event_time.tzinfo is None else event_time
        else:
            event_dt = datetime.now(timezone.utc)

        if auction.status in [AuctionStatus.CLOSED, AuctionStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auction is not eligible for bidding (status: {auction.status})",
            )

        # Before Start Time
        if auction.start_time is not None:
            start_dt = auction.start_time.replace(tzinfo=timezone.utc) if auction.start_time.tzinfo is None else auction.start_time
            if event_dt < start_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction has not started yet. Bidding is not accepted before start time.",
                )

        # After Forced Close Time
        if auction.forced_bid_close_time is not None:
            forced_dt = auction.forced_bid_close_time.replace(tzinfo=timezone.utc) if auction.forced_bid_close_time.tzinfo is None else auction.forced_bid_close_time
            if event_dt > forced_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction has closed. Bidding is not accepted after forced close time.",
                )

        # After Current Close Time
        if auction.end_time is not None:
            end_dt = auction.end_time.replace(tzinfo=timezone.utc) if auction.end_time.tzinfo is None else auction.end_time
            if event_dt > end_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction has closed. Bidding is not accepted after bid close time.",
                )

        # Auto-activate scheduled auction when live bidding begins
        if auction.status == AuctionStatus.SCHEDULED:
            auction.status = AuctionStatus.LIVE
            if current_round.status == AuctionRoundStatus.PENDING:
                current_round.status = AuctionRoundStatus.ACTIVE

        # 7. Check for existing duplicate bid for this supplier on this RFQ's auction
        existing_bid = (
            db.query(Bid)
            .filter(
                Bid.auction_id == auction.id,
                Bid.supplier_id == supplier.id,
            )
            .first()
        )
        if existing_bid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with id '{supplier.id}' has already submitted a bid for this RFQ",
            )

        # 7. Capture previous ranking state before the new bid is registered
        prev_ranking_resp = get_rfq_bid_ranking(db, rfq.id)
        previous_rankings = prev_ranking_resp.rankings

        # 8. Create Bid record
        bid = Bid(
            auction_id=auction.id,
            round_id=current_round.id,
            supplier_id=supplier.id,
            amount=bid_in.amount,
            carrier_name=bid_in.carrier_name,
            freight_charges=bid_in.freight_charges,
            origin_charges=bid_in.origin_charges,
            destination_charges=bid_in.destination_charges,
            transit_time=bid_in.transit_time,
            validity_of_quote=bid_in.validity_of_quote,
            is_valid=True,
        )
        db.add(bid)
        db.flush()

        # 9. Compute updated ranking state after the new bid
        new_ranking_resp = get_rfq_bid_ranking(db, rfq.id)
        new_rankings = new_ranking_resp.rankings

        # 10. Evaluate and apply British Auction automatic time extension
        extended, new_close, ext_reason = evaluate_and_apply_extension(
            db=db,
            auction=auction,
            bid=bid,
            previous_rankings=previous_rankings,
            new_rankings=new_rankings,
            event_time=event_dt,
        )

        # 11. Create ActivityLog record for BID_SUBMITTED
        activity_log = ActivityLog(
            rfq_id=rfq.id,
            auction_id=auction.id,
            actor_type=ActorType.SUPPLIER,
            actor_id=supplier.id,
            event_type=EventType.BID_SUBMITTED,
            message=f"Bid of {bid.amount} {rfq.currency} submitted by supplier '{supplier.name}'",
            metadata_json={
                "bid_id": str(bid.id),
                "rfq_id": str(rfq.id),
                "supplier_id": str(supplier.id),
                "supplier_name": supplier.name,
                "amount": str(bid.amount),
                "carrier_name": bid_in.carrier_name,
                "freight_charges": str(bid_in.freight_charges) if bid_in.freight_charges is not None else None,
                "origin_charges": str(bid_in.origin_charges) if bid_in.origin_charges is not None else None,
                "destination_charges": str(bid_in.destination_charges) if bid_in.destination_charges is not None else None,
                "transit_time": bid_in.transit_time,
                "validity_of_quote": bid_in.validity_of_quote,
                "currency": rfq.currency,
                "rfq_item_id": str(bid_in.rfq_item_id) if bid_in.rfq_item_id else None,
                "round_number": current_round.round_number,
                "auction_extended": extended,
                "new_close_time": new_close.isoformat() if new_close else None,
            },
        )
        db.add(activity_log)

        # 12. Commit entire transaction atomically
        db.commit()

        # Eagerly load supplier relationship for response
        persisted_bid = (
            db.query(Bid)
            .options(
                joinedload(Bid.supplier),
                joinedload(Bid.auction),
            )
            .filter(Bid.id == bid.id)
            .first()
        )
        if not persisted_bid:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve persisted bid",
            )
        # Attach rfq_id and extension metadata for schema serialization
        persisted_bid.rfq_id = rfq.id
        persisted_bid.auction_end_time = auction.end_time
        persisted_bid.auction_extended = extended
        persisted_bid.extension_reason = ext_reason
        return persisted_bid

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating bid: {e}")
        orig_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {orig_msg}",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating bid: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the bid. The transaction was rolled back.",
        )


def get_bid_by_id(db: Session, bid_id: UUID) -> Bid:
    """
    Retrieve a Bid by UUID with supplier and auction details loaded.
    Raises HTTP 404 if not found.
    """
    bid = (
        db.query(Bid)
        .options(
            joinedload(Bid.supplier),
            joinedload(Bid.auction),
        )
        .filter(Bid.id == bid_id)
        .first()
    )
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid with id '{bid_id}' not found",
        )
    if bid.auction:
        bid.rfq_id = bid.auction.rfq_id
    return bid


def list_bids_for_rfq(db: Session, rfq_id: UUID) -> List[Bid]:
    """
    List all bids placed on auctions associated with a specific RFQ.
    """
    auction = db.query(Auction).filter(Auction.rfq_id == rfq_id).first()
    if not auction:
        return []

    bids = (
        db.query(Bid)
        .options(joinedload(Bid.supplier))
        .filter(Bid.auction_id == auction.id)
        .order_by(Bid.submitted_at.desc())
        .all()
    )
    for b in bids:
        b.rfq_id = rfq_id
    return bids


def get_rfq_bid_ranking(db: Session, rfq_id: UUID) -> RFQRankingResponse:
    """
    Calculates deterministic bid ranking for an RFQ based on valid submitted bids.

    Ranking rules:
    - Lowest bid amount = Rank 1 (ascending price ordering)
    - Deterministic tie-breaker:
        1. amount ASC
        2. submitted_at ASC (earlier submission prioritized)
        3. id ASC (stable UUID ordering)
    - Valid bids only (is_valid == True)
    - Sequential 1-based ranks (1, 2, 3, ...)
    - Scoped strictly to the target RFQ's auction
    """
    # 1. Verify that target RFQ exists (404 if non-existent)
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with id '{rfq_id}' not found",
        )

    # 2. Retrieve associated Auction
    auction = db.query(Auction).filter(Auction.rfq_id == rfq.id).first()
    if not auction:
        return RFQRankingResponse(
            rfq_id=rfq.id,
            rfq_title=rfq.title,
            currency=rfq.currency,
            baseline_price=rfq.baseline_price,
            total_bids=0,
            rankings=[],
        )

    # 3. Query all valid bids for the RFQ's auction ordered by amount ASC, submitted_at ASC, id ASC
    bids = (
        db.query(Bid)
        .options(joinedload(Bid.supplier))
        .filter(
            Bid.auction_id == auction.id,
            Bid.is_valid.is_(True),
        )
        .order_by(
            Bid.amount.asc(),
            Bid.submitted_at.asc(),
            Bid.id.asc(),
        )
        .all()
    )

    # 4. Assign sequential ranks (1..N) and construct response
    rankings: List[RankedBidItem] = []
    for rank_idx, bid in enumerate(bids, start=1):
        supplier_resp = None
        supplier_name = None
        supplier_company = None
        if bid.supplier:
            supplier_resp = SupplierResponse.model_validate(bid.supplier)
            supplier_name = bid.supplier.name
            supplier_company = bid.supplier.company_name

        rankings.append(
            RankedBidItem(
                rank=rank_idx,
                bid_id=bid.id,
                supplier_id=bid.supplier_id,
                supplier_name=supplier_name,
                supplier_company=supplier_company,
                amount=bid.amount,
                carrier_name=bid.carrier_name,
                freight_charges=bid.freight_charges,
                origin_charges=bid.origin_charges,
                destination_charges=bid.destination_charges,
                transit_time=bid.transit_time,
                validity_of_quote=bid.validity_of_quote,
                submitted_at=bid.submitted_at,
                is_valid=bid.is_valid,
                rfq_item_id=None,
                supplier=supplier_resp,
            )
        )

    return RFQRankingResponse(
        rfq_id=rfq.id,
        rfq_title=rfq.title,
        currency=rfq.currency,
        baseline_price=rfq.baseline_price,
        total_bids=len(rankings),
        rankings=rankings,
    )


def get_rfq_activity_logs(db: Session, rfq_id: UUID) -> List[ActivityLog]:
    """
    Retrieves all ActivityLog events associated with an RFQ or its Auction ordered by creation date desc.
    Raises HTTP 404 if the target RFQ does not exist.
    """
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with id '{rfq_id}' not found",
        )

    # Filter activity logs belonging to this RFQ or its Auction
    auction_id = rfq.auction.id if rfq.auction else None
    if auction_id:
        logs = (
            db.query(ActivityLog)
            .filter((ActivityLog.rfq_id == rfq.id) | (ActivityLog.auction_id == auction_id))
            .order_by(ActivityLog.created_at.desc())
            .all()
        )
    else:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.rfq_id == rfq.id)
            .order_by(ActivityLog.created_at.desc())
            .all()
        )
    return logs


def compute_auction_display_status(auction: Auction) -> str:
    """
    Calculates human-readable dynamic auction status: Active, Closed, Force Closed, Scheduled.
    """
    now = datetime.now(timezone.utc)
    if auction.status == AuctionStatus.CANCELLED:
        return "Cancelled"
    if auction.status == AuctionStatus.PAUSED:
        return "Paused"

    # 1. Forced close boundary check
    if auction.forced_bid_close_time:
        forced_t = (
            auction.forced_bid_close_time.replace(tzinfo=timezone.utc)
            if auction.forced_bid_close_time.tzinfo is None
            else auction.forced_bid_close_time
        )
        if now >= forced_t:
            return "Force Closed"
        if auction.end_time:
            end_t = (
                auction.end_time.replace(tzinfo=timezone.utc)
                if auction.end_time.tzinfo is None
                else auction.end_time
            )
            if end_t >= forced_t and (now >= end_t or auction.status == AuctionStatus.CLOSED):
                return "Force Closed"

    # 2. Standard close check
    if auction.end_time:
        end_t = (
            auction.end_time.replace(tzinfo=timezone.utc)
            if auction.end_time.tzinfo is None
            else auction.end_time
        )
        if now >= end_t or auction.status == AuctionStatus.CLOSED:
            return "Closed"

    # 3. Scheduled check
    if auction.start_time:
        start_t = (
            auction.start_time.replace(tzinfo=timezone.utc)
            if auction.start_time.tzinfo is None
            else auction.start_time
        )
        if now < start_t and auction.status == AuctionStatus.SCHEDULED:
            return "Scheduled"

    return "Active"


def list_auctions(db: Session, skip: int = 0, limit: int = 100) -> List[AuctionListItemResponse]:
    """
    Lists all British Auctions with real RFQ details, current lowest bid, countdown timers, and dynamic status.
    """
    auctions = (
        db.query(Auction)
        .options(
            joinedload(Auction.rfq),
            joinedload(Auction.bids).joinedload(Bid.supplier),
        )
        .order_by(Auction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results: List[AuctionListItemResponse] = []
    for auc in auctions:
        if not auc.rfq:
            continue

        # Find lowest valid bid
        valid_bids = [b for b in auc.bids if b.is_valid]
        valid_bids.sort(key=lambda x: (x.amount, x.submitted_at, str(x.id)))
        lowest_bid_val = valid_bids[0].amount if valid_bids else None
        lowest_bidder_name = valid_bids[0].supplier.name if valid_bids and valid_bids[0].supplier else None
        lowest_bidder_id = valid_bids[0].supplier_id if valid_bids else None

        display_stat = compute_auction_display_status(auc)

        results.append(
            AuctionListItemResponse(
                id=auc.id,
                rfq_id=auc.rfq_id,
                rfq_title=auc.rfq.title,
                currency=auc.rfq.currency,
                baseline_price=auc.rfq.baseline_price,
                lowest_bid=lowest_bid_val,
                lowest_bidder_name=lowest_bidder_name,
                lowest_bidder_id=lowest_bidder_id,
                bid_start_time=auc.start_time,
                bid_close_time=auc.end_time,
                forced_bid_close_time=auc.forced_bid_close_time,
                trigger_window_minutes=auc.trigger_window_minutes,
                extension_duration_minutes=auc.extension_duration_minutes,
                extension_trigger=auc.extension_trigger,
                status=auc.status,
                display_status=display_stat,
                total_bids=len(valid_bids),
                created_at=auc.created_at,
                updated_at=auc.updated_at,
            )
        )

    return results


def get_auction_detail(db: Session, identifier: UUID) -> AuctionDetailFullResponse:
    """
    Retrieves full auction workspace details by Auction UUID or RFQ UUID.
    Includes configuration, all supplier bids with L1/L2/L3 rankings and quote details, and activity log history.
    """
    auction = (
        db.query(Auction)
        .options(
            joinedload(Auction.rfq).joinedload(RFQ.buyer),
            joinedload(Auction.rfq).selectinload(RFQ.items),
        )
        .filter((Auction.id == identifier) | (Auction.rfq_id == identifier))
        .first()
    )

    if not auction or not auction.rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction or RFQ with id '{identifier}' not found",
        )

    rfq = auction.rfq

    # Calculate deterministic rankings
    ranking_resp = get_rfq_bid_ranking(db, rfq.id)
    rankings = ranking_resp.rankings

    # Fetch activity logs
    activity_records = get_rfq_activity_logs(db, rfq.id)
    activity_logs = [ActivityLogResponse.model_validate(log) for log in activity_records]

    # Convert items & buyer
    items_resp = [RFQItemResponse.model_validate(item) for item in rfq.items]
    buyer_resp = BuyerResponse.model_validate(rfq.buyer) if rfq.buyer else None

    # Determine lowest bid
    lowest_bid_val = rankings[0].amount if rankings else None
    lowest_bidder_name = rankings[0].supplier_name if rankings else None

    display_stat = compute_auction_display_status(auction)

    return AuctionDetailFullResponse(
        id=auction.id,
        rfq_id=rfq.id,
        rfq_title=rfq.title,
        rfq_description=rfq.description,
        rfq_category=rfq.category,
        currency=rfq.currency,
        baseline_price=rfq.baseline_price,
        pickup_service_date=rfq.pickup_service_date,
        rfq_status=rfq.status,
        bid_start_time=auction.start_time,
        bid_close_time=auction.end_time,
        forced_bid_close_time=auction.forced_bid_close_time,
        trigger_window_minutes=auction.trigger_window_minutes,
        extension_duration_minutes=auction.extension_duration_minutes,
        extension_trigger=auction.extension_trigger,
        status=auction.status,
        display_status=display_stat,
        current_round=auction.current_round,
        created_at=auction.created_at,
        updated_at=auction.updated_at,
        lowest_bid=lowest_bid_val,
        lowest_bidder_name=lowest_bidder_name,
        total_bids=len(rankings),
        buyer=buyer_resp,
        items=items_resp,
        bids=rankings,
        activity_logs=activity_logs,
    )


