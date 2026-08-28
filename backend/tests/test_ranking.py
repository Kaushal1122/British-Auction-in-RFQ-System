import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.bid import Bid


@pytest.fixture
def ranking_setup(client: TestClient, cleanup_tracker):
    """Helper fixture to create a Buyer, 3 distinct Suppliers, and 2 separate RFQs."""
    # 1. Create Buyer
    buyer_resp = client.post(
        "/api/v1/buyers",
        json={"name": "Procurement Director", "email": f"buyer_{uuid.uuid4().hex[:8]}@enterprise.com", "company_name": "MegaCorp"},
    )
    assert buyer_resp.status_code == 201
    buyer_id = buyer_resp.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(buyer_id))

    # 2. Create 3 Suppliers
    suppliers = []
    supplier_names = [
        ("Supplier Alpha", "Alpha Tech Ltd"),
        ("Supplier Beta", "Beta Industrial Supply"),
        ("Supplier Gamma", "Gamma Dynamics Corp"),
    ]
    for name, company in supplier_names:
        s_resp = client.post(
            "/api/v1/suppliers",
            json={"name": name, "email": f"sup_{uuid.uuid4().hex[:8]}@example.com", "company_name": company},
        )
        assert s_resp.status_code == 201
        s_data = s_resp.json()
        cleanup_tracker.track_supplier(uuid.UUID(s_data["id"]))
        suppliers.append(s_data)

    # 3. Create RFQ A (USD)
    rfq_a_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": buyer_id,
            "title": "Industrial Component Procurement",
            "description": "High grade aerospace bearings",
            "category": "Aerospace",
            "currency": "USD",
            "baseline_price": 50000.00,
            "items": [
                {"name": "Roller Bearing A", "quantity": 100, "unit": "units"}
            ],
        },
    )
    assert rfq_a_resp.status_code == 201
    rfq_a = rfq_a_resp.json()
    cleanup_tracker.track_rfq(uuid.UUID(rfq_a["id"]))

    # 4. Create RFQ B (EUR) for isolation testing
    rfq_b_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": buyer_id,
            "title": "Electronic Sensor Batch",
            "description": "Temperature and pressure sensors",
            "category": "Electronics",
            "currency": "EUR",
            "baseline_price": 30000.00,
            "items": [
                {"name": "Sensor Unit", "quantity": 50, "unit": "units"}
            ],
        },
    )
    assert rfq_b_resp.status_code == 201
    rfq_b = rfq_b_resp.json()
    cleanup_tracker.track_rfq(uuid.UUID(rfq_b["id"]))

    return {
        "buyer_id": buyer_id,
        "suppliers": suppliers,
        "rfq_a": rfq_a,
        "rfq_b": rfq_b,
    }


def test_1_ranking_endpoint_exists(client: TestClient, ranking_setup):
    """Test 1: Verify the ranking endpoint exists and returns 200 OK for an existing RFQ."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    response = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert response.status_code == 200


def test_2_ranking_returns_404_when_rfq_not_found(client: TestClient):
    """Test 2: Verify ranking returns 404 Not Found with clean detail when RFQ does not exist."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/rfqs/{random_id}/ranking")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_3_ranking_returns_empty_list_when_no_bids(client: TestClient, ranking_setup):
    """Test 3: Verify ranking returns empty rankings list and total_bids=0 when RFQ has no bids."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    response = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert response.status_code == 200
    data = response.json()
    assert data["rfq_id"] == rfq_id
    assert data["rfq_title"] == "Industrial Component Procurement"
    assert data["currency"] == "USD"
    assert data["total_bids"] == 0
    assert data["rankings"] == []


def test_4_single_bid_receives_rank_1(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 4: Verify that a single placed bid receives rank 1."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    supplier_id = ranking_setup["suppliers"][0]["id"]

    bid_resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": rfq_id, "supplier_id": supplier_id, "amount": 48000.00},
    )
    assert bid_resp.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(bid_resp.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert rank_resp.status_code == 200
    data = rank_resp.json()
    assert data["total_bids"] == 1
    assert len(data["rankings"]) == 1
    assert data["rankings"][0]["rank"] == 1
    assert data["rankings"][0]["bid_id"] == bid_resp.json()["id"]
    assert Decimal(str(data["rankings"][0]["amount"])) == Decimal("48000.00")
    assert data["rankings"][0]["supplier_id"] == supplier_id


def test_5_multiple_bids_sorted_lowest_to_highest(client: TestClient, ranking_setup, cleanup_tracker):
    """
    Test 5: Verify multiple bids are sorted from lowest amount (Rank 1) to highest amount.
    Example: 50000, 45000, 48000 -> 45000 (Rank 1), 48000 (Rank 2), 50000 (Rank 3).
    """
    rfq_id = ranking_setup["rfq_a"]["id"]
    suppliers = ranking_setup["suppliers"]

    # Submit bids in non-sorted order: 50000, 45000, 48000
    b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[0]["id"], "amount": 50000.00})
    b2 = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[1]["id"], "amount": 45000.00})
    b3 = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[2]["id"], "amount": 48000.00})
    assert b1.status_code == 201
    assert b2.status_code == 201
    assert b3.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b2.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b3.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert rank_resp.status_code == 200
    rankings = rank_resp.json()["rankings"]
    assert len(rankings) == 3

    # Rank 1 -> 45000 (Supplier 1 / Beta)
    assert rankings[0]["rank"] == 1
    assert Decimal(str(rankings[0]["amount"])) == Decimal("45000.00")
    assert rankings[0]["bid_id"] == b2.json()["id"]
    assert rankings[0]["supplier_id"] == suppliers[1]["id"]

    # Rank 2 -> 48000 (Supplier 2 / Gamma)
    assert rankings[1]["rank"] == 2
    assert Decimal(str(rankings[1]["amount"])) == Decimal("48000.00")
    assert rankings[1]["bid_id"] == b3.json()["id"]
    assert rankings[1]["supplier_id"] == suppliers[2]["id"]

    # Rank 3 -> 50000 (Supplier 0 / Alpha)
    assert rankings[2]["rank"] == 3
    assert Decimal(str(rankings[2]["amount"])) == Decimal("50000.00")
    assert rankings[2]["bid_id"] == b1.json()["id"]
    assert rankings[2]["supplier_id"] == suppliers[0]["id"]


def test_6_equal_bid_amounts_deterministic_tie_breaker(client: TestClient, ranking_setup, cleanup_tracker):
    """
    Test 6: Verify deterministic tie-breaking for equal amounts.
    Supplier A -> 45000 (submitted first)
    Supplier B -> 45000 (submitted second)
    Supplier C -> 47000 (submitted third)
    Order: A (Rank 1), B (Rank 2), C (Rank 3).
    """
    rfq_id = ranking_setup["rfq_a"]["id"]
    suppliers = ranking_setup["suppliers"]

    # Submit Supplier 0 (45000) first
    b_first = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[0]["id"], "amount": 45000.00})
    assert b_first.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b_first.json()["id"]))

    # Submit Supplier 1 (45000) second (same amount)
    b_second = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[1]["id"], "amount": 45000.00})
    assert b_second.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b_second.json()["id"]))

    # Submit Supplier 2 (47000) third
    b_third = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[2]["id"], "amount": 47000.00})
    assert b_third.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b_third.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert rank_resp.status_code == 200
    rankings = rank_resp.json()["rankings"]
    assert len(rankings) == 3

    assert rankings[0]["rank"] == 1
    assert rankings[0]["bid_id"] == b_first.json()["id"]
    assert Decimal(str(rankings[0]["amount"])) == Decimal("45000.00")

    assert rankings[1]["rank"] == 2
    assert rankings[1]["bid_id"] == b_second.json()["id"]
    assert Decimal(str(rankings[1]["amount"])) == Decimal("45000.00")

    assert rankings[2]["rank"] == 3
    assert rankings[2]["bid_id"] == b_third.json()["id"]
    assert Decimal(str(rankings[2]["amount"])) == Decimal("47000.00")


def test_7_ranking_uses_only_bids_belonging_to_requested_rfq(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 7: Verify ranking returns only bids belonging to the specified RFQ."""
    rfq_a_id = ranking_setup["rfq_a"]["id"]
    supplier_id = ranking_setup["suppliers"][0]["id"]

    b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_a_id, "supplier_id": supplier_id, "amount": 42000.00})
    assert b1.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b1.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_a_id}/ranking")
    data = rank_resp.json()
    assert data["rfq_id"] == rfq_a_id
    assert all(r["bid_id"] == b1.json()["id"] for r in data["rankings"])


def test_8_cross_rfq_isolation(client: TestClient, ranking_setup, cleanup_tracker):
    """
    Test 8: Verify bids from RFQ B never appear in RFQ A ranking, and vice versa.
    RFQ A: 45000, 48000
    RFQ B: 25000, 28000
    """
    rfq_a_id = ranking_setup["rfq_a"]["id"]
    rfq_b_id = ranking_setup["rfq_b"]["id"]
    suppliers = ranking_setup["suppliers"]

    # RFQ A bids
    b_a1 = client.post("/api/v1/bids", json={"rfq_id": rfq_a_id, "supplier_id": suppliers[0]["id"], "amount": 45000.00})
    b_a2 = client.post("/api/v1/bids", json={"rfq_id": rfq_a_id, "supplier_id": suppliers[1]["id"], "amount": 48000.00})
    cleanup_tracker.track_bid(uuid.UUID(b_a1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_a2.json()["id"]))

    # RFQ B bids
    b_b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_b_id, "supplier_id": suppliers[1]["id"], "amount": 25000.00})
    b_b2 = client.post("/api/v1/bids", json={"rfq_id": rfq_b_id, "supplier_id": suppliers[2]["id"], "amount": 28000.00})
    cleanup_tracker.track_bid(uuid.UUID(b_b1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_b2.json()["id"]))

    # Query RFQ A
    resp_a = client.get(f"/api/v1/rfqs/{rfq_a_id}/ranking")
    rankings_a = resp_a.json()["rankings"]
    assert len(rankings_a) == 2
    assert [Decimal(str(r["amount"])) for r in rankings_a] == [Decimal("45000.00"), Decimal("48000.00")]
    assert all(r["bid_id"] in [b_a1.json()["id"], b_a2.json()["id"]] for r in rankings_a)
    assert not any(r["bid_id"] in [b_b1.json()["id"], b_b2.json()["id"]] for r in rankings_a)

    # Query RFQ B
    resp_b = client.get(f"/api/v1/rfqs/{rfq_b_id}/ranking")
    rankings_b = resp_b.json()["rankings"]
    assert len(rankings_b) == 2
    assert [Decimal(str(r["amount"])) for r in rankings_b] == [Decimal("25000.00"), Decimal("28000.00")]
    assert all(r["bid_id"] in [b_b1.json()["id"], b_b2.json()["id"]] for r in rankings_b)
    assert not any(r["bid_id"] in [b_a1.json()["id"], b_a2.json()["id"]] for r in rankings_b)


def test_9_sequential_rank_numbers(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 9: Verify rankings have strictly sequential position ranks 1, 2, 3... without gaps."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    suppliers = ranking_setup["suppliers"]

    for i, sup in enumerate(suppliers):
        b = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": sup["id"], "amount": 40000 + (i * 2000)})
        assert b.status_code == 201
        cleanup_tracker.track_bid(uuid.UUID(b.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    rankings = rank_resp.json()["rankings"]
    assert [r["rank"] for r in rankings] == [1, 2, 3]


def test_10_correct_bid_ids_returned(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 10: Verify the exact persisted bid IDs are returned in ranking items."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    suppliers = ranking_setup["suppliers"]

    b1 = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[0]["id"], "amount": 43000})
    b2 = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[1]["id"], "amount": 41000})
    cleanup_tracker.track_bid(uuid.UUID(b1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b2.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    rankings = rank_resp.json()["rankings"]
    assert rankings[0]["bid_id"] == b2.json()["id"]
    assert rankings[1]["bid_id"] == b1.json()["id"]


def test_11_correct_supplier_ids_and_details_returned(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 11: Verify correct supplier IDs and supplier profiles (name, company) are populated."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    supplier = ranking_setup["suppliers"][0]

    b = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": supplier["id"], "amount": 46000})
    cleanup_tracker.track_bid(uuid.UUID(b.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    item = rank_resp.json()["rankings"][0]
    assert item["supplier_id"] == supplier["id"]
    assert item["supplier_name"] == supplier["name"]
    assert item["supplier_company"] == supplier["company_name"]
    assert item["supplier"]["email"] == supplier["email"]


def test_12_correct_bid_amounts_returned(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 12: Verify precise Decimal amounts are preserved in ranking."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    supplier_id = ranking_setup["suppliers"][0]["id"]

    b = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": supplier_id, "amount": 39999.95})
    cleanup_tracker.track_bid(uuid.UUID(b.json()["id"]))

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    item = rank_resp.json()["rankings"][0]
    assert Decimal(str(item["amount"])) == Decimal("39999.95")


def test_13_currency_returned_correctly(client: TestClient, ranking_setup):
    """Test 13: Verify RFQ currency code matches contract (USD for RFQ A, EUR for RFQ B)."""
    resp_a = client.get(f"/api/v1/rfqs/{ranking_setup['rfq_a']['id']}/ranking")
    assert resp_a.json()["currency"] == "USD"

    resp_b = client.get(f"/api/v1/rfqs/{ranking_setup['rfq_b']['id']}/ranking")
    assert resp_b.json()["currency"] == "EUR"


def test_14_invalid_or_withdrawn_bids_excluded(client: TestClient, db: Session, ranking_setup, cleanup_tracker):
    """Test 14: Verify invalid bids (is_valid == False) are excluded from ranking."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    suppliers = ranking_setup["suppliers"]

    # Place 2 bids
    b_valid = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[0]["id"], "amount": 47000})
    b_invalid = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": suppliers[1]["id"], "amount": 30000})
    cleanup_tracker.track_bid(uuid.UUID(b_valid.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_invalid.json()["id"]))

    # Manually mark b_invalid as is_valid = False in DB
    db_bid = db.query(Bid).filter(Bid.id == uuid.UUID(b_invalid.json()["id"])).first()
    db_bid.is_valid = False
    db.commit()

    rank_resp = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    data = rank_resp.json()
    assert data["total_bids"] == 1
    assert len(data["rankings"]) == 1
    assert data["rankings"][0]["bid_id"] == b_valid.json()["id"]
    assert Decimal(str(data["rankings"][0]["amount"])) == Decimal("47000.00")


def test_15_existing_bid_submission_still_works(client: TestClient, ranking_setup, cleanup_tracker):
    """Test 15: Regression check — Bid submission functionality remains intact."""
    payload = {
        "rfq_id": ranking_setup["rfq_a"]["id"],
        "supplier_id": ranking_setup["suppliers"][0]["id"],
        "amount": 44500.00,
    }
    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(response.json()["id"]))


def test_16_existing_rfq_retrieval_still_works(client: TestClient, ranking_setup):
    """Test 16: Regression check — RFQ detail and listing APIs remain intact."""
    rfq_id = ranking_setup["rfq_a"]["id"]
    detail_resp = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == rfq_id
    assert len(detail_resp.json()["items"]) == 1

    list_resp = client.get("/api/v1/rfqs")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2
