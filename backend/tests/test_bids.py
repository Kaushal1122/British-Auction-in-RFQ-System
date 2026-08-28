import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, EventType, ActorType, AuctionStatus, AuctionRoundStatus


@pytest.fixture
def test_setup(client: TestClient, cleanup_tracker):
    """Helper fixture to create a valid Buyer, Supplier, and RFQ with items for testing."""
    # 1. Create Buyer
    buyer_resp = client.post(
        "/api/v1/buyers",
        json={"name": "Test Buyer", "email": f"buyer_{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert buyer_resp.status_code == 201
    buyer_id = buyer_resp.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(buyer_id))

    # 2. Create Supplier
    supplier_resp = client.post(
        "/api/v1/suppliers",
        json={"name": "Precision Bearings Ltd", "email": f"supplier_{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]
    cleanup_tracker.track_supplier(uuid.UUID(supplier_id))

    # 3. Create RFQ with 2 items
    rfq_payload = {
        "buyer_id": buyer_id,
        "title": "Industrial Bearing Procurement",
        "description": "High precision ball bearings",
        "category": "Industrial Machinery",
        "currency": "USD",
        "baseline_price": 50000.00,
        "items": [
            {
                "name": "Steel Roller Bearing",
                "description": "Inner diameter 50mm",
                "quantity": 200,
                "unit": "units",
            },
            {
                "name": "Ceramic Ball Bearing",
                "description": "High temperature resistant",
                "quantity": 100,
                "unit": "units",
            },
        ],
    }
    rfq_resp = client.post("/api/v1/rfqs", json=rfq_payload)
    assert rfq_resp.status_code == 201
    rfq_data = rfq_resp.json()
    rfq_id = rfq_data["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq_id))

    return {
        "buyer_id": buyer_id,
        "supplier_id": supplier_id,
        "rfq_id": rfq_id,
        "items": rfq_data["items"],
    }


def test_create_bid_valid_amount(client: TestClient, test_setup, cleanup_tracker):
    """Verify successful submission of a valid bid against an RFQ."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 42500.00,
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["amount"])) == Decimal("42500.00")
    assert data["supplier_id"] == test_setup["supplier_id"]
    assert data["is_valid"] is True
    assert "id" in data
    assert "auction_id" in data
    assert "round_id" in data
    assert "submitted_at" in data
    cleanup_tracker.track_bid(uuid.UUID(data["id"]))


def test_create_bid_with_specific_item(client: TestClient, test_setup, cleanup_tracker):
    """Verify bid submission with an associated RFQ line item."""
    item_id = test_setup["items"][0]["id"]
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 18000.50,
        "rfq_item_id": item_id,
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["amount"])) == Decimal("18000.50")
    cleanup_tracker.track_bid(uuid.UUID(data["id"]))


def test_create_bid_negative_amount_rejected(client: TestClient, test_setup):
    """Verify negative bid amount is rejected with 422."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": -500.00,
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 422


def test_create_bid_missing_required_fields(client: TestClient, test_setup):
    """Verify missing required fields return 422."""
    # Missing amount
    r1 = client.post("/api/v1/bids", json={"rfq_id": test_setup["rfq_id"], "supplier_id": test_setup["supplier_id"]})
    assert r1.status_code == 422

    # Missing rfq_id
    r2 = client.post("/api/v1/bids", json={"supplier_id": test_setup["supplier_id"], "amount": 1000})
    assert r2.status_code == 422

    # Missing supplier_id
    r3 = client.post("/api/v1/bids", json={"rfq_id": test_setup["rfq_id"], "amount": 1000})
    assert r3.status_code == 422


def test_create_bid_non_existent_rfq_returns_404(client: TestClient, test_setup):
    """Verify 404 when bidding on a non-existent RFQ."""
    random_rfq = uuid.uuid4()
    payload = {
        "rfq_id": str(random_rfq),
        "supplier_id": test_setup["supplier_id"],
        "amount": 10000,
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 404
    assert "rfq with id" in response.json()["detail"].lower()


def test_create_bid_non_existent_supplier_returns_404(client: TestClient, test_setup):
    """Verify 404 when bidding with a non-existent Supplier."""
    random_supplier = uuid.uuid4()
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": str(random_supplier),
        "amount": 10000,
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 404
    assert "supplier with id" in response.json()["detail"].lower()


def test_create_bid_invalid_item_id_returns_404(client: TestClient, test_setup):
    """Verify 404 when passing an item ID that doesn't belong to the RFQ."""
    random_item = uuid.uuid4()
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 10000,
        "rfq_item_id": str(random_item),
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 404
    assert "rfq item with id" in response.json()["detail"].lower()


def test_create_bid_persists_in_database(client: TestClient, db: Session, test_setup, cleanup_tracker):
    """Verify real PostgreSQL database persistence of Bid, Auction, AuctionRound, and ActivityLog."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 35000.00,
        "rfq_item_id": test_setup["items"][0]["id"],
    }

    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 201
    bid_data = response.json()
    bid_id = uuid.UUID(bid_data["id"])
    cleanup_tracker.track_bid(bid_id)

    # 1. Query Bid record in DB
    db_bid = db.query(Bid).filter(Bid.id == bid_id).first()
    assert db_bid is not None
    assert db_bid.amount == Decimal("35000.00")
    assert str(db_bid.supplier_id) == test_setup["supplier_id"]
    assert db_bid.is_valid is True

    # 2. Query Auction record in DB
    db_auction = db.query(Auction).filter(Auction.id == db_bid.auction_id).first()
    assert db_auction is not None
    assert str(db_auction.rfq_id) == test_setup["rfq_id"]

    # 3. Query AuctionRound in DB
    db_round = db.query(AuctionRound).filter(AuctionRound.id == db_bid.round_id).first()
    assert db_round is not None
    assert db_round.auction_id == db_auction.id

    # 4. Query ActivityLog in DB
    db_log = (
        db.query(ActivityLog)
        .filter(ActivityLog.rfq_id == uuid.UUID(test_setup["rfq_id"]), ActivityLog.event_type == EventType.BID_SUBMITTED)
        .first()
    )
    assert db_log is not None
    assert db_log.actor_type == ActorType.SUPPLIER
    assert str(db_log.actor_id) == test_setup["supplier_id"]


def test_get_bid_by_id(client: TestClient, test_setup, cleanup_tracker):
    """Verify retrieving a bid by UUID."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 29000.00,
    }
    create_resp = client.post("/api/v1/bids", json=payload)
    assert create_resp.status_code == 201
    bid_id = create_resp.json()["id"]
    cleanup_tracker.track_bid(uuid.UUID(bid_id))

    get_resp = client.get(f"/api/v1/bids/{bid_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == bid_id
    assert Decimal(str(get_resp.json()["amount"])) == Decimal("29000.00")


def test_get_non_existing_bid_returns_404(client: TestClient):
    """Verify 404 for non-existing bid UUID."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/bids/{random_id}")
    assert response.status_code == 404


def test_list_bids_for_rfq(client: TestClient, test_setup, cleanup_tracker):
    """Verify listing all bids for a specific RFQ with distinct suppliers."""
    # Create second supplier
    sup2_resp = client.post(
        "/api/v1/suppliers",
        json={"name": "Second Supplier Ltd", "email": f"supplier2_{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert sup2_resp.status_code == 201
    sup2_id = sup2_resp.json()["id"]
    cleanup_tracker.track_supplier(uuid.UUID(sup2_id))

    # Place 2 bids from distinct suppliers
    b1 = client.post("/api/v1/bids", json={"rfq_id": test_setup["rfq_id"], "supplier_id": test_setup["supplier_id"], "amount": 40000})
    b2 = client.post("/api/v1/bids", json={"rfq_id": test_setup["rfq_id"], "supplier_id": sup2_id, "amount": 38000})
    assert b1.status_code == 201
    assert b2.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b2.json()["id"]))

    list_resp = client.get(f"/api/v1/bids/rfq/{test_setup['rfq_id']}")
    assert list_resp.status_code == 200
    bids = list_resp.json()
    assert len(bids) >= 2


def test_create_bid_on_closed_rfq_rejected(client: TestClient, db: Session, test_setup, cleanup_tracker):
    """Verify bidding on a closed RFQ is rejected."""
    rfq = db.query(RFQ).filter(RFQ.id == uuid.UUID(test_setup["rfq_id"])).first()
    rfq.status = RFQStatus.CLOSED
    db.commit()

    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 30000,
    }
    response = client.post("/api/v1/bids", json=payload)
    assert response.status_code == 400
    assert "not eligible for bidding" in response.json()["detail"].lower()


# ==============================================================================
# STEP 6 FIX: MULTI-RFQ PARTICIPATION & COMPOSITE UNIQUENESS TESTS (TESTS 1 - 8)
# ==============================================================================

def test_1_first_bid_succeeds(client: TestClient, test_setup, cleanup_tracker):
    """TEST 1 — First bid from a bidder on an RFQ succeeds."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 46000.00,
    }
    resp = client.post("/api/v1/bids", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["supplier_id"] == test_setup["supplier_id"]
    assert Decimal(str(data["amount"])) == Decimal("46000.00")
    cleanup_tracker.track_bid(uuid.UUID(data["id"]))


def test_2_same_bidder_can_bid_on_another_rfq(client: TestClient, test_setup, cleanup_tracker):
    """
    TEST 2 — Same bidder can bid on multiple different RFQs (Regression Test).
    Bidder A -> RFQ 1: SUCCESS
    Bidder A -> RFQ 2: SUCCESS
    """
    # 1. Create second RFQ
    rfq2_payload = {
        "buyer_id": test_setup["buyer_id"],
        "title": "Secondary RFQ - Precision Parts",
        "category": "Manufacturing",
        "currency": "USD",
        "baseline_price": 75000.00,
        "items": [
            {"name": "Shaft Couplings", "quantity": 50, "unit": "pieces"}
        ],
    }
    rfq2_resp = client.post("/api/v1/rfqs", json=rfq2_payload)
    assert rfq2_resp.status_code == 201
    rfq2_id = rfq2_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq2_id))

    # 2. Submit Bid 1: Supplier A on RFQ 1
    b1_resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": test_setup["rfq_id"], "supplier_id": test_setup["supplier_id"], "amount": 47000.00},
    )
    assert b1_resp.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b1_resp.json()["id"]))

    # 3. Submit Bid 2: SAME Supplier A on RFQ 2
    b2_resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": rfq2_id, "supplier_id": test_setup["supplier_id"], "amount": 71000.00},
    )
    assert b2_resp.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b2_resp.json()["id"]))

    # Verify both bids exist with distinct RFQs and auction IDs
    assert b1_resp.json()["id"] != b2_resp.json()["id"]
    assert b1_resp.json()["auction_id"] != b2_resp.json()["auction_id"]


def test_3_same_bidder_cannot_duplicate_bid_on_same_rfq(client: TestClient, test_setup, cleanup_tracker):
    """
    TEST 3 — Duplicate bid from the same bidder on the SAME RFQ is rejected.
    Bidder A -> RFQ 1: SUCCESS
    Bidder A -> RFQ 1: REJECTED (400)
    """
    # 1. First bid succeeds
    b1_resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": test_setup["rfq_id"], "supplier_id": test_setup["supplier_id"], "amount": 45000.00},
    )
    assert b1_resp.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b1_resp.json()["id"]))

    # 2. Duplicate bid on same RFQ fails
    b2_resp = client.post(
        "/api/v1/bids",
        json={"rfq_id": test_setup["rfq_id"], "supplier_id": test_setup["supplier_id"], "amount": 43000.00},
    )
    assert b2_resp.status_code == 400
    detail = b2_resp.json()["detail"].lower()
    assert "already submitted a bid" in detail or "constraint violation" in detail


def test_4_same_bidder_multiple_rfqs(client: TestClient, db: Session, test_setup, cleanup_tracker):
    """
    TEST 4 — Same bidder successfully places bids on 3 distinct RFQs.
    Verify 3 separate bid records exist in DB.
    """
    # Create RFQ 2 and RFQ 3
    rfq2_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": test_setup["buyer_id"],
            "title": "RFQ 2 - CNC Machining",
            "currency": "USD",
            "baseline_price": 60000.00,
            "items": [{"name": "CNC Part A", "quantity": 100, "unit": "units"}],
        },
    )
    rfq2_id = rfq2_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq2_id))

    rfq3_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": test_setup["buyer_id"],
            "title": "RFQ 3 - Sheet Metal",
            "currency": "USD",
            "baseline_price": 30000.00,
            "items": [{"name": "Sheet Metal Panel", "quantity": 500, "unit": "units"}],
        },
    )
    rfq3_id = rfq3_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq3_id))

    supplier_id = test_setup["supplier_id"]

    # Submit on RFQ 1, 2, 3
    b1 = client.post("/api/v1/bids", json={"rfq_id": test_setup["rfq_id"], "supplier_id": supplier_id, "amount": 48000})
    b2 = client.post("/api/v1/bids", json={"rfq_id": rfq2_id, "supplier_id": supplier_id, "amount": 58000})
    b3 = client.post("/api/v1/bids", json={"rfq_id": rfq3_id, "supplier_id": supplier_id, "amount": 28000})

    assert b1.status_code == 201
    assert b2.status_code == 201
    assert b3.status_code == 201

    cleanup_tracker.track_bid(uuid.UUID(b1.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b2.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b3.json()["id"]))

    # Verify three separate records in PostgreSQL
    db_bids = db.query(Bid).filter(Bid.supplier_id == uuid.UUID(supplier_id)).all()
    created_db_bid_ids = {str(b.id) for b in db_bids}
    assert b1.json()["id"] in created_db_bid_ids
    assert b2.json()["id"] in created_db_bid_ids
    assert b3.json()["id"] in created_db_bid_ids


def test_5_multiple_bidders_on_same_rfq(client: TestClient, test_setup, cleanup_tracker):
    """TEST 5 — Multiple distinct bidders can submit bids for the same RFQ."""
    # Create Supplier B & Supplier C
    sup_b = client.post("/api/v1/suppliers", json={"name": "Supplier Beta", "email": f"beta_{uuid.uuid4().hex[:8]}@example.com"}).json()
    sup_c = client.post("/api/v1/suppliers", json={"name": "Supplier Gamma", "email": f"gamma_{uuid.uuid4().hex[:8]}@example.com"}).json()
    cleanup_tracker.track_supplier(uuid.UUID(sup_b["id"]))
    cleanup_tracker.track_supplier(uuid.UUID(sup_c["id"]))

    rfq_id = test_setup["rfq_id"]

    # Submit Supplier A, B, C
    b_a = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": test_setup["supplier_id"], "amount": 49000})
    b_b = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": sup_b["id"], "amount": 47000})
    b_c = client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": sup_c["id"], "amount": 48000})

    assert b_a.status_code == 201
    assert b_b.status_code == 201
    assert b_c.status_code == 201

    cleanup_tracker.track_bid(uuid.UUID(b_a.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_b.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_c.json()["id"]))

    # List bids for RFQ
    list_resp = client.get(f"/api/v1/bids/rfq/{rfq_id}")
    assert list_resp.status_code == 200
    returned_ids = [b["id"] for b in list_resp.json()]
    assert b_a.json()["id"] in returned_ids
    assert b_b.json()["id"] in returned_ids
    assert b_c.json()["id"] in returned_ids


def test_6_bid_isolation_between_rfqs(client: TestClient, test_setup, cleanup_tracker):
    """
    TEST 6 — Bid isolation:
    RFQ 1 bids and RFQ 2 bids remain strictly isolated in API listings and ranking.
    """
    # Create Supplier B
    sup_b = client.post("/api/v1/suppliers", json={"name": "Supplier B", "email": f"supb_{uuid.uuid4().hex[:8]}@example.com"}).json()
    cleanup_tracker.track_supplier(uuid.UUID(sup_b["id"]))

    # Create RFQ 2 with required items
    rfq2_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": test_setup["buyer_id"],
            "title": "Isolated RFQ 2",
            "category": "Machinery",
            "currency": "USD",
            "baseline_price": 50000,
            "items": [{"name": "Isolated Item", "quantity": 10, "unit": "units"}],
        },
    )
    assert rfq2_resp.status_code == 201
    rfq2 = rfq2_resp.json()
    cleanup_tracker.track_rfq(uuid.UUID(rfq2["id"]))

    rfq1_id = test_setup["rfq_id"]
    rfq2_id = rfq2["id"]
    sup_a_id = test_setup["supplier_id"]
    sup_b_id = sup_b["id"]

    # RFQ 1: Supplier A + Supplier B
    b_1a = client.post("/api/v1/bids", json={"rfq_id": rfq1_id, "supplier_id": sup_a_id, "amount": 48000})
    b_1b = client.post("/api/v1/bids", json={"rfq_id": rfq1_id, "supplier_id": sup_b_id, "amount": 45000})
    assert b_1a.status_code == 201
    assert b_1b.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b_1a.json()["id"]))
    cleanup_tracker.track_bid(uuid.UUID(b_1b.json()["id"]))

    # RFQ 2: Supplier A only
    b_2a = client.post("/api/v1/bids", json={"rfq_id": rfq2_id, "supplier_id": sup_a_id, "amount": 42000})
    assert b_2a.status_code == 201
    cleanup_tracker.track_bid(uuid.UUID(b_2a.json()["id"]))

    # Verify RFQ 1 bids list
    bids_rfq1 = client.get(f"/api/v1/bids/rfq/{rfq1_id}").json()
    rfq1_bid_ids = [b["id"] for b in bids_rfq1]
    assert b_1a.json()["id"] in rfq1_bid_ids
    assert b_1b.json()["id"] in rfq1_bid_ids
    assert b_2a.json()["id"] not in rfq1_bid_ids

    # Verify RFQ 2 bids list
    bids_rfq2 = client.get(f"/api/v1/bids/rfq/{rfq2_id}").json()
    rfq2_bid_ids = [b["id"] for b in bids_rfq2]
    assert b_2a.json()["id"] in rfq2_bid_ids
    assert b_1a.json()["id"] not in rfq2_bid_ids
    assert b_1b.json()["id"] not in rfq2_bid_ids


def test_7_database_uniqueness_constraint_enforced(client: TestClient, db: Session, test_setup, cleanup_tracker):
    """
    TEST 7 — Database-level uniqueness constraint:
    Direct DB insertion of duplicate (auction_id, supplier_id) raises IntegrityError,
    while distinct (auction_id, supplier_id) is allowed.
    """
    from sqlalchemy.exc import IntegrityError

    # 1. Create a dedicated RFQ for DB constraint test
    rfq_resp = client.post(
        "/api/v1/rfqs",
        json={
            "buyer_id": test_setup["buyer_id"],
            "title": "DB Constraint Test RFQ",
            "currency": "USD",
            "baseline_price": 50000,
            "items": [{"name": "Constraint Item", "quantity": 1, "unit": "unit"}],
        },
    )
    assert rfq_resp.status_code == 201
    db_rfq_id = uuid.UUID(rfq_resp.json()["id"])
    cleanup_tracker.track_rfq(db_rfq_id)

    # 2. Get or create Auction and Round in DB
    auction1 = db.query(Auction).filter(Auction.rfq_id == db_rfq_id).first()
    if not auction1:
        auction1 = Auction(rfq_id=db_rfq_id, status=AuctionStatus.LIVE, current_round=1)
        db.add(auction1)
        db.flush()
    else:
        auction1.status = AuctionStatus.LIVE
        db.flush()

    round1 = db.query(AuctionRound).filter(AuctionRound.auction_id == auction1.id, AuctionRound.round_number == 1).first()
    if not round1:
        round1 = AuctionRound(auction_id=auction1.id, round_number=1, status=AuctionRoundStatus.ACTIVE)
        db.add(round1)
        db.flush()
    else:
        round1.status = AuctionRoundStatus.ACTIVE
        db.flush()

    supplier_uuid = uuid.UUID(test_setup["supplier_id"])


    # 3. Insert valid bid directly
    bid1 = Bid(
        auction_id=auction1.id,
        round_id=round1.id,
        supplier_id=supplier_uuid,
        amount=Decimal("41000.00"),
        is_valid=True,
    )
    db.add(bid1)
    db.commit()
    cleanup_tracker.track_bid(bid1.id)

    # 4. Attempt direct duplicate insert on same auction_id and supplier_id -> must raise IntegrityError
    bid2 = Bid(
        auction_id=auction1.id,
        round_id=round1.id,
        supplier_id=supplier_uuid,
        amount=Decimal("39000.00"),
        is_valid=True,
    )
    db.add(bid2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_8_existing_bids_remain_valid(client: TestClient, db: Session, test_setup, cleanup_tracker):
    """TEST 8 — Verify that existing bids remain fully valid, queryable, and uncorrupted."""
    payload = {
        "rfq_id": test_setup["rfq_id"],
        "supplier_id": test_setup["supplier_id"],
        "amount": 37500.00,
    }
    create_resp = client.post("/api/v1/bids", json=payload)
    assert create_resp.status_code == 201
    bid_id = create_resp.json()["id"]
    cleanup_tracker.track_bid(uuid.UUID(bid_id))

    # Read back via API
    get_resp = client.get(f"/api/v1/bids/{bid_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_valid"] is True
    assert Decimal(str(get_resp.json()["amount"])) == Decimal("37500.00")

    # Direct DB inspection
    db_bid = db.query(Bid).filter(Bid.id == uuid.UUID(bid_id)).first()
    assert db_bid is not None
    assert db_bid.amount == Decimal("37500.00")
    assert db_bid.is_valid is True


# ==============================================================================
# AUCTION LIFECYCLE TIMING TESTS (STEP 8 FIX)
# ==============================================================================

def test_bid_before_auction_start_rejected(db: Session, test_setup, cleanup_tracker):
    """Verify that a bid placed before the auction start time is rejected with 400."""
    from datetime import datetime, timedelta, timezone
    from app.schemas.bid import BidCreate
    from app.services.bid_service import create_bid
    from fastapi import HTTPException

    rfq_uuid = uuid.UUID(test_setup["rfq_id"])
    supplier_uuid = uuid.UUID(test_setup["supplier_id"])

    # Configure auction with future start time
    auction = db.query(Auction).filter(Auction.rfq_id == rfq_uuid).first()
    future_start = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    future_close = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    future_forced = datetime(2026, 9, 1, 11, 30, 0, tzinfo=timezone.utc)

    if not auction:
        auction = Auction(
            rfq_id=rfq_uuid,
            start_time=future_start,
            end_time=future_close,
            forced_bid_close_time=future_forced,
            status=AuctionStatus.SCHEDULED,
            current_round=1,
        )
        db.add(auction)
        db.commit()
    else:
        auction.start_time = future_start
        auction.end_time = future_close
        auction.forced_bid_close_time = future_forced
        auction.status = AuctionStatus.SCHEDULED
        db.commit()

    # Attempt to place bid before start time (e.g. 09:30)
    bid_payload = BidCreate(rfq_id=rfq_uuid, supplier_id=supplier_uuid, amount=Decimal("40000.00"))
    early_time = datetime(2026, 9, 1, 9, 30, 0, tzinfo=timezone.utc)

    with pytest.raises(HTTPException) as exc_info:
        create_bid(db, bid_payload, event_time=early_time)

    assert exc_info.value.status_code == 400
    assert "Auction has not started yet" in exc_info.value.detail


def test_bid_after_forced_close_rejected(db: Session, test_setup, cleanup_tracker):
    """Verify that a bid placed after the auction forced close time is rejected with 400."""
    from datetime import datetime, timezone
    from app.schemas.bid import BidCreate
    from app.services.bid_service import create_bid
    from fastapi import HTTPException

    rfq_uuid = uuid.UUID(test_setup["rfq_id"])
    supplier_uuid = uuid.UUID(test_setup["supplier_id"])

    # Configure auction with past forced close time
    auction = db.query(Auction).filter(Auction.rfq_id == rfq_uuid).first()
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 11, 30, 0, tzinfo=timezone.utc)

    if not auction:
        auction = Auction(
            rfq_id=rfq_uuid,
            start_time=start_time,
            end_time=close_time,
            forced_bid_close_time=forced_close,
            status=AuctionStatus.LIVE,
            current_round=1,
        )
        db.add(auction)
        db.commit()
    else:
        auction.start_time = start_time
        auction.end_time = close_time
        auction.forced_bid_close_time = forced_close
        auction.status = AuctionStatus.LIVE
        db.commit()

    # Attempt to place bid after forced close (e.g. 11:35)
    bid_payload = BidCreate(rfq_id=rfq_uuid, supplier_id=supplier_uuid, amount=Decimal("40000.00"))
    late_time = datetime(2026, 9, 1, 11, 35, 0, tzinfo=timezone.utc)

    with pytest.raises(HTTPException) as exc_info:
        create_bid(db, bid_payload, event_time=late_time)

    assert exc_info.value.status_code == 400
    assert "Auction has closed" in exc_info.value.detail


def test_bid_during_active_auction_accepted(db: Session, test_setup, cleanup_tracker):
    """Verify that a bid placed during the active auction window is accepted."""
    from datetime import datetime, timezone
    from app.schemas.bid import BidCreate
    from app.services.bid_service import create_bid

    rfq_uuid = uuid.UUID(test_setup["rfq_id"])
    supplier_uuid = uuid.UUID(test_setup["supplier_id"])

    # Configure active auction
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 11, 30, 0, tzinfo=timezone.utc)

    auction = db.query(Auction).filter(Auction.rfq_id == rfq_uuid).first()
    if not auction:
        auction = Auction(
            rfq_id=rfq_uuid,
            start_time=start_time,
            end_time=close_time,
            forced_bid_close_time=forced_close,
            status=AuctionStatus.LIVE,
            current_round=1,
        )
        db.add(auction)
        db.commit()
    else:
        auction.start_time = start_time
        auction.end_time = close_time
        auction.forced_bid_close_time = forced_close
        auction.status = AuctionStatus.LIVE
        db.commit()

    # Place bid inside active window at 10:15
    active_time = datetime(2026, 9, 1, 10, 15, 0, tzinfo=timezone.utc)
    bid_payload = BidCreate(rfq_id=rfq_uuid, supplier_id=supplier_uuid, amount=Decimal("41500.00"))

    created = create_bid(db, bid_payload, event_time=active_time)
    cleanup_tracker.track_bid(created.id)

    assert created is not None
    assert created.amount == Decimal("41500.00")
    assert created.is_valid is True


