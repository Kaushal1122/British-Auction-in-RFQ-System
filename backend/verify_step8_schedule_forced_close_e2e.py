import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_URL = "http://127.0.0.1:8000/api/v1"
DB_URL = "postgresql://postgres@127.0.0.1:5433/british_auction"

def log(msg):
    print(f"[STEP 8 E2E] {msg}")

def main():
    log("================================================================================")
    log("STEP 8 FIX: AUCTION SCHEDULE VALIDATION & FORCED CLOSE E2E VERIFICATION")
    log("================================================================================")

    # 1. Test Database connection
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    log("Successfully connected to PostgreSQL on port 5433.")

    # 2. Create Buyer & Suppliers via real FastAPI endpoints
    buyer_email = f"buyer.step8.{uuid.uuid4().hex[:6]}@example.com"
    buyer_resp = httpx.post(f"{BASE_URL}/buyers", json={"name": "Alice Buyer", "email": buyer_email, "company_name": "Aerospace Global"})
    assert buyer_resp.status_code == 201, f"Failed to create buyer: {buyer_resp.text}"
    buyer_id = buyer_resp.json()["id"]
    log(f"Created Buyer: id={buyer_id}, email={buyer_email}")

    suppliers = []
    for i in range(1, 8):
        sup_resp = httpx.post(f"{BASE_URL}/suppliers", json={"name": f"Supplier {i}", "email": f"sup{i}.step8.{uuid.uuid4().hex[:6]}@example.com", "company_name": f"Supplier {i} Corp"})
        assert sup_resp.status_code == 201, f"Failed to create supplier {i}: {sup_resp.text}"
        suppliers.append(sup_resp.json()["id"])
    log(f"Created {len(suppliers)} Suppliers.")

    # 3. Test Schedule Validation on POST /api/v1/rfqs
    log("--- Testing API Schedule Validations ---")
    
    # Case A: Start > Close
    r_a = httpx.post(f"{BASE_URL}/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Invalid Chronology A",
        "baseline_price": 50000,
        "bid_start_time": "2026-08-29T02:40:00Z",
        "bid_close_time": "2026-08-29T02:24:00Z",
        "forced_bid_close_time": "2026-08-29T03:00:00Z",
        "items": [{"name": "Item 1", "quantity": 10, "unit": "units"}],
    })
    assert r_a.status_code == 422, f"Expected 422 for start > close, got {r_a.status_code}: {r_a.text}"
    log("Case A (Start > Close): Correctly rejected with 422.")

    # Case B: Close > Forced Close
    r_b = httpx.post(f"{BASE_URL}/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Invalid Chronology B",
        "baseline_price": 50000,
        "bid_start_time": "2026-08-29T02:24:00Z",
        "bid_close_time": "2026-08-29T02:40:00Z",
        "forced_bid_close_time": "2026-08-29T02:34:00Z",
        "items": [{"name": "Item 1", "quantity": 10, "unit": "units"}],
    })
    assert r_b.status_code == 422, f"Expected 422 for close > forced, got {r_b.status_code}: {r_b.text}"
    log("Case B (Close > Forced Close): Correctly rejected with 422.")

    # Case C: Start == Close
    r_c = httpx.post(f"{BASE_URL}/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Invalid Chronology C",
        "baseline_price": 50000,
        "bid_start_time": "2026-08-29T02:40:00Z",
        "bid_close_time": "2026-08-29T02:40:00Z",
        "forced_bid_close_time": "2026-08-29T03:00:00Z",
        "items": [{"name": "Item 1", "quantity": 10, "unit": "units"}],
    })
    assert r_c.status_code == 422, f"Expected 422 for start == close, got {r_c.status_code}: {r_c.text}"
    log("Case C (Start == Close): Correctly rejected with 422.")

    # Case D: Close == Forced Close
    r_d = httpx.post(f"{BASE_URL}/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Invalid Chronology D",
        "baseline_price": 50000,
        "bid_start_time": "2026-08-29T02:24:00Z",
        "bid_close_time": "2026-08-29T03:00:00Z",
        "forced_bid_close_time": "2026-08-29T03:00:00Z",
        "items": [{"name": "Item 1", "quantity": 10, "unit": "units"}],
    })
    assert r_d.status_code == 422, f"Expected 422 for close == forced, got {r_d.status_code}: {r_d.text}"
    log("Case D (Close == Forced Close): Correctly rejected with 422.")

    # 4. Create Valid RFQ with full Schedule & British Auction Configuration
    start_dt = datetime(2026, 8, 29, 2, 24, 0, tzinfo=timezone.utc)
    close_dt = datetime(2026, 8, 29, 2, 40, 0, tzinfo=timezone.utc)
    forced_dt = datetime(2026, 8, 29, 3, 0, 0, tzinfo=timezone.utc)

    valid_payload = {
        "buyer_id": buyer_id,
        "title": "Industrial High-Precision Valves",
        "description": "British Auction dynamic procurement test",
        "category": "Industrial Valves",
        "currency": "USD",
        "baseline_price": 100000.00,
        "bid_start_time": start_dt.isoformat(),
        "bid_close_time": close_dt.isoformat(),
        "forced_bid_close_time": forced_dt.isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "BID_RECEIVED",
        "items": [
            {"name": "DN50 Gate Valve", "quantity": 25, "unit": "pcs"},
            {"name": "DN100 Check Valve", "quantity": 10, "unit": "pcs"},
        ],
    }

    create_resp = httpx.post(f"{BASE_URL}/rfqs", json=valid_payload)
    assert create_resp.status_code == 201, f"Failed to create valid RFQ: {create_resp.text}"
    rfq_data = create_resp.json()
    rfq_id = rfq_data["id"]
    log(f"Created Valid RFQ: id={rfq_id}")

    # 5. Direct Database Persistence Verification in PostgreSQL
    log("--- Verifying PostgreSQL Persistence ---")
    cursor.execute("SELECT * FROM rfqs WHERE id = %s", (rfq_id,))
    db_rfq = cursor.fetchone()
    assert db_rfq is not None
    assert db_rfq["title"] == "Industrial High-Precision Valves"
    assert db_rfq["baseline_price"] == Decimal("100000.00")

    cursor.execute("SELECT * FROM auctions WHERE rfq_id = %s", (rfq_id,))
    db_auction = cursor.fetchone()
    assert db_auction is not None
    assert db_auction["start_time"] == start_dt
    assert db_auction["end_time"] == close_dt
    assert db_auction["forced_bid_close_time"] == forced_dt
    assert db_auction["trigger_window_minutes"] == 10
    assert db_auction["extension_duration_minutes"] == 5
    assert db_auction["extension_trigger"] == "BID_RECEIVED"
    log("PostgreSQL Auction record verified: start, close, forced close, X=10, Y=5, trigger=BID_RECEIVED are correctly stored.")

    cursor.execute("SELECT * FROM rfq_items WHERE rfq_id = %s", (rfq_id,))
    db_items = cursor.fetchall()
    assert len(db_items) == 2
    log(f"PostgreSQL RFQ items verified: {len(db_items)} items persisted.")

    # 6. Test Extension Logic & Forced Close Cap using direct service or API with timestamps
    # We will test bidding lifecycle directly using the backend service logic
    from app.db.database import SessionLocal
    from app.models.auction import Auction
    from app.schemas.bid import BidCreate
    from app.services.bid_service import create_bid
    from fastapi import HTTPException

    db_session = SessionLocal()
    try:
        # Test Lifecycle: Bid before start time (e.g. 02:20 UTC)
        log("--- Testing Lifecycle: Bid Before Start Time ---")
        try:
            create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[0]), amount=Decimal("95000.00")), event_time=datetime(2026, 8, 29, 2, 20, 0, tzinfo=timezone.utc))
            assert False, "Should have rejected bid before start time"
        except HTTPException as e:
            assert e.status_code == 400
            log(f"Bid before start time correctly rejected: {e.detail}")

        # Test Bid Outside Trigger Window: at 02:26 (close is 02:40, trigger window is [02:30, 02:40])
        log("--- Testing Bid Outside Trigger Window (02:26) ---")
        bid1 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[0]), amount=Decimal("95000.00")), event_time=datetime(2026, 8, 29, 2, 26, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == close_dt, f"Expected close {close_dt}, got {cur_close}"
        log(f"Bid at 02:26 outside window: Close time remains unchanged at {cur_close.strftime('%H:%M')}.")

        # Test Bid Inside Trigger Window 1: at 02:35 (inside [02:30, 02:40]) -> extends close by +5 min to 02:45
        log("--- Testing Qualifying Bid Inside Trigger Window (02:35) ---")
        bid2 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[1]), amount=Decimal("92000.00")), event_time=datetime(2026, 8, 29, 2, 35, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == datetime(2026, 8, 29, 2, 45, 0, tzinfo=timezone.utc), f"Expected close 02:45, got {cur_close}"
        log(f"Bid at 02:35 inside window: Close time extended to {cur_close.strftime('%H:%M')} (+5 mins).")

        # Test Subsequent Bid in NEW Window [02:35, 02:45]: at 02:42 -> extends close to 02:50
        log("--- Testing Second Qualifying Extension (02:42) ---")
        bid3 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[2]), amount=Decimal("89000.00")), event_time=datetime(2026, 8, 29, 2, 42, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == datetime(2026, 8, 29, 2, 50, 0, tzinfo=timezone.utc), f"Expected close 02:50, got {cur_close}"
        log(f"Bid at 02:42 inside new window: Close time extended to {cur_close.strftime('%H:%M')} (+5 mins).")

        # Test Third Qualifying Extension in [02:40, 02:50]: at 02:48 -> extends close to 02:55
        log("--- Testing Third Qualifying Extension (02:48) ---")
        bid4 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[3]), amount=Decimal("86000.00")), event_time=datetime(2026, 8, 29, 2, 48, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == datetime(2026, 8, 29, 2, 55, 0, tzinfo=timezone.utc), f"Expected close 02:55, got {cur_close}"
        log(f"Bid at 02:48 inside new window: Close time extended to {cur_close.strftime('%H:%M')} (+5 mins).")

        # Test Fourth Qualifying Extension in [02:45, 02:55]: at 02:53 -> requested 03:00, capped at Forced Close 03:00
        log("--- Testing Fourth Extension Reaching Forced Close Cap (02:53) ---")
        bid5 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[4]), amount=Decimal("83000.00")), event_time=datetime(2026, 8, 29, 2, 53, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == forced_dt, f"Expected close capped at {forced_dt}, got {cur_close}"
        log(f"Bid at 02:53 inside new window: Close time reaches Forced Close cap at {cur_close.strftime('%H:%M')}.")

        # Test Fifth Bid when Close == Forced Close (02:58): Cannot extend beyond 03:00
        log("--- Testing Fifth Bid At Forced Close Boundary (02:58) ---")
        bid6 = create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[5]), amount=Decimal("80000.00")), event_time=datetime(2026, 8, 29, 2, 58, 0, tzinfo=timezone.utc))
        cursor.execute("SELECT end_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
        cur_close = cursor.fetchone()["end_time"]
        assert cur_close == forced_dt, f"Close time exceeded forced close! Got {cur_close}"
        assert bid6.auction_extended is False
        log(f"Bid at 02:58: Close time strictly remains {cur_close.strftime('%H:%M')} (FORCED CLOSE CAP HONORED).")

        # Test Bid After Forced Close: at 03:05
        log("--- Testing Bid After Forced Close (03:05) ---")
        try:
            create_bid(db_session, BidCreate(rfq_id=uuid.UUID(rfq_id), supplier_id=uuid.UUID(suppliers[6]), amount=Decimal("78000.00")), event_time=datetime(2026, 8, 29, 3, 5, 0, tzinfo=timezone.utc))
            assert False, "Should have rejected bid after forced close"
        except HTTPException as e:
            assert e.status_code == 400
            log(f"Bid after forced close correctly rejected: {e.detail}")

    finally:
        db_session.close()

    # 7. Final Database Inspection
    cursor.execute("SELECT end_time, forced_bid_close_time FROM auctions WHERE id = %s", (str(db_auction["id"]),))
    final_row = cursor.fetchone()
    assert final_row["end_time"] <= final_row["forced_bid_close_time"]
    assert final_row["end_time"] == forced_dt
    log(f"Final PostgreSQL verification: Auction end_time ({final_row['end_time']}) == forced_bid_close_time ({final_row['forced_bid_close_time']}).")
    log("================================================================================")
    log("ALL STEP 8 E2E VERIFICATIONS PASSED SUCCESSFULLY!")
    log("================================================================================")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
