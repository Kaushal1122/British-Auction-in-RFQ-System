import uuid
from decimal import Decimal
import psycopg2
from fastapi.testclient import TestClient

from app.main import app

def main():
    print("==================================================================")
    print("CRITICAL END-TO-END VERIFICATION: EXISTING SUPPLIER REUSE")
    print("==================================================================")

    client = TestClient(app)

    # 1. Connect to PostgreSQL directly
    conn = psycopg2.connect("postgresql://postgres@127.0.0.1:5433/british_auction")
    cur = conn.cursor()
    print("[PASS] Direct PostgreSQL connection established on port 5433.")

    # 2. Create a Buyer
    buyer_email = f"buyer_{uuid.uuid4().hex[:6]}@procurement.com"
    buyer_resp = client.post("/api/v1/buyers", json={
        "name": "Global Aerospace Corp",
        "email": buyer_email,
        "company_name": "Global Aerospace Industries",
    })
    assert buyer_resp.status_code == 201, f"Buyer creation failed: {buyer_resp.text}"
    buyer = buyer_resp.json()
    buyer_id = buyer["id"]
    print(f"[PASS] Buyer created: {buyer['name']} (ID: {buyer_id})")

    # 3. STEP 1: Create or identify existing supplier Kaushal Kumar
    test_email = "kk795109@gmail.com"
    # Check if supplier already exists in DB or create
    cur.execute("SELECT id, name, email, company_name FROM suppliers WHERE email = %s", (test_email,))
    existing_row = cur.fetchone()

    if existing_row:
        supplier_id = str(existing_row[0])
        print(f"[PASS] STEP 1: Identified existing supplier: {existing_row[1]} | {existing_row[2]} (ID: {supplier_id})")
    else:
        sup_resp = client.post("/api/v1/suppliers", json={
            "name": "Kaushal Kumar",
            "email": test_email,
            "company_name": "ABC Company",
        })
        assert sup_resp.status_code == 201, f"Supplier creation failed: {sup_resp.text}"
        supplier = sup_resp.json()
        supplier_id = supplier["id"]
        print(f"[PASS] STEP 1: Created supplier: {supplier['name']} | {supplier['email']} (ID: {supplier_id})")

    # 4. STEP 2: Create RFQ #1 and submit bid $47,000
    rfq1_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Industrial Component Procurement",
        "description": "High Precision Titanium Components",
        "category": "Industrial",
        "currency": "USD",
        "baseline_price": 50000.00,
        "items": [
            {"name": "Titanium Bearing", "quantity": 100, "unit": "units"},
        ],
    })
    assert rfq1_resp.status_code == 201, f"RFQ 1 creation failed: {rfq1_resp.text}"
    rfq1 = rfq1_resp.json()
    rfq1_id = rfq1["id"]
    print(f"[PASS] STEP 2: RFQ #1 created: '{rfq1['title']}' (ID: {rfq1_id})")

    bid1_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq1_id,
        "supplier_id": supplier_id,
        "amount": 47000.00,
    })
    assert bid1_resp.status_code == 201, f"Bid #1 failed: {bid1_resp.text}"
    bid1 = bid1_resp.json()
    print(f"[PASS] STEP 2: Bid #1 submitted: RFQ #1 -> Supplier S1 (Amount: ${bid1['amount']}, Bid ID: {bid1['id']})")

    # 5. STEP 3: Create RFQ #2 (Another Procurement RFQ)
    rfq2_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Another Procurement RFQ",
        "description": "Electronic Sensor Assemblies",
        "category": "Electronics",
        "currency": "USD",
        "baseline_price": 60000.00,
        "items": [
            {"name": "Pressure Sensor 10bar", "quantity": 50, "unit": "units"},
        ],
    })
    assert rfq2_resp.status_code == 201, f"RFQ 2 creation failed: {rfq2_resp.text}"
    rfq2 = rfq2_resp.json()
    rfq2_id = rfq2["id"]
    print(f"[PASS] STEP 3: RFQ #2 created: '{rfq2['title']}' (ID: {rfq2_id})")

    # 6. STEP 4: Submit Bid #2 for RFQ #2 using the SAME supplier_id
    bid2_resp = client.post("/api/v1/bids", json={
        "rfq_id": rfq2_id,
        "supplier_id": supplier_id,
        "amount": 45000.00,
    })
    assert bid2_resp.status_code == 201, f"Bid #2 failed: {bid2_resp.text}"
    bid2 = bid2_resp.json()
    print(f"[PASS] STEP 4: Bid #2 submitted: RFQ #2 -> SAME Supplier S1 (Amount: ${bid2['amount']}, Bid ID: {bid2['id']})")

    # 7. STEP 5: Verify supplier uniqueness in PostgreSQL
    cur.execute("SELECT id, name, email, company_name FROM suppliers WHERE email = %s", (test_email,))
    supplier_records = cur.fetchall()
    print("\n--- PostgreSQL Supplier Records Check ---")
    print(f"Query: SELECT id, name, email, company_name FROM suppliers WHERE email = '{test_email}';")
    print(f"Found {len(supplier_records)} supplier record(s):")
    for r in supplier_records:
        print(f"  -> ID: {r[0]} | Name: {r[1]} | Email: {r[2]} | Company: {r[3]}")
    assert len(supplier_records) == 1, f"Expected exactly 1 supplier record, found {len(supplier_records)}"
    print("[PASS] EXACTLY ONE supplier record exists for kk795109@gmail.com.")

    # 8. STEP 6: Verify both bids in PostgreSQL reference the SAME supplier_id
    cur.execute("""
        SELECT b.id, b.supplier_id, a.rfq_id, b.amount, b.is_valid, b.submitted_at
        FROM bids b
        JOIN auctions a ON b.auction_id = a.id
        WHERE b.supplier_id = %s
        ORDER BY b.submitted_at ASC
    """, (supplier_id,))
    db_bids = cur.fetchall()
    print("\n--- PostgreSQL Bids Verification for Supplier S1 ---")
    print(f"Total Bids for Supplier {supplier_id}: {len(db_bids)}")
    for b in db_bids:
        print(f"  -> Bid ID: {b[0]} | Supplier ID: {b[1]} | RFQ ID: {b[2]} | Amount: ${b[3]} | Valid: {b[4]}")

    # Ensure at least bid1 and bid2 are among the records
    bid_ids = [str(b[0]) for b in db_bids]
    assert bid1["id"] in bid_ids, f"Bid 1 {bid1['id']} not found in DB"
    assert bid2["id"] in bid_ids, f"Bid 2 {bid2['id']} not found in DB"

    # Verify both reference the SAME supplier_id
    bid1_record = next(b for b in db_bids if str(b[0]) == bid1["id"])
    bid2_record = next(b for b in db_bids if str(b[0]) == bid2["id"])

    assert str(bid1_record[1]) == str(bid2_record[1]) == supplier_id
    assert str(bid1_record[2]) == rfq1_id
    assert str(bid2_record[2]) == rfq2_id
    assert Decimal(str(bid1_record[3])) == Decimal("47000.00")
    assert Decimal(str(bid2_record[3])) == Decimal("45000.00")

    print("\n==================================================================")
    print("E2E & DATABASE VERIFICATION: ALL CHECKS PASSED SUCCESSFULLY!")
    print("==================================================================")

    conn.close()

if __name__ == "__main__":
    main()
