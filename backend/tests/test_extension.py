import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ExtensionTrigger, EventType
from app.schemas.bid import BidCreate, RankedBidItem
from app.services.bid_service import create_bid, get_rfq_bid_ranking
from app.services.extension_service import (
    is_within_trigger_window,
    calculate_extension,
    validate_auction_extension_config,
    evaluate_and_apply_extension,
)


@pytest.fixture
def extension_setup(client: TestClient, db: Session, cleanup_tracker):
    """Helper fixture to create Buyer, 3 Suppliers, RFQ, and Auction configured for extension testing."""
    # 1. Create Buyer
    buyer = Buyer(name="Extension Buyer", email=f"ext_buyer_{uuid.uuid4().hex[:8]}@example.com")
    db.add(buyer)
    db.flush()
    cleanup_tracker.track_buyer(buyer.id)

    # 2. Create 3 Suppliers
    supplier_a = Supplier(name="Supplier Alpha", email=f"alpha_{uuid.uuid4().hex[:8]}@example.com", company_name="Alpha Corp")
    supplier_b = Supplier(name="Supplier Beta", email=f"beta_{uuid.uuid4().hex[:8]}@example.com", company_name="Beta Corp")
    supplier_c = Supplier(name="Supplier Gamma", email=f"gamma_{uuid.uuid4().hex[:8]}@example.com", company_name="Gamma Corp")
    db.add_all([supplier_a, supplier_b, supplier_c])
    db.flush()
    cleanup_tracker.track_supplier(supplier_a.id)
    cleanup_tracker.track_supplier(supplier_b.id)
    cleanup_tracker.track_supplier(supplier_c.id)

    # 3. Create RFQ
    rfq = RFQ(
        buyer_id=buyer.id,
        title="Extension Test RFQ",
        currency="USD",
        baseline_price=Decimal("100000.00"),
        status=RFQStatus.AUCTION_ACTIVE,
    )
    db.add(rfq)
    db.flush()
    cleanup_tracker.track_rfq(rfq.id)

    rfq_item = RFQItem(
        rfq_id=rfq.id,
        name="Precision Engine Turbine",
        quantity=Decimal("10"),
        unit="units",
    )
    db.add(rfq_item)
    db.flush()

    db.commit()

    return {
        "buyer": buyer,
        "supplier_a": supplier_a,
        "supplier_b": supplier_b,
        "supplier_c": supplier_c,
        "rfq": rfq,
        "rfq_item": rfq_item,
    }


# ==============================================================================
# TEST 1 — Trigger Window Calculation
# ==============================================================================
def test_1_trigger_window_calculation():
    """Given close = 18:00, X = 10, verify trigger window starts at 17:50 and ends at 18:00."""
    close_time = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    trigger_window_minutes = 10

    # Test exact window start (17:50:00)
    assert is_within_trigger_window(
        event_time=datetime(2026, 8, 29, 17, 50, 0, tzinfo=timezone.utc),
        current_close=close_time,
        trigger_window_minutes=trigger_window_minutes,
    ) is True

    # Test inside window (17:55:00)
    assert is_within_trigger_window(
        event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc),
        current_close=close_time,
        trigger_window_minutes=trigger_window_minutes,
    ) is True

    # Test exact window end (18:00:00)
    assert is_within_trigger_window(
        event_time=datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc),
        current_close=close_time,
        trigger_window_minutes=trigger_window_minutes,
    ) is True

    # Test 1 second before window start (17:49:59) -> outside
    assert is_within_trigger_window(
        event_time=datetime(2026, 8, 29, 17, 49, 59, tzinfo=timezone.utc),
        current_close=close_time,
        trigger_window_minutes=trigger_window_minutes,
    ) is False


# ==============================================================================
# TEST 2 — Bid Inside Trigger Window
# ==============================================================================
def test_2_bid_inside_trigger_window(db: Session, extension_setup, cleanup_tracker):
    """Given close = 18:00, X = 10, Y = 5, bid at 17:55 extends close to 18:05."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        start_time=initial_close - timedelta(hours=1),
        end_time=initial_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.flush()

    round1 = AuctionRound(
        auction_id=auction.id,
        round_number=1,
        status=AuctionRoundStatus.ACTIVE,
        start_time=auction.start_time,
        end_time=initial_close,
    )
    db.add(round1)
    db.commit()

    bid_time = datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc)
    bid_payload = BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00"))

    created = create_bid(db, bid_payload, event_time=bid_time)
    cleanup_tracker.track_bid(created.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert created.auction_extended is True


# ==============================================================================
# TEST 3 — Bid Outside Trigger Window
# ==============================================================================
def test_3_bid_outside_trigger_window(db: Session, extension_setup, cleanup_tracker):
    """Given close = 18:00, X = 10, bid at 17:40 leaves close at 18:00."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        start_time=initial_close - timedelta(hours=1),
        end_time=initial_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    bid_time = datetime(2026, 8, 29, 17, 40, 0, tzinfo=timezone.utc)
    bid_payload = BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00"))

    created = create_bid(db, bid_payload, event_time=bid_time)
    cleanup_tracker.track_bid(created.id)

    db.refresh(auction)
    assert auction.end_time == initial_close
    assert created.auction_extended is False


# ==============================================================================
# TEST 4 — Bid Exactly Near Close
# ==============================================================================
def test_4_bid_exactly_near_close(db: Session, extension_setup, cleanup_tracker):
    """Bid in the final minute (17:59:30 for 18:00:00 close) extends if BID_RECEIVED."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    bid_time = datetime(2026, 8, 29, 17, 59, 30, tzinfo=timezone.utc)
    bid_payload = BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("88000.00"))

    created = create_bid(db, bid_payload, event_time=bid_time)
    cleanup_tracker.track_bid(created.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert created.auction_extended is True


# ==============================================================================
# TEST 5 — Any Rank Change Trigger
# ==============================================================================
def test_5_any_rank_change_trigger(db: Session, extension_setup, cleanup_tracker):
    """When Supplier B's bid inside window changes the supplier ranking, extension occurs."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.ANY_RANK_CHANGE,
    )
    db.add(auction)
    db.commit()

    # Step 1: Supplier A places initial bid outside window at 17:30 (A is L1)
    bid_a = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("85000.00")),
        event_time=datetime(2026, 8, 29, 17, 30, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_a.id)

    # Step 2: Supplier B places lower bid at 17:55 (inside window, B becomes L1, A becomes L2)
    bid_b = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("80000.00")),
        event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_b.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert bid_b.auction_extended is True


# ==============================================================================
# TEST 6 — Any Rank Change Outside Window
# ==============================================================================
def test_6_any_rank_change_outside_window(db: Session, extension_setup, cleanup_tracker):
    """Ranking changes, but bid occurs outside trigger window -> no extension."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.ANY_RANK_CHANGE,
    )
    db.add(auction)
    db.commit()

    bid_a = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("85000.00")),
        event_time=datetime(2026, 8, 29, 17, 20, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_a.id)

    # Supplier B places bid at 17:40 (outside 17:50-18:00 window)
    bid_b = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("80000.00")),
        event_time=datetime(2026, 8, 29, 17, 40, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_b.id)

    db.refresh(auction)
    assert auction.end_time == initial_close
    assert bid_b.auction_extended is False


# ==============================================================================
# TEST 7 — L1 Rank Change Trigger
# ==============================================================================
def test_7_l1_rank_change_trigger(db: Session, extension_setup, cleanup_tracker):
    """Lowest Bidder (L1) changes inside trigger window -> extension occurs."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.L1_RANK_CHANGE,
    )
    db.add(auction)
    db.commit()

    # Initial L1 is Supplier A
    bid_a = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("85000.00")),
        event_time=datetime(2026, 8, 29, 17, 30, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_a.id)

    # Supplier B takes L1 inside trigger window at 17:56
    bid_b = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("79000.00")),
        event_time=datetime(2026, 8, 29, 17, 56, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_b.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert bid_b.auction_extended is True


# ==============================================================================
# TEST 8 — L1 Does Not Change
# ==============================================================================
def test_8_l1_does_not_change(db: Session, extension_setup, cleanup_tracker):
    """
    Supplier A is L1 (70k), Supplier B is L2 (90k).
    Supplier C submits 80k (takes L2 position). L1 remains Supplier A.
    For L1_RANK_CHANGE trigger: no extension.
    """
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]
    supplier_c = extension_setup["supplier_c"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.L1_RANK_CHANGE,
    )
    db.add(auction)
    db.commit()

    bid_a = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("70000.00")),
        event_time=datetime(2026, 8, 29, 17, 20, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_a.id)

    bid_b = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("90000.00")),
        event_time=datetime(2026, 8, 29, 17, 30, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_b.id)

    # Supplier C submits 80k at 17:55 (inside window, becomes L2, but L1 is still A)
    bid_c = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_c.id, amount=Decimal("80000.00")),
        event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_c.id)

    db.refresh(auction)
    # L1 did not change, so auction must NOT extend
    assert auction.end_time == initial_close
    assert bid_c.auction_extended is False


# ==============================================================================
# TEST 9 — Bid Received Trigger Independent of Rank
# ==============================================================================
def test_9_bid_received_independent_of_rank(db: Session, extension_setup, cleanup_tracker):
    """In BID_RECEIVED mode, any valid bid inside trigger window extends, even if rank doesn't change."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    bid_a = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("50000.00")),
        event_time=datetime(2026, 8, 29, 17, 30, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_a.id)

    # Supplier B submits higher bid (90k, becomes L2, no L1 change) inside window at 17:55
    bid_b = create_bid(
        db,
        BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("90000.00")),
        event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc),
    )
    cleanup_tracker.track_bid(bid_b.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert bid_b.auction_extended is True


# ==============================================================================
# TEST 10 — Invalid Bid Does Not Trigger
# ==============================================================================
def test_10_invalid_bid_does_not_trigger(client: TestClient, db: Session, extension_setup, cleanup_tracker):
    """An invalid bid rejected by validation must not trigger an extension."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    # Submit invalid negative amount
    resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": str(rfq.id), "supplier_id": str(supplier_a.id), "amount": -100.00},
    )
    assert resp.status_code == 422

    db.refresh(auction)
    assert auction.end_time == initial_close


# ==============================================================================
# TEST 11 — Extension Duration
# ==============================================================================
def test_11_extension_duration():
    """Given close = 18:00 and Y = 5, calculate_extension returns 18:05."""
    close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    new_close = calculate_extension(close, extension_duration_minutes=5)
    assert new_close == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)


# ==============================================================================
# TEST 12 — Forced Close Cap
# ==============================================================================
def test_12_forced_close_cap():
    """Given close = 18:27, Y = 10, forced close = 18:30 -> new close is 18:30, never 18:37."""
    close = datetime(2026, 8, 29, 18, 27, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)

    new_close = calculate_extension(close, extension_duration_minutes=10, forced_close=forced_close)
    assert new_close == datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)
    assert new_close <= forced_close


# ==============================================================================
# TEST 13 — Forced Close Already Reached
# ==============================================================================
def test_13_forced_close_already_reached(db: Session, extension_setup, cleanup_tracker):
    """When close == forced close, no further extension is possible."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    forced_close = datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=forced_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    bid_time = datetime(2026, 8, 29, 18, 25, 0, tzinfo=timezone.utc)
    bid_payload = BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("75000.00"))

    created = create_bid(db, bid_payload, event_time=bid_time)
    cleanup_tracker.track_bid(created.id)

    db.refresh(auction)
    assert auction.end_time == forced_close
    assert created.auction_extended is False


# ==============================================================================
# TEST 14 — Forced Close Validation
# ==============================================================================
def test_14_forced_close_validation():
    """Validate forced close time must be strictly later than bid close time."""
    close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    # Valid: forced > close
    validate_auction_extension_config(bid_close_time=close, forced_bid_close_time=close + timedelta(minutes=30))

    # Invalid: forced == close
    with pytest.raises(HTTPException) as exc_info1:
        validate_auction_extension_config(bid_close_time=close, forced_bid_close_time=close)
    assert exc_info1.value.status_code == 400

    # Invalid: forced < close
    with pytest.raises(HTTPException) as exc_info2:
        validate_auction_extension_config(bid_close_time=close, forced_bid_close_time=close - timedelta(minutes=1))
    assert exc_info2.value.status_code == 400


# ==============================================================================
# TEST 15 — Multiple Extensions
# ==============================================================================
def test_15_multiple_extensions(db: Session, extension_setup, cleanup_tracker):
    """
    Initial close = 18:00, forced close = 18:20, X = 10, Y = 5.
    Multiple qualifying bids advance close: 18:00 -> 18:05 -> 18:10 -> 18:15 -> 18:20 (cap).
    """
    rfq = extension_setup["rfq"]
    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 20, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    # Step 1: Supplier 1 bids at 17:55 -> close becomes 18:05
    s1 = Supplier(name="S1", email=f"s1_{uuid.uuid4().hex[:8]}@example.com")
    db.add(s1)
    db.commit()
    cleanup_tracker.track_supplier(s1.id)
    b1 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=s1.id, amount=Decimal("95000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b1.id)
    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)

    # Step 2: Supplier 2 bids at 18:00 -> close becomes 18:10
    s2 = Supplier(name="S2", email=f"s2_{uuid.uuid4().hex[:8]}@example.com")
    db.add(s2)
    db.commit()
    cleanup_tracker.track_supplier(s2.id)
    b2 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=s2.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b2.id)
    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 10, 0, tzinfo=timezone.utc)

    # Step 3: Supplier 3 bids at 18:07 -> close becomes 18:15
    s3 = Supplier(name="S3", email=f"s3_{uuid.uuid4().hex[:8]}@example.com")
    db.add(s3)
    db.commit()
    cleanup_tracker.track_supplier(s3.id)
    b3 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=s3.id, amount=Decimal("85000.00")), event_time=datetime(2026, 8, 29, 18, 7, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b3.id)
    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 15, 0, tzinfo=timezone.utc)

    # Step 4: Supplier 4 bids at 18:14 -> close becomes 18:20 (capped at forced close)
    s4 = Supplier(name="S4", email=f"s4_{uuid.uuid4().hex[:8]}@example.com")
    db.add(s4)
    db.commit()
    cleanup_tracker.track_supplier(s4.id)
    b4 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=s4.id, amount=Decimal("80000.00")), event_time=datetime(2026, 8, 29, 18, 14, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b4.id)
    db.refresh(auction)
    assert auction.end_time == forced_close


# ==============================================================================
# TEST 16 — Trigger Window Uses CURRENT Close Time
# ==============================================================================
def test_16_trigger_window_uses_current_close(db: Session, extension_setup, cleanup_tracker):
    """
    Initial close = 18:00, X = 10, Y = 5.
    Trigger at 17:55 extends close to 18:05.
    Subsequent trigger window is [17:55, 18:05]. A bid at 17:56 is inside this new window.
    """
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 30, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    # Bid 1 at 17:55 -> close becomes 18:05
    b1 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b1.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)

    # Next trigger window is based on 18:05 -> [17:55, 18:05]
    # Bid 2 at 18:02 is inside [17:55, 18:05] -> extends close to 18:10
    b2 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("85000.00")), event_time=datetime(2026, 8, 29, 18, 2, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b2.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 10, 0, tzinfo=timezone.utc)


# ==============================================================================
# TEST 17 — Multiple Suppliers Ranking Extension Interaction
# ==============================================================================
def test_17_multiple_suppliers_extension(db: Session, extension_setup, cleanup_tracker):
    """Verify extension calculation with multiple suppliers and rank transitions."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]
    supplier_c = extension_setup["supplier_c"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.ANY_RANK_CHANGE,
    )
    db.add(auction)
    db.commit()

    # Pre-populate 2 bids outside window
    b_a = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 17, 20, 0, tzinfo=timezone.utc))
    b_b = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("80000.00")), event_time=datetime(2026, 8, 29, 17, 30, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b_a.id)
    cleanup_tracker.track_bid(b_b.id)

    # Initial ranks: B=L1 (80k), A=L2 (90k)
    # Supplier C bids 85k inside trigger window at 17:55 (becomes L2, shifts A to L3)
    b_c = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_c.id, amount=Decimal("85000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b_c.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert b_c.auction_extended is True


# ==============================================================================
# TEST 18 — No Duplicate Extension From One Bid
# ==============================================================================
def test_18_no_duplicate_extension_from_one_bid(db: Session, extension_setup, cleanup_tracker):
    """A single qualifying bid applies exactly one extension increment."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    bid = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(bid.id)

    db.refresh(auction)
    # Exactly +5 minutes, not +10
    assert auction.end_time == initial_close + timedelta(minutes=5)


# ==============================================================================
# TEST 19 — Concurrent Bid Safety
# ==============================================================================
def test_19_concurrent_bid_safety(db: Session, extension_setup, cleanup_tracker):
    """Close time never moves backwards, never exceeds forced close."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]
    supplier_b = extension_setup["supplier_b"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 8, 29, 18, 10, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    b1 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b1.id)

    db.refresh(auction)
    assert auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)

    b2 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("85000.00")), event_time=datetime(2026, 8, 29, 17, 56, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(b2.id)

    db.refresh(auction)
    # Close time advanced to 18:10 (forced close cap) and never backwards
    assert auction.end_time == forced_close
    assert auction.end_time <= forced_close


# ==============================================================================
# TEST 20 — Persistence
# ==============================================================================
def test_20_persistence(db: Session, extension_setup, cleanup_tracker):
    """Verify new close time is persisted in PostgreSQL and survives session clear."""
    rfq = extension_setup["rfq"]
    supplier_a = extension_setup["supplier_a"]

    initial_close = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)

    auction = Auction(
        rfq_id=rfq.id,
        status=AuctionStatus.LIVE,
        current_round=1,
        end_time=initial_close,
        forced_bid_close_time=initial_close + timedelta(minutes=30),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger=ExtensionTrigger.BID_RECEIVED,
    )
    db.add(auction)
    db.commit()

    auction_id = auction.id

    bid = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("90000.00")), event_time=datetime(2026, 8, 29, 17, 55, 0, tzinfo=timezone.utc))
    cleanup_tracker.track_bid(bid.id)

    # Expire and reload directly from PostgreSQL
    db.expire_all()
    reloaded_auction = db.query(Auction).filter(Auction.id == auction_id).first()

    assert reloaded_auction is not None
    assert reloaded_auction.end_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert reloaded_auction.bid_close_time == datetime(2026, 8, 29, 18, 5, 0, tzinfo=timezone.utc)
    assert reloaded_auction.trigger_window == 10
    assert reloaded_auction.extension_duration == 5
    assert reloaded_auction.extension_trigger == ExtensionTrigger.BID_RECEIVED
