import uuid
from decimal import Decimal
import psycopg2
from fastapi.testclient import TestClient

from app.main import app

def main():
    print("==================================================================")
    print("CRITICAL END-TO-END VERIFICATION: EXISTING BUYER REUSE FOR RFQS")
    print("==================================================================")

    client = TestClient(app)

    # 1. Connect to PostgreSQL directly on port 5433
    conn = psycopg2.connect("postgresql://postgres@127.0.0.1:5433/british_auction")
    cur = conn.cursor()
    print("[PASS] Direct PostgreSQL connection established on port 5433.")

    # 2. STEP 1: Create or identify existing Buyer A
    test_buyer_email = f"buyer_alpha_{uuid.uuid4().hex[:6]}@enterprise.com"
    buyer_resp = client.post("/api/v1/buyers", json={
        "name": "Acme Global Procurement",
        "email": test_buyer_email,
        "company_name": "Acme Global Industries",
    })
    assert buyer_resp.status_code == 201, f"Buyer creation failed: {buyer_resp.text}"
    buyer_a = buyer_resp.json()
    buyer_a_id = buyer_a["id"]
    print(f"[PASS] STEP 1: Created initial Buyer A: '{buyer_a['name']}' | {buyer_a['email']} (ID: {buyer_a_id})")

    # Verify Buyer A is present in GET /api/v1/buyers
    list_resp = client.get("/api/v1/buyers?limit=100")
    assert list_resp.status_code == 200, f"List buyers failed: {list_resp.text}"
    buyers_list = list_resp.json()
    assert any(b["id"] == buyer_a_id for b in buyers_list), f"Buyer A {buyer_a_id} not found in GET /api/v1/buyers"
    print(f"[PASS] STEP 1b: Buyer A successfully listed in GET /api/v1/buyers (Total loaded: {len(buyers_list)})")

    # 3. STEP 2: Create RFQ A using existing Buyer A
    rfq_a_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_a_id,
        "title": "Precision Aerospace CNC Components",
        "description": "High Precision Titanium Turbine Blades",
        "category": "Aerospace",
        "currency": "USD",
        "baseline_price": 120000.00,
        "items": [
            {"name": "Turbine Blade Set", "quantity": 25, "unit": "sets"},
            {"name": "Mounting Hardware Kit", "quantity": 50, "unit": "kits"},
        ],
    })
    assert rfq_a_resp.status_code == 201, f"RFQ A creation failed: {rfq_a_resp.text}"
    rfq_a = rfq_a_resp.json()
    rfq_a_id = rfq_a["id"]
    print(f"[PASS] STEP 2: RFQ A created with Buyer A: '{rfq_a['title']}' (RFQ ID: {rfq_a_id}, Buyer ID: {rfq_a['buyer_id']})")

    # 4. STEP 3: Return to Create RFQ and select the SAME Buyer A for RFQ B
    rfq_b_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_a_id,
        "title": "Industrial Hydraulic Pump Assemblies",
        "description": "High Pressure Fluid Power Pumps",
        "category": "Hydraulics",
        "currency": "USD",
        "baseline_price": 85000.00,
        "items": [
            {"name": "Hydraulic Axial Pump 350bar", "quantity": 10, "unit": "units"},
        ],
    })
    assert rfq_b_resp.status_code == 201, f"RFQ B creation failed: {rfq_b_resp.text}"
    rfq_b = rfq_b_resp.json()
    rfq_b_id = rfq_b["id"]
    print(f"[PASS] STEP 3: RFQ B created with SAME Buyer A: '{rfq_b['title']}' (RFQ ID: {rfq_b_id}, Buyer ID: {rfq_b['buyer_id']})")

    # 5. STEP 4: Verify PostgreSQL records for Buyer A
    cur.execute("SELECT id, name, email, company_name FROM buyers WHERE email = %s", (test_buyer_email,))
    buyer_records = cur.fetchall()
    print("\n--- PostgreSQL Buyer Records Check ---")
    print(f"Query: SELECT id, name, email, company_name FROM buyers WHERE email = '{test_buyer_email}';")
    print(f"Found {len(buyer_records)} buyer record(s):")
    for r in buyer_records:
        print(f"  -> ID: {r[0]} | Name: {r[1]} | Email: {r[2]} | Company: {r[3]}")
    assert len(buyer_records) == 1, f"Expected exactly 1 buyer record, found {len(buyer_records)}"
    print("[PASS] EXACTLY ONE buyer record exists in PostgreSQL for the buyer.")

    # 6. STEP 5: Verify both RFQs exist in PostgreSQL referencing Buyer A's ID
    cur.execute("""
        SELECT r.id, r.buyer_id, r.title, r.baseline_price, r.status, COUNT(i.id) as item_count
        FROM rfqs r
        LEFT JOIN rfq_items i ON r.id = i.rfq_id
        WHERE r.buyer_id = %s
        GROUP BY r.id, r.buyer_id, r.title, r.baseline_price, r.status
        ORDER BY r.created_at ASC
    """, (buyer_a_id,))
    db_rfqs = cur.fetchall()
    print("\n--- PostgreSQL RFQs Verification for Buyer A ---")
    print(f"Total RFQs for Buyer {buyer_a_id}: {len(db_rfqs)}")
    for r in db_rfqs:
        print(f"  -> RFQ ID: {r[0]} | Buyer ID: {r[1]} | Title: '{r[2]}' | Price: ${r[3]} | Status: {r[4]} | Items: {r[5]}")

    rfq_ids = [str(r[0]) for r in db_rfqs]
    assert rfq_a_id in rfq_ids, f"RFQ A {rfq_a_id} not found in DB for Buyer A"
    assert rfq_b_id in rfq_ids, f"RFQ B {rfq_b_id} not found in DB for Buyer A"

    rfq_a_row = next(r for r in db_rfqs if str(r[0]) == rfq_a_id)
    rfq_b_row = next(r for r in db_rfqs if str(r[0]) == rfq_b_id)

    assert str(rfq_a_row[1]) == str(rfq_b_row[1]) == buyer_a_id
    assert Decimal(str(rfq_a_row[3])) == Decimal("120000.00")
    assert Decimal(str(rfq_b_row[3])) == Decimal("85000.00")
    print("[PASS] Both RFQs correctly reference Buyer A in PostgreSQL without duplicate buyer rows.")

    # 7. STEP 6: Verify Create New Buyer Workflow & Automatic Selection for RFQ C
    new_buyer_email = f"buyer_new_{uuid.uuid4().hex[:6]}@newenterprise.com"
    new_buyer_resp = client.post("/api/v1/buyers", json={
        "name": "NexGen Dynamics",
        "email": new_buyer_email,
        "company_name": "NexGen Dynamics International",
    })
    assert new_buyer_resp.status_code == 201, f"New buyer creation failed: {new_buyer_resp.text}"
    buyer_c = new_buyer_resp.json()
    buyer_c_id = buyer_c["id"]
    print(f"\n[PASS] STEP 6: Created New Buyer C: '{buyer_c['name']}' | {buyer_c['email']} (ID: {buyer_c_id})")

    rfq_c_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_c_id,
        "title": "Quantum Sensor Array Project",
        "description": "Sub-atomic resolution sensors",
        "currency": "USD",
        "baseline_price": 250000.00,
        "items": [
            {"name": "Quantum Optical Sensor", "quantity": 4, "unit": "units"},
        ],
    })
    assert rfq_c_resp.status_code == 201, f"RFQ C creation failed: {rfq_c_resp.text}"
    rfq_c = rfq_c_resp.json()
    assert rfq_c["buyer_id"] == buyer_c_id
    print(f"[PASS] STEP 6b: Successfully created RFQ C using newly created Buyer C (RFQ ID: {rfq_c['id']})")

    # 8. STEP 7: Verify Duplicate Email Rejection
    dup_resp = client.post("/api/v1/buyers", json={
        "name": "Duplicate Attempt",
        "email": test_buyer_email,
    })
    assert dup_resp.status_code == 409, f"Expected 409 Conflict, got: {dup_resp.status_code}"
    print(f"[PASS] STEP 7: Duplicate email '{test_buyer_email}' correctly rejected with 409 Conflict.")

    print("\n==================================================================")
    print("BUYER REUSE E2E & DATABASE VERIFICATION: ALL CHECKS PASSED!")
    print("==================================================================")

    conn.close()

if __name__ == "__main__":
    main()
