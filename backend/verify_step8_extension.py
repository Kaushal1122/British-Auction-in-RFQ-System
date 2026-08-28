import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ExtensionTrigger
from app.schemas.bid import BidCreate
from app.services.bid_service import create_bid


def run_e2e_extension_verification():
    print("=" * 80)
    print("STEP 8 — BRITISH AUCTION AUTOMATIC TIME EXTENSION VERIFICATION")
    print("=" * 80)

    db = SessionLocal()
    client = TestClient(app)

    try:
        # 1. Create entities
        buyer = Buyer(name="Step 8 Buyer", email=f"step8_buyer_{uuid.uuid4().hex[:6]}@example.com")
        db.add(buyer)
        db.flush()

        supplier_a = Supplier(name="Supplier Alpha", email=f"alpha_{uuid.uuid4().hex[:6]}@example.com", company_name="Alpha Corp")
        supplier_b = Supplier(name="Supplier Beta", email=f"beta_{uuid.uuid4().hex[:6]}@example.com", company_name="Beta Corp")
        supplier_c = Supplier(name="Supplier Gamma", email=f"gamma_{uuid.uuid4().hex[:6]}@example.com", company_name="Gamma Corp")
        db.add_all([supplier_a, supplier_b, supplier_c])
        db.flush()

        rfq = RFQ(
            buyer_id=buyer.id,
            title="Aero Turbine British Auction",
            currency="USD",
            baseline_price=Decimal("150000.00"),
            status=RFQStatus.AUCTION_ACTIVE,
        )
        db.add(rfq)
        db.flush()

        # =========================================================================
        # Scenario 1: BID_RECEIVED trigger with multiple extensions up to forced close
        # =========================================================================
        print("\n[Scenario 1] Testing BID_RECEIVED trigger with chained extensions and forced close cap...")
        initial_close = datetime.now(timezone.utc) + timedelta(minutes=10)
        forced_close = initial_close + timedelta(minutes=12)  # Cap allows 2 extensions: +5m (15m), +5m (20m -> capped at 22m)

        auction = Auction(
            rfq_id=rfq.id,
            status=AuctionStatus.LIVE,
            current_round=1,
            start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
            end_time=initial_close,
            forced_bid_close_time=forced_close,
            trigger_window_minutes=10,
            extension_duration_minutes=5,
            extension_trigger=ExtensionTrigger.BID_RECEIVED,
        )
        db.add(auction)
        db.commit()

        print(f"  Initial Close Time: {auction.end_time.isoformat()}")
        print(f"  Forced Close Time:  {auction.forced_bid_close_time.isoformat()}")
        print(f"  Trigger Window:     {auction.trigger_window} minutes")
        print(f"  Extension Duration: {auction.extension_duration} minutes")
        print(f"  Extension Trigger:  {auction.extension_trigger}")

        # Extension 1: Bid inside window
        bid1_time = initial_close - timedelta(minutes=5)
        bid1 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_a.id, amount=Decimal("140000.00")), event_time=bid1_time)
        db.refresh(auction)
        print(f"  --> After Bid 1: Close extended to {auction.end_time.isoformat()} (Extended={bid1.auction_extended})")
        assert auction.end_time == initial_close + timedelta(minutes=5), "Close time should advance by 5m"
        assert bid1.auction_extended is True

        # Extension 2: Second bid in new window
        bid2_time = auction.end_time - timedelta(minutes=3)
        bid2 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_b.id, amount=Decimal("135000.00")), event_time=bid2_time)
        db.refresh(auction)
        print(f"  --> After Bid 2: Close extended to {auction.end_time.isoformat()} (Extended={bid2.auction_extended})")
        assert auction.end_time == initial_close + timedelta(minutes=10), "Close time should advance by another 5m"
        assert bid2.auction_extended is True

        # Extension 3: Third bid hitting forced close cap (forced close is +12m, requested is +15m)
        bid3_time = auction.end_time - timedelta(minutes=2)
        bid3 = create_bid(db, BidCreate(rfq_id=rfq.id, supplier_id=supplier_c.id, amount=Decimal("130000.00")), event_time=bid3_time)
        db.refresh(auction)
        print(f"  --> After Bid 3 (cap): Close capped at {auction.end_time.isoformat()} (Extended={bid3.auction_extended})")
        assert auction.end_time == forced_close, "Close time should be strictly capped at forced close"
        assert auction.end_time <= forced_close

        print("  [OK] Scenario 1 passed!")

        # =========================================================================
        # Scenario 2: ANY_RANK_CHANGE trigger vs L1_RANK_CHANGE trigger
        # =========================================================================
        print("\n[Scenario 2] Testing ANY_RANK_CHANGE vs L1_RANK_CHANGE...")
        rfq2 = RFQ(
            buyer_id=buyer.id,
            title="Turbine Bearings British Auction",
            currency="USD",
            baseline_price=Decimal("80000.00"),
            status=RFQStatus.AUCTION_ACTIVE,
        )
        db.add(rfq2)
        db.flush()

        initial_close2 = datetime.now(timezone.utc) + timedelta(minutes=10)
        forced_close2 = initial_close2 + timedelta(minutes=30)

        auction2 = Auction(
            rfq_id=rfq2.id,
            status=AuctionStatus.LIVE,
            current_round=1,
            end_time=initial_close2,
            forced_bid_close_time=forced_close2,
            trigger_window_minutes=10,
            extension_duration_minutes=5,
            extension_trigger=ExtensionTrigger.L1_RANK_CHANGE,
        )
        db.add(auction2)
        db.commit()

        # Step A: Supplier A bids 50k (becomes L1)
        b_a = create_bid(db, BidCreate(rfq_id=rfq2.id, supplier_id=supplier_a.id, amount=Decimal("50000.00")), event_time=initial_close2 - timedelta(minutes=15))
        # Step B: Supplier B bids 70k (becomes L2, A is still L1)
        b_b = create_bid(db, BidCreate(rfq_id=rfq2.id, supplier_id=supplier_b.id, amount=Decimal("70000.00")), event_time=initial_close2 - timedelta(minutes=12))

        # Step C: Supplier C bids 60k inside window at close-5m (becomes L2, B shifts to L3, but L1 is STILL A)
        b_c = create_bid(db, BidCreate(rfq_id=rfq2.id, supplier_id=supplier_c.id, amount=Decimal("60000.00")), event_time=initial_close2 - timedelta(minutes=5))
        db.refresh(auction2)
        print(f"  --> L1_RANK_CHANGE mode with non-L1 rank change: Close={auction2.end_time.isoformat()} (Extended={b_c.auction_extended})")
        assert auction2.end_time == initial_close2, "Auction should NOT extend because L1 supplier did not change"
        assert b_c.auction_extended is False

        # Step D: Supplier D takes L1 with 45k inside window
        supplier_d = Supplier(name="Supplier Delta", email=f"delta_{uuid.uuid4().hex[:6]}@example.com")
        db.add(supplier_d)
        db.commit()

        b_d = create_bid(db, BidCreate(rfq_id=rfq2.id, supplier_id=supplier_d.id, amount=Decimal("45000.00")), event_time=initial_close2 - timedelta(minutes=4))
        db.refresh(auction2)
        print(f"  --> L1_RANK_CHANGE mode when L1 changes: Close={auction2.end_time.isoformat()} (Extended={b_d.auction_extended})")
        assert auction2.end_time == initial_close2 + timedelta(minutes=5), "Auction SHOULD extend when L1 changes"
        assert b_d.auction_extended is True

        print("  [OK] Scenario 2 passed!")

        # =========================================================================
        # Database Persistence Verification
        # =========================================================================
        print("\n[Database Persistence Verification]")
        db.expire_all()
        persisted = db.query(Auction).filter(Auction.id == auction.id).first()
        assert persisted.end_time == forced_close
        assert persisted.forced_bid_close_time == forced_close
        assert persisted.trigger_window_minutes == 10
        assert persisted.extension_duration_minutes == 5
        assert persisted.extension_trigger == ExtensionTrigger.BID_RECEIVED
        print(f"  [OK] PostgreSQL Persistence Verified: Close={persisted.end_time}, Forced={persisted.forced_bid_close_time}, Mode={persisted.extension_trigger}")

        print("\n" + "=" * 80)
        print("ALL STEP 8 EXTENSION VERIFICATION SCENARIOS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_e2e_extension_verification()
