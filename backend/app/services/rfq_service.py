import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.buyer import Buyer
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ExtensionTrigger, ActorType, EventType
from app.schemas.rfq import RFQCreate
from app.services.extension_service import validate_auction_extension_config

logger = logging.getLogger(__name__)


def create_rfq(db: Session, rfq_in: RFQCreate) -> RFQ:
    """
    Atomically creates an RFQ along with all provided line items, its associated
    Auction and British Auction extension configuration, and records an RFQ_CREATED
    ActivityLog event within a single database transaction.

    If any operation fails or validation error occurs, the entire transaction is rolled back.
    """
    # 1. Verify that the specified buyer exists
    buyer = db.query(Buyer).filter(Buyer.id == rfq_in.buyer_id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Buyer with id '{rfq_in.buyer_id}' not found",
        )

    # 2. Validate items collection
    if not rfq_in.items or len(rfq_in.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one item is required to create an RFQ",
        )

    # 3. Validate auction schedule & extension timing rules
    validate_auction_extension_config(
        bid_close_time=rfq_in.bid_close_time,
        forced_bid_close_time=rfq_in.forced_bid_close_time,
        bid_start_time=rfq_in.bid_start_time,
        trigger_window_minutes=rfq_in.trigger_window_minutes if rfq_in.trigger_window_minutes is not None else 10,
        extension_duration_minutes=rfq_in.extension_duration_minutes if rfq_in.extension_duration_minutes is not None else 5,
    )

    # 4. Execute atomic creation in a single transaction
    try:
        # Create RFQ header
        rfq = RFQ(
            buyer_id=rfq_in.buyer_id,
            title=rfq_in.title,
            description=rfq_in.description,
            category=rfq_in.category,
            currency=rfq_in.currency,
            baseline_price=rfq_in.baseline_price,
            pickup_service_date=rfq_in.pickup_service_date,
            status=RFQStatus.DRAFT,
        )
        db.add(rfq)
        db.flush()  # Generates rfq.id for foreign keys without committing transaction

        # Create all line items
        for item_in in rfq_in.items:
            rfq_item = RFQItem(
                rfq_id=rfq.id,
                name=item_in.name,
                description=item_in.description,
                quantity=item_in.quantity,
                unit=item_in.unit,
            )
            db.add(rfq_item)

        # Create associated Auction record with British Auction configuration
        auction = Auction(
            rfq_id=rfq.id,
            start_time=rfq_in.bid_start_time,
            end_time=rfq_in.bid_close_time,
            forced_bid_close_time=rfq_in.forced_bid_close_time,
            trigger_window_minutes=rfq_in.trigger_window_minutes if rfq_in.trigger_window_minutes is not None else 10,
            extension_duration_minutes=rfq_in.extension_duration_minutes if rfq_in.extension_duration_minutes is not None else 5,
            extension_trigger=rfq_in.extension_trigger or ExtensionTrigger.BID_RECEIVED,
            status=AuctionStatus.SCHEDULED,
            current_round=1,
        )
        db.add(auction)
        db.flush()

        # Create initial pending/scheduled AuctionRound (round 1)
        round1 = AuctionRound(
            auction_id=auction.id,
            round_number=1,
            status=AuctionRoundStatus.PENDING,
            start_time=auction.start_time,
            end_time=auction.end_time,
        )
        db.add(round1)

        # Create RFQ_CREATED activity log
        activity_log = ActivityLog(
            rfq_id=rfq.id,
            actor_type=ActorType.BUYER,
            actor_id=rfq_in.buyer_id,
            event_type=EventType.RFQ_CREATED,
            message=f"RFQ '{rfq.title}' created with {len(rfq_in.items)} line item(s) and British Auction configuration",
            metadata_json={
                "items_count": len(rfq_in.items),
                "baseline_price": str(rfq_in.baseline_price),
                "currency": rfq_in.currency,
                "category": rfq_in.category,
                "pickup_service_date": rfq_in.pickup_service_date.isoformat() if rfq_in.pickup_service_date else None,
                "bid_start_time": rfq_in.bid_start_time.isoformat() if rfq_in.bid_start_time else None,
                "bid_close_time": rfq_in.bid_close_time.isoformat() if rfq_in.bid_close_time else None,
                "forced_bid_close_time": rfq_in.forced_bid_close_time.isoformat() if rfq_in.forced_bid_close_time else None,
                "trigger_window_minutes": auction.trigger_window_minutes,
                "extension_duration_minutes": auction.extension_duration_minutes,
                "extension_trigger": str(auction.extension_trigger),
            },
        )
        db.add(activity_log)

        # Commit entire transaction atomically
        db.commit()

        # Eagerly load the complete RFQ with relationships for response
        persisted_rfq = (
            db.query(RFQ)
            .options(
                joinedload(RFQ.buyer),
                selectinload(RFQ.items),
                joinedload(RFQ.auction),
            )
            .filter(RFQ.id == rfq.id)
            .first()
        )
        return persisted_rfq

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating RFQ: {e}")
        orig_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {orig_msg}",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during RFQ creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the RFQ. The transaction was rolled back.",
        )


def get_rfq_by_id(db: Session, rfq_id: UUID) -> RFQ:
    """
    Retrieve an RFQ by UUID with its buyer profile, line items, and auction config eagerly loaded.
    Raises HTTP 404 if not found.
    """
    rfq = (
        db.query(RFQ)
        .options(
            joinedload(RFQ.buyer),
            selectinload(RFQ.items),
            joinedload(RFQ.auction),
        )
        .filter(RFQ.id == rfq_id)
        .first()
    )
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with id '{rfq_id}' not found",
        )
    return rfq


def list_rfqs(db: Session, skip: int = 0, limit: int = 100) -> List[RFQ]:
    """
    List RFQs ordered by creation date descending with line items and auction loaded for summary response.
    """
    return (
        db.query(RFQ)
        .options(
            selectinload(RFQ.items),
            joinedload(RFQ.auction),
        )
        .order_by(RFQ.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

