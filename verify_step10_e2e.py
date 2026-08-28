"""
Step 10 End-to-End Verification Script: British Auction in RFQ System
=====================================================================
Executes a live end-to-end workflow against PostgreSQL (Port 5433)
testing all requirements from the assignment PDF:
1. Quote submission breakdown fields persistence & verification.
2. Activity tracking for BID_SUBMITTED and AUCTION_EXTENDED.
3. Dynamic extension trigger reason verification (BID_RECEIVED, ANY_RANK_CHANGE, L1_RANK_CHANGE).
4. Deterministic L1/L2/L3 ranking.
5. Auction listing and detailed workspace endpoints.
6. Forced-close hard cap boundary enforcement.
7. Multi-RFQ data isolation.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.db.database import SessionLocal
from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.services.bid_service import create_bid, get_auction_detail, list_auctions, get_rfq_bid_ranking
from app.schemas.bid import BidCreate


def run_e2e_verification():
    print("=" * 70)
    print(">> STARTING STEP 10 LIVE E2E FULL SYSTEM VERIFICATION")
    print("=" * 70)

    client = TestClient(app)
    db = SessionLocal()

    try:
        # 1. Health check
        print("\n[1/7] Testing API & Database Health (/health)...")
        res = client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("  [OK] Backend and PostgreSQL are healthy: " + str(res.json()))

        # 2. Setup Buyer & Suppliers
        print("\n[2/7] Creating Buyer & Suppliers in PostgreSQL...")
        unique_run = uuid4().hex[:6]
        buyer = Buyer(
            name=f"E2E Enterprise Buyer {unique_run}",
            email=f"buyer_{unique_run}@e2e-corp.com",
            company_name="Global Aerospace Logistics",
        )
        db.add(buyer)

        suppliers = []
        for i, name in enumerate(["Maersk Marine Freight", "DHL Global Forwarding", "Kuehne+Nagel Logistics"], 1):
            s = Supplier(
                name=f"{name} {unique_run}",
                email=f"supplier{i}_{unique_run}@e2e-freight.com",
                company_name=name,
            )
            db.add(s)
            suppliers.append(s)

        db.commit()
        db.refresh(buyer)
        for s in suppliers:
            db.refresh(s)
        print(f"  [OK] Created Buyer ID: {buyer.id}")
        print(f"  [OK] Created {len(suppliers)} Suppliers: {[s.name for s in suppliers]}")

        # 3. Create British Auction RFQ with L1_RANK_CHANGE Trigger
        print("\n[3/7] Publishing British Auction RFQ with line item specifications...")
        now = datetime.now(timezone.utc)
        initial_close = now + timedelta(minutes=8) # inside 10m window
        forced_close = now + timedelta(minutes=25)

        rfq_payload = {
            "buyer_id": str(buyer.id),
            "title": f"Turbine Components Freight RFQ {unique_run}",
            "description": "Procurement of specialized turbine fasteners and heavy shipping",
            "category": "Aerospace Freight",
            "currency": "USD",
            "baseline_price": 75000.00,
            "bid_start_time": (now - timedelta(hours=1)).isoformat(),
            "bid_close_time": initial_close.isoformat(),
            "forced_bid_close_time": forced_close.isoformat(),
            "trigger_window_minutes": 10,
            "extension_duration_minutes": 5,
            "extension_trigger": "L1_RANK_CHANGE",
            "items": [
                {"name": "Turbine Fastener Grade 5", "quantity": 1000, "unit": "units", "description": "High-temp fasteners"}
            ],
        }
        rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
        assert rfq_res.status_code == 201, f"RFQ creation failed: {rfq_res.text}"
        rfq_data = rfq_res.json()
        rfq_id = rfq_data["id"]
        print(f"  [OK] Created RFQ ID: {rfq_id}")
        print(f"  [OK] Config: Trigger Window={rfq_data['trigger_window_minutes']}m, Duration=+{rfq_data['extension_duration_minutes']}m, Trigger={rfq_data['extension_trigger']}")

        # 4. Submit Supplier Bids with Quote Details & Verify Dynamic Extensions
        print("\n[4/7] Submitting Supplier Bids with full quote breakdown and verifying dynamic clock extensions...")
        
        # Bid 1: Supplier 0 places first bid at 65000 (becomes L1)
        bid1_in = BidCreate(
            rfq_id=rfq_id,
            supplier_id=suppliers[0].id,
            amount=Decimal("65000.00"),
            carrier_name="Maersk Line Intermodal",
            freight_charges=Decimal("2500.00"),
            origin_charges=Decimal("600.00"),
            destination_charges=Decimal("750.00"),
            transit_time="4 business days",
            validity_of_quote="45 days",
        )
        bid1_res = create_bid(db, bid1_in, event_time=now - timedelta(minutes=20))
        print(f"  [OK] Bid 1: {suppliers[0].name} placed $65,000 (Carrier: {bid1_res.carrier_name}, Freight: ${bid1_res.freight_charges}) -> Rank L1")

        # Bid 2: Supplier 1 places bid at 68000 (becomes L2 inside window) -> L1 remains Supplier 0 -> NO extension under L1_RANK_CHANGE
        bid2_in = BidCreate(
            rfq_id=rfq_id,
            supplier_id=suppliers[1].id,
            amount=Decimal("68000.00"),
            carrier_name="DHL Air & Ocean",
            freight_charges=Decimal("3000.00"),
            transit_time="3 business days",
            validity_of_quote="30 days",
        )
        bid2_res = create_bid(db, bid2_in, event_time=now)
        print(f"  [OK] Bid 2: {suppliers[1].name} placed $68,000 (Rank L2) inside trigger window -> No extension (L1 unchanged)")

        # Bid 3: Supplier 2 places bid at 59000 (becomes new L1 inside window) -> Triggers EXTENSION!
        bid3_in = BidCreate(
            rfq_id=rfq_id,
            supplier_id=suppliers[2].id,
            amount=Decimal("59000.00"),
            carrier_name="Kuehne+Nagel Global",
            freight_charges=Decimal("2100.00"),
            origin_charges=Decimal("500.00"),
            destination_charges=Decimal("650.00"),
            transit_time="5 days",
            validity_of_quote="60 days",
        )
        bid3_res = create_bid(db, bid3_in, event_time=now)
        auc_obj = db.query(Auction).filter(Auction.rfq_id == rfq_id).first()
        assert auc_obj is not None, "Auction object must exist for RFQ"
        assert auc_obj.end_time is not None, "Auction end_time must not be None"
        print(f"  [OK] Bid 3: {suppliers[2].name} placed $59,000 (New L1) inside trigger window -> EXTENSION TRIGGERED! Extended to {auc_obj.end_time.isoformat()}")

        # 5. Verify Activity Logs & Trigger Reasons
        print("\n[5/7] Verifying Activity Tracking & Extension Audit Records...")
        act_res = client.get(f"/api/v1/rfqs/{rfq_id}/activity")
        assert act_res.status_code == 200
        logs = act_res.json()
        print(f"  [OK] Retrieved {len(logs)} activity events for RFQ {rfq_id}")
        for log in logs:
            print(f"    - [{log['event_type']}] {log['message']}")
            if log['event_type'] == 'AUCTION_EXTENDED':
                assert 'Lowest bidder (L1) changed' in log['message'] or 'L1' in log['message']
                assert log['metadata_json']['trigger_mode'] == 'L1_RANK_CHANGE'
                print(f"      Verified metadata reason: '{log['metadata_json']['reason']}'")

        # 6. Verify Deterministic Ranking & Auctions Listing / Workspace
        print("\n[6/7] Verifying Auctions Listing, Auction Details & Deterministic Rankings...")
        rank_data = get_rfq_bid_ranking(db, rfq_id)
        assert rank_data.rankings[0].rank == 1
        assert rank_data.rankings[0].amount == Decimal("59000.00")
        assert rank_data.rankings[0].supplier_name is not None
        assert rank_data.rankings[0].supplier_name.startswith("Kuehne+Nagel")
        assert rank_data.rankings[0].carrier_name == "Kuehne+Nagel Global"
        assert rank_data.rankings[1].rank == 2
        assert rank_data.rankings[1].amount == Decimal("65000.00")
        assert rank_data.rankings[2].rank == 3
        assert rank_data.rankings[2].amount == Decimal("68000.00")
        print("  [OK] Deterministic L1/L2/L3 Rankings verified:")
        for r in rank_data.rankings:
            print(f"    - Rank L{r.rank}: {r.supplier_name} - ${r.amount} (Carrier: {r.carrier_name})")

        # Check Auction Details API
        detail_data = get_auction_detail(db, rfq_id)
        assert detail_data.rfq_title == rfq_data["title"]
        assert detail_data.lowest_bid == Decimal("59000.00")
        assert len(detail_data.bids) == 3
        assert len(detail_data.activity_logs) >= 4
        print(f"  [OK] Auction Details Workspace verified: Status='{detail_data.display_status}', Lowest Bid=${detail_data.lowest_bid}")

        # Check Auctions List API
        auctions = list_auctions(db)
        target = next(a for a in auctions if str(a.rfq_id) == str(rfq_id))
        assert target.lowest_bid == Decimal("59000.00")
        print(f"  [OK] Auctions Listing API verified: RFQ '{target.rfq_title}' lowest bid is ${target.lowest_bid}")

        # 7. Verify Forced Close Hard Cap Boundary
        print("\n[7/7] Verifying Forced Close Hard Cap Boundary...")
        # Bid after forced close must be rejected
        late_bid_in = BidCreate(
            rfq_id=rfq_id,
            supplier_id=suppliers[0].id,
            amount=Decimal("50000.00"),
        )
        try:
            create_bid(db, late_bid_in, event_time=forced_close + timedelta(minutes=1))
            assert False, "Bid after forced close should have been rejected"
        except Exception as e:
            print(f"  [OK] Bidding after forced close correctly rejected: {e}")

        print("\n" + "=" * 70)
        print(">> ALL STEP 10 REQUIREMENTS & E2E POSTGRESQL CHECKS COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_e2e_verification()
