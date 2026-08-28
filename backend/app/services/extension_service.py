import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.models.enums import AuctionRoundStatus, ExtensionTrigger, ActorType, EventType
from app.schemas.bid import RankedBidItem

logger = logging.getLogger(__name__)


def is_within_trigger_window(
    event_time: datetime,
    current_close: datetime,
    trigger_window_minutes: int,
) -> bool:
    """
    Determines whether a bidding event occurred inside the trigger window [current_close - X, current_close].

    Args:
        event_time: Authoritative timestamp of the bid or activity.
        current_close: Current auction close timestamp.
        trigger_window_minutes: Window duration X in minutes.

    Returns:
        bool: True if event_time falls within [current_close - X, current_close], False otherwise.
    """
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    if current_close.tzinfo is None:
        current_close = current_close.replace(tzinfo=timezone.utc)

    window_start = current_close - timedelta(minutes=trigger_window_minutes)
    return window_start <= event_time <= current_close


def calculate_extension(
    current_close: datetime,
    extension_duration_minutes: int,
    forced_close: Optional[datetime] = None,
) -> datetime:
    """
    Calculates the extended close time given the current close, duration Y, and absolute forced close cap.

    Formula:
        requested_close = current_close + extension_duration_minutes
        new_close = min(requested_close, forced_close) if forced_close else requested_close

    Args:
        current_close: The current auction close time.
        extension_duration_minutes: Additional time Y in minutes to extend.
        forced_close: Optional upper bound datetime that can never be exceeded.

    Returns:
        datetime: The calculated new close time respecting the forced close cap.
    """
    if current_close.tzinfo is None:
        current_close = current_close.replace(tzinfo=timezone.utc)

    requested_close = current_close + timedelta(minutes=extension_duration_minutes)

    if forced_close is not None:
        if forced_close.tzinfo is None:
            forced_close = forced_close.replace(tzinfo=timezone.utc)
        return min(requested_close, forced_close)

    return requested_close


def validate_auction_extension_config(
    bid_close_time: Optional[datetime] = None,
    forced_bid_close_time: Optional[datetime] = None,
    bid_start_time: Optional[datetime] = None,
    trigger_window_minutes: int = 10,
    extension_duration_minutes: int = 5,
) -> None:
    """
    Validates auction time configuration rules:
    - Bid Start Time must be strictly earlier than Bid Close Time.
    - Forced Bid Close Time must be strictly later than Bid Close Time.
    - Forced Bid Close Time must be strictly later than Bid Start Time.
    - Trigger window and extension duration must be positive integers.

    Raises:
        HTTPException (400) if validation fails.
    """
    if trigger_window_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trigger window must be greater than 0 minutes",
        )

    if extension_duration_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extension duration must be greater than 0 minutes",
        )

    start_t: Optional[datetime] = None
    if bid_start_time is not None:
        start_t = bid_start_time.replace(tzinfo=timezone.utc) if bid_start_time.tzinfo is None else bid_start_time

    close_t: Optional[datetime] = None
    if bid_close_time is not None:
        close_t = bid_close_time.replace(tzinfo=timezone.utc) if bid_close_time.tzinfo is None else bid_close_time

    forced_t: Optional[datetime] = None
    if forced_bid_close_time is not None:
        forced_t = forced_bid_close_time.replace(tzinfo=timezone.utc) if forced_bid_close_time.tzinfo is None else forced_bid_close_time

    if start_t is not None and close_t is not None:
        if close_t <= start_t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid Close Time must be later than Bid Start Time",
            )

    if close_t is not None and forced_t is not None:
        if forced_t <= close_t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forced Bid Close Time must be later than Bid Close Time",
            )

    if start_t is not None and forced_t is not None:
        if forced_t <= start_t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forced Bid Close Time must be later than Bid Start Time",
            )


def evaluate_and_apply_extension(
    db: Session,
    auction: Auction,
    bid: Bid,
    previous_rankings: List[RankedBidItem],
    new_rankings: List[RankedBidItem],
    event_time: Optional[datetime] = None,
) -> Tuple[bool, Optional[datetime], Optional[str]]:
    """
    Evaluates British Auction automatic extension criteria and persists updated close time if qualified.

    Supported Extension Triggers:
    1. BID_RECEIVED: Any valid bid received inside the trigger window [close - X, close].
    2. ANY_RANK_CHANGE: Any change in supplier rank positions caused by the qualifying bid inside the trigger window.
    3. L1_RANK_CHANGE: A change in the identity of the lowest bidder (L1 supplier) inside the trigger window.

    Rules:
    - If current_close is None (open-ended / unscheduled), no extension is applied.
    - Extensions use the auction's CURRENT close time, supporting multiple successive extensions.
    - Extensions NEVER exceed the Forced Bid Close Time.
    - When close time reaches forced_bid_close_time, no further extension occurs.
    - Synchronizes the active AuctionRound end_time with the updated auction close time.

    Returns:
        Tuple[bool, Optional[datetime], Optional[str]]:
            (extended, new_close_time, reason_or_status_message)
    """
    if auction.end_time is None:
        return False, None, "Auction has no close time configured"

    # Normalize datetimes for timezone-safe comparison
    close_time = auction.end_time
    if close_time.tzinfo is None:
        close_time = close_time.replace(tzinfo=timezone.utc)

    event_dt = event_time or bid.submitted_at or datetime.now(timezone.utc)
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)

    forced_close: Optional[datetime] = None
    if auction.forced_bid_close_time is not None:
        forced_close = auction.forced_bid_close_time
        if forced_close.tzinfo is None:
            forced_close = forced_close.replace(tzinfo=timezone.utc)

        # Check if already at or beyond forced close boundary
        if close_time >= forced_close:
            return False, close_time, "Auction close time has already reached Forced Bid Close Time boundary"

    # 1. Verify event occurs inside trigger window [close_time - X, close_time]
    window_minutes = auction.trigger_window_minutes if auction.trigger_window_minutes is not None else 10
    if not is_within_trigger_window(event_dt, close_time, window_minutes):
        return False, close_time, "Activity occurred outside the trigger window"

    # 2. Evaluate trigger condition
    trigger_mode = auction.extension_trigger or ExtensionTrigger.BID_RECEIVED
    trigger_met = False
    trigger_reason = ""

    if trigger_mode == ExtensionTrigger.BID_RECEIVED:
        trigger_met = True
        trigger_reason = f"Bid received inside {window_minutes}-minute trigger window"

    elif trigger_mode == ExtensionTrigger.ANY_RANK_CHANGE:
        prev_map = {r.supplier_id: r.rank for r in previous_rankings}
        new_map = {r.supplier_id: r.rank for r in new_rankings}
        # Check if any supplier's rank changed or new position assigned
        rank_changed = (prev_map != new_map)
        trigger_met = rank_changed
        if rank_changed:
            trigger_reason = f"Supplier rank change detected inside {window_minutes}-minute trigger window"
        else:
            trigger_reason = "Bid did not change supplier rankings"

    elif trigger_mode == ExtensionTrigger.L1_RANK_CHANGE:
        prev_l1 = previous_rankings[0].supplier_id if previous_rankings else None
        new_l1 = new_rankings[0].supplier_id if new_rankings else None
        # Must be a change in the lowest bidder (L1) supplier identity
        l1_changed = (prev_l1 != new_l1)
        trigger_met = l1_changed
        if l1_changed:
            trigger_reason = f"Lowest bidder (L1) changed from '{prev_l1}' to '{new_l1}' inside {window_minutes}-minute trigger window"
        else:
            trigger_reason = "Lowest bidder (L1) supplier identity remained unchanged"

    if not trigger_met:
        return False, close_time, trigger_reason

    # 3. Calculate extended close time capped at forced close
    duration_minutes = auction.extension_duration_minutes if auction.extension_duration_minutes is not None else 5
    new_close = calculate_extension(close_time, duration_minutes, forced_close)

    if new_close <= close_time:
        return False, close_time, "Calculated extension does not advance close time (forced close cap reached)"

    # 4. Apply extension to Auction and active AuctionRound(s)
    auction.end_time = new_close

    if auction.rounds:
        for r in auction.rounds:
            if r.status == AuctionRoundStatus.ACTIVE or r.round_number == auction.current_round:
                r.end_time = new_close

    # 5. Log ActivityLog event for AUCTION_EXTENDED
    activity_log = ActivityLog(
        rfq_id=auction.rfq_id,
        auction_id=auction.id,
        actor_type=ActorType.SYSTEM,
        event_type=EventType.AUCTION_EXTENDED,
        message=f"Auction automatically extended by {duration_minutes}m to {new_close.isoformat()} ({trigger_reason})",
        metadata_json={
            "trigger_mode": trigger_mode.value if hasattr(trigger_mode, "value") else str(trigger_mode),
            "trigger_window_minutes": window_minutes,
            "extension_duration_minutes": duration_minutes,
            "previous_close_time": close_time.isoformat(),
            "new_close_time": new_close.isoformat(),
            "forced_bid_close_time": forced_close.isoformat() if forced_close else None,
            "reason": trigger_reason,
            "bid_id": str(bid.id) if bid else None,
        },
    )
    db.add(activity_log)
    db.flush()

    logger.info(
        f"Auction '{auction.id}' extended from {close_time.isoformat()} to {new_close.isoformat()} "
        f"(Trigger: {trigger_mode}, Cap: {forced_close})"
    )

    return True, new_close, trigger_reason
