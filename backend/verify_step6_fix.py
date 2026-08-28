import uuid
from decimal import Decimal
import psycopg2
from fastapi.testclient import TestClient

from app.main import app

def main():
    print("==================================================================")
    print("STEP 6 VERIFICATION: ALLOW SAME BIDDER TO BID ON MULTIPLE RFQS")
    print("==================================================================")

    client = TestClient(app)

    # 1. Create Buyer
    buyer_resp = client.post("/api/v1/buyers", json={
        "name": "Global Manufacturing Corp",
        "email": f"buyer_{uuid.uuid4().hex[:6]}@globalmfg.com",
        "company_name": "Global Manufacturing",
    })
    assert buyer_resp.status_code == 201, f"Buyer creation failed: {buyer_resp.text}"
    buyer = buyer_resp.json()
    print(f"[PASS] Buyer created: {buyer['name']} (ID: {buyer['id']})")

    # 2. STEP 1: Create Supplier / Bidder A
    sup_a_resp = client.post("/api/v1/suppliers", json={
        "name": "Supplier Alpha",
        "email": f"alpha_{uuid.uuid4().hex[:6]}@alpha.com",
        "company_name": "Alpha Technologies",
    })
    assert sup_a_resp.status_code == 201, f"Supplier A creation failed: {sup_a_resp.text}"
    sup_a = sup_a_resp.json()
    print(f"[PASS] STEP 1: Supplier A created: {sup_a['name']} (ID: {sup_a['id']})")

    # 3. STEP 2: Create RFQ 1
    rfq1_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer["id"],
        "title": "RFQ 1 - Industrial Bearings",
        "description": "High Precision Ball Bearings",
        "category": "Industrial",
        "currency": "USD",
        "baseline_price": 50000.00,
        "items": [
            {"name": "Bearing Set A", "quantity": 100, "unit": "sets"},
        ],
    })
    assert rfq1_resp.status_code == 201, f"RFQ 1 creation failed: {rfq1_resp.text}"
    rfq1 = rfq1_resp.json()
    print(f"[PASS] STEP 2: RFQ 1 created: {rfq1['title']} (ID: {rfq1['id']})")

    # 4. STEP 3: Submit bid from Supplier A on RFQ 1
    bid1_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq1["id"],
        "supplier_id": sup_a["id"],
        "amount": 48000.00,
    })
    assert bid1_resp.status_code == 201, f"Bid 1 failed: {bid1_resp.text}"
    bid1 = bid1_resp.json()
    print(f"[PASS] STEP 3: Supplier A -> RFQ 1: SUCCESS (Bid ID: {bid1['id']}, Amount: ${bid1['amount']})")

    # 5. STEP 4: Create RFQ 2
    rfq2_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer["id"],
        "title": "RFQ 2 - Linear Actuators",
        "description": "Hydraulic Linear Actuators",
        "category": "Automation",
        "currency": "USD",
        "baseline_price": 80000.00,
        "items": [
            {"name": "Actuator Unit 500mm", "quantity": 25, "unit": "units"},
        ],
    })
    assert rfq2_resp.status_code == 201, f"RFQ 2 creation failed: {rfq2_resp.text}"
    rfq2 = rfq2_resp.json()
    print(f"[PASS] STEP 4: RFQ 2 created: {rfq2['title']} (ID: {rfq2['id']})")

    # 6. STEP 5: Using the SAME Supplier A, submit a bid on RFQ 2
    bid2_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq2["id"],
        "supplier_id": sup_a["id"],
        "amount": 74000.00,
    })
    assert bid2_resp.status_code == 201, f"Bid 2 failed: {bid2_resp.text}"
    bid2 = bid2_resp.json()
    print(f"[PASS] STEP 5: Supplier A -> RFQ 2: SUCCESS (Bid ID: {bid2['id']}, Amount: ${bid2['amount']})")

    # 7. STEP 6: Go back to RFQ 1, try submitting another bid using Supplier A -> must be REJECTED as duplicate
    dup_bid_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq1["id"],
        "supplier_id": sup_a["id"],
        "amount": 47000.00,
    })
    assert dup_bid_resp.status_code == 400, f"Expected 400 for duplicate bid, got {dup_bid_resp.status_code}: {dup_bid_resp.text}"
    dup_detail = dup_bid_resp.json()["detail"]
    print(f"[PASS] STEP 6: Supplier A -> RFQ 1 (Duplicate): REJECTED as expected (HTTP 400, Detail: '{dup_detail}')")

    # 8. STEP 7: Check PostgreSQL directly
    conn = psycopg2.connect("postgresql://postgres@127.0.0.1:5433/british_auction")
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.supplier_id, a.rfq_id, b.amount, b.is_valid
        FROM bids b
        JOIN auctions a ON b.auction_id = a.id
        WHERE b.supplier_id = %s
        ORDER BY b.submitted_at ASC
    """, (sup_a["id"],))
    db_records = cur.fetchall()

    assert len(db_records) == 2, f"Expected 2 bid records for Supplier A in DB, found {len(db_records)}"
    print(f"\n[PASS] STEP 7: PostgreSQL Direct Verification:")
    print("   -------------------------------------------------------------------------")
    print(f"   Record 1: Bid ID {db_records[0][0]} | Supplier A | RFQ 1 ({db_records[0][2]}) | ${db_records[0][3]}")
    print(f"   Record 2: Bid ID {db_records[1][0]} | Supplier A | RFQ 2 ({db_records[1][2]}) | ${db_records[1][3]}")
    print("   -------------------------------------------------------------------------")
    assert str(db_records[0][2]) == rfq1["id"]
    assert str(db_records[1][2]) == rfq2["id"]

    # 9. STEP 8: Create Supplier B and submit on RFQ 1
    sup_b_resp = client.post("/api/v1/suppliers", json={
        "name": "Supplier Beta",
        "email": f"beta_{uuid.uuid4().hex[:6]}@beta.com",
    })
    sup_b = sup_b_resp.json()
    bid3_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq1["id"],
        "supplier_id": sup_b["id"],
        "amount": 46000.00,
    })
    assert bid3_resp.status_code == 201
    print(f"\n[PASS] Multiple bidders on same RFQ: Supplier B -> RFQ 1: SUCCESS (${bid3_resp.json()['amount']})")

    # 10. Check RFQ Isolation
    rfq1_bids = client.get(f"/api/v1/bids/rfq/{rfq1['id']}").json()
    rfq2_bids = client.get(f"/api/v1/bids/rfq/{rfq2['id']}").json()
    assert len(rfq1_bids) == 2, f"Expected 2 bids for RFQ 1, got {len(rfq1_bids)}"
    assert len(rfq2_bids) == 1, f"Expected 1 bid for RFQ 2, got {len(rfq2_bids)}"
    print(f"[PASS] RFQ Isolation verified: RFQ 1 has {len(rfq1_bids)} bids, RFQ 2 has {len(rfq2_bids)} bids.")

    print("\n==================================================================")
    print("ALL STEP 6 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    main()
