import psycopg2
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=================================================================")
print("=== STEP 7 LIVE POSTGRESQL & API END-TO-END RANKING VERIFICATION ===")
print("=================================================================")

# 1. Direct DB Connection
conn = psycopg2.connect("postgresql://postgres@127.0.0.1:5433/british_auction")
cur = conn.cursor()
print("-> PostgreSQL connection established on port 5433.")

# 2. Create Buyer
buyer_res = client.post("/api/v1/buyers", json={
    "name": "Global Aerospace Corp",
    "email": f"procurement_{uuid.uuid4().hex[:6]}@aerospace.com",
    "company_name": "Global Aerospace Systems"
})
assert buyer_res.status_code == 201
buyer = buyer_res.json()
print(f"-> Created Buyer: {buyer['name']} (ID: {buyer['id']})")

# 3. Create RFQ A (USD)
rfq_a_res = client.post("/api/v1/rfqs", json={
    "buyer_id": buyer["id"],
    "title": "Industrial Component Procurement",
    "description": "Grade 5 Titanium turbine shafts",
    "category": "Aerospace",
    "currency": "USD",
    "baseline_price": 75000.00,
    "items": [
        {"name": "Titanium Turbine Shaft", "quantity": 50, "unit": "units"}
    ]
})
assert rfq_a_res.status_code == 201
rfq_a = rfq_a_res.json()
print(f"-> Created RFQ A: '{rfq_a['title']}' (ID: {rfq_a['id']}, Baseline: {rfq_a['baseline_price']} {rfq_a['currency']})")

# 4. Verify Empty Ranking for RFQ A before any bids
rank_empty_res = client.get(f"/api/v1/rfqs/{rfq_a['id']}/ranking")
assert rank_empty_res.status_code == 200
rank_empty = rank_empty_res.json()
assert rank_empty["total_bids"] == 0
assert rank_empty["rankings"] == []
print(f"-> Empty Ranking Verification: PASSED (total_bids=0, rankings=[])")

# 5. Create 3 Suppliers
suppliers = []
supplier_specs = [
    ("Supplier Alpha", "Alpha Dynamics Ltd"),
    ("Supplier Beta", "Beta Precision Engineering"),
    ("Supplier Gamma", "Gamma Advanced Alloys"),
]
for name, company in supplier_specs:
    s_res = client.post("/api/v1/suppliers", json={
        "name": name,
        "email": f"bids_{uuid.uuid4().hex[:6]}@{name.lower().replace(' ', '')}.com",
        "company_name": company
    })
    assert s_res.status_code == 201
    s = s_res.json()
    suppliers.append(s)
    print(f"-> Created Supplier: {s['name']} (ID: {s['id']})")

sup_alpha, sup_beta, sup_gamma = suppliers

# 6. Submit 3 Bids for RFQ A
# Supplier Alpha -> 48000
# Supplier Beta  -> 45000
# Supplier Gamma -> 47000
b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_a["id"], "supplier_id": sup_alpha["id"], "amount": 48000.00})
b2 = client.post("/api/v1/bids", json={"rfq_id": rfq_a["id"], "supplier_id": sup_beta["id"], "amount": 45000.00})
b3 = client.post("/api/v1/bids", json={"rfq_id": rfq_a["id"], "supplier_id": sup_gamma["id"], "amount": 47000.00})
assert b1.status_code == 201
assert b2.status_code == 201
assert b3.status_code == 201
print(f"-> Submitted 3 Bids: Alpha ($48,000), Beta ($45,000), Gamma ($47,000)")

# 7. Query Ranking for RFQ A
rank_res = client.get(f"/api/v1/rfqs/{rfq_a['id']}/ranking")
assert rank_res.status_code == 200
ranking = rank_res.json()
print("\n--- Current RFQ A Bid Rankings ---")
print(f"RFQ: {ranking['rfq_title']} | Currency: {ranking['currency']} | Total Valid Bids: {ranking['total_bids']}")
for item in ranking["rankings"]:
    amt = float(item['amount'])
    print(f"  Rank {item['rank']}: {item['supplier_name']} ({item['supplier_company']}) -> ${amt:,.2f} (Bid ID: {item['bid_id']})")


# Assertions for Ranking Order
assert ranking["total_bids"] == 3
assert ranking["rankings"][0]["rank"] == 1
assert ranking["rankings"][0]["supplier_id"] == sup_beta["id"]
assert Decimal(str(ranking["rankings"][0]["amount"])) == Decimal("45000.00")

assert ranking["rankings"][1]["rank"] == 2
assert ranking["rankings"][1]["supplier_id"] == sup_gamma["id"]
assert Decimal(str(ranking["rankings"][1]["amount"])) == Decimal("47000.00")

assert ranking["rankings"][2]["rank"] == 3
assert ranking["rankings"][2]["supplier_id"] == sup_alpha["id"]
assert Decimal(str(ranking["rankings"][2]["amount"])) == Decimal("48000.00")
print("-> Ranking Order Verification (Lowest = Rank 1): PASSED")

# 8. Test Deterministic Tie Breaking
# Create Supplier Delta and submit matching $45,000 bid (after Supplier Beta)
s_delta_res = client.post("/api/v1/suppliers", json={
    "name": "Supplier Delta",
    "email": f"bids_{uuid.uuid4().hex[:6]}@delta.com",
    "company_name": "Delta Industrial"
})
sup_delta = s_delta_res.json()
b_delta = client.post("/api/v1/bids", json={"rfq_id": rfq_a["id"], "supplier_id": sup_delta["id"], "amount": 45000.00})
assert b_delta.status_code == 201

rank_tie_res = client.get(f"/api/v1/rfqs/{rfq_a['id']}/ranking")
rankings_tie = rank_tie_res.json()["rankings"]
assert len(rankings_tie) == 4
# Rank 1: Beta ($45,000) (submitted earlier)
assert rankings_tie[0]["rank"] == 1
assert rankings_tie[0]["supplier_id"] == sup_beta["id"]
# Rank 2: Delta ($45,000) (submitted second)
assert rankings_tie[1]["rank"] == 2
assert rankings_tie[1]["supplier_id"] == sup_delta["id"]
# Rank 3: Gamma ($47,000)
assert rankings_tie[2]["rank"] == 3
assert rankings_tie[2]["supplier_id"] == sup_gamma["id"]
# Rank 4: Alpha ($48,000)
assert rankings_tie[3]["rank"] == 4
assert rankings_tie[3]["supplier_id"] == sup_alpha["id"]
print("-> Deterministic Tie Breaking Verification: PASSED (Beta=Rank 1, Delta=Rank 2)")

# 9. Test RFQ Isolation
rfq_b_res = client.post("/api/v1/rfqs", json={
    "buyer_id": buyer["id"],
    "title": "Electronic Sensor Batch",
    "description": "Inconel sensors",
    "currency": "EUR",
    "baseline_price": 40000.00,
    "items": [{"name": "Sensor Part", "quantity": 10, "unit": "units"}]
})
rfq_b = rfq_b_res.json()
b_b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_b["id"], "supplier_id": sup_alpha["id"], "amount": 32000.00})
b_b2 = client.post("/api/v1/bids", json={"rfq_id": rfq_b["id"], "supplier_id": sup_beta["id"], "amount": 30000.00})

rank_b_res = client.get(f"/api/v1/rfqs/{rfq_b['id']}/ranking")
rankings_b = rank_b_res.json()["rankings"]
assert len(rankings_b) == 2
assert [Decimal(str(r["amount"])) for r in rankings_b] == [Decimal("30000.00"), Decimal("32000.00")]
assert not any(r["bid_id"] in [b1.json()["id"], b2.json()["id"]] for r in rankings_b)

rank_a_again = client.get(f"/api/v1/rfqs/{rfq_a['id']}/ranking")
assert not any(r["bid_id"] in [b_b1.json()["id"], b_b2.json()["id"]] for r in rank_a_again.json()["rankings"])
print("-> Cross-RFQ Isolation Verification: PASSED")

# 10. Direct PostgreSQL Records Validation
cur.execute("SELECT id, supplier_id, amount, is_valid, submitted_at FROM bids WHERE id = %s", (b2.json()["id"],))
db_bid_b = cur.fetchone()
assert db_bid_b is not None
assert db_bid_b[2] == Decimal("45000.00")
print(f"-> PostgreSQL Direct Record Check (Rank 1 Bid ID {db_bid_b[0]}): Amount={db_bid_b[2]}, Valid={db_bid_b[3]}")

print("\n>>> ALL STEP 7 END-TO-END AND DATABASE CHECKS PASSED SUCCESSFULLY! <<<\n")
