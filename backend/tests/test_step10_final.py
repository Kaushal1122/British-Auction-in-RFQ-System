import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ExtensionTrigger, EventType
from app.services.bid_service import create_bid, get_rfq_activity_logs, get_auction_detail, list_auctions
from app.schemas.bid import BidCreate


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_buyer(db):
    unique_id = uuid4().hex[:8]
    buyer = Buyer(
        name=f"Step10 Buyer {unique_id}",
        email=f"step10_buyer_{unique_id}@example.com",
        company_name="Step 10 Logistics Global",
    )
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return buyer


@pytest.fixture
def test_suppliers(db):
    suppliers = []
    for i in range(1, 4):
        unique_id = uuid4().hex[:8]
        sup = Supplier(
            name=f"Step10 Supplier {i} {unique_id}",
            email=f"step10_supplier{i}_{unique_id}@example.com",
            company_name=f"Carrier Express Corp {i}",
        )
        db.add(sup)
        suppliers.append(sup)
    db.commit()
    for s in suppliers:
        db.refresh(s)
    return suppliers


# =========================================================================
# 1. Quote Submission Fields Persistence & Retrieval Tests
# =========================================================================

def test_quote_fields_persistence_and_retrieval(client, db, test_buyer, test_suppliers):
    """
    Verifies that all 6 quote breakdown fields:
    - Carrier Name
    - Freight Charges
    - Origin Charges
    - Destination Charges
    - Transit Time
    - Validity of Quote
    are accepted by API, persisted in PostgreSQL, and returned in Bid and Auction Detail responses.
    """
    now = datetime.now(timezone.utc)
    rfq_payload = {
        "buyer_id": str(test_buyer.id),
        "title": "Step 10 Freight RFQ with Full Quote Breakdown",
        "baseline_price": 50000.00,
        "currency": "USD",
        "bid_start_time": (now - timedelta(hours=1)).isoformat(),
        "bid_close_time": (now + timedelta(hours=2)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=4)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "BID_RECEIVED",
        "items": [
            {"name": "Heavy Machinery Part", "quantity": 10, "unit": "units"}
        ],
    }
    rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
    assert rfq_res.status_code == status.HTTP_201_CREATED
    rfq_data = rfq_res.json()
    rfq_id = rfq_data["id"]

    supplier = test_suppliers[0]

    bid_payload = {
        "rfq_id": rfq_id,
        "supplier_id": str(supplier.id),
        "amount": 42500.00,
        "carrier_name": "Maersk Line Global",
        "freight_charges": 1200.00,
        "origin_charges": 350.00,
        "destination_charges": 450.00,
        "transit_time": "5 business days",
        "validity_of_quote": "30 days",
    }

    bid_res = client.post("/api/v1/bids", json=bid_payload)
    assert bid_res.status_code == status.HTTP_201_CREATED
    bid_data = bid_res.json()

    # Verify API Response
    assert bid_data["carrier_name"] == "Maersk Line Global"
    assert Decimal(str(bid_data["freight_charges"])) == Decimal("1200.00")
    assert Decimal(str(bid_data["origin_charges"])) == Decimal("350.00")
    assert Decimal(str(bid_data["destination_charges"])) == Decimal("450.00")
    assert bid_data["transit_time"] == "5 business days"
    assert bid_data["validity_of_quote"] == "30 days"

    # Verify direct PostgreSQL query
    db_bid = db.query(Bid).filter(Bid.id == bid_data["id"]).first()
    assert db_bid is not None
    assert db_bid.carrier_name == "Maersk Line Global"
    assert db_bid.freight_charges == Decimal("1200.00")
    assert db_bid.origin_charges == Decimal("350.00")
    assert db_bid.destination_charges == Decimal("450.00")
    assert db_bid.transit_time == "5 business days"
    assert db_bid.validity_of_quote == "30 days"

    # Verify ranking endpoint returns quote fields
    rank_res = client.get(f"/api/v1/rfqs/{rfq_id}/ranking")
    assert rank_res.status_code == status.HTTP_200_OK
    rank_data = rank_res.json()
    assert len(rank_data["rankings"]) == 1
    assert rank_data["rankings"][0]["carrier_name"] == "Maersk Line Global"
    assert Decimal(str(rank_data["rankings"][0]["freight_charges"])) == Decimal("1200.00")


# =========================================================================
# 2. Activity Tracking for all 3 Extension Triggers
# =========================================================================

def test_activity_logging_bid_received_trigger(client, db, test_buyer, test_suppliers):
    """
    Test Trigger A: BID_RECEIVED inside trigger window creates:
    - BID_SUBMITTED event
    - AUCTION_EXTENDED event with reason 'Bid received inside X-minute trigger window'
    """
    now = datetime.now(timezone.utc)
    initial_close = now + timedelta(minutes=8)  # inside 10m window
    forced_close = now + timedelta(minutes=30)

    rfq_payload = {
        "buyer_id": str(test_buyer.id),
        "title": "Trigger A: BID_RECEIVED Test",
        "baseline_price": 10000.00,
        "bid_start_time": (now - timedelta(minutes=30)).isoformat(),
        "bid_close_time": initial_close.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "BID_RECEIVED",
        "items": [{"name": "Item A", "quantity": 1, "unit": "pc"}],
    }
    rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
    rfq_id = rfq_res.json()["id"]

    # Submit bid inside trigger window
    bid_in = BidCreate(
        rfq_id=rfq_id,
        supplier_id=test_suppliers[0].id,
        amount=Decimal("8000.00"),
    )
    bid_res = create_bid(db, bid_in, event_time=now)
    assert bid_res.auction_extended is True

    # Check Activity Logs via API
    act_res = client.get(f"/api/v1/rfqs/{rfq_id}/activity")
    assert act_res.status_code == status.HTTP_200_OK
    act_logs = act_res.json()

    event_types = [log["event_type"] for log in act_logs]
    assert "BID_SUBMITTED" in event_types
    assert "AUCTION_EXTENDED" in event_types

    ext_log = next(log for log in act_logs if log["event_type"] == "AUCTION_EXTENDED")
    assert "Bid received inside 10-minute trigger window" in ext_log["message"]
    assert ext_log["metadata_json"]["trigger_mode"] == "BID_RECEIVED"


def test_activity_logging_any_rank_change_trigger(client, db, test_buyer, test_suppliers):
    """
    Test Trigger B: ANY_RANK_CHANGE inside trigger window:
    - Initial bid before trigger window sets initial ranking.
    - Bid 2 inside window causes rank change -> AUCTION_EXTENDED with rank change reason.
    """
    now = datetime.now(timezone.utc)
    initial_close = now + timedelta(minutes=6)
    forced_close = now + timedelta(minutes=40)

    rfq_payload = {
        "buyer_id": str(test_buyer.id),
        "title": "Trigger B: ANY_RANK_CHANGE Test",
        "baseline_price": 20000.00,
        "bid_start_time": (now - timedelta(hours=1)).isoformat(),
        "bid_close_time": initial_close.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "ANY_RANK_CHANGE",
        "items": [{"name": "Item B", "quantity": 1, "unit": "pc"}],
    }
    rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
    rfq_id = rfq_res.json()["id"]

    # 1. Supplier 1 places bid at 15000 (outside window)
    create_bid(db, BidCreate(rfq_id=rfq_id, supplier_id=test_suppliers[0].id, amount=Decimal("15000.00")), event_time=now - timedelta(minutes=20))

    # 2. Supplier 2 places bid at 12000 (inside window) -> triggers rank change
    bid2 = create_bid(db, BidCreate(rfq_id=rfq_id, supplier_id=test_suppliers[1].id, amount=Decimal("12000.00")), event_time=now)
    assert bid2.auction_extended is True

    # Check Activity Logs
    act_logs = get_rfq_activity_logs(db, rfq_id)
    ext_log = next(l for l in act_logs if l.event_type == EventType.AUCTION_EXTENDED)
    assert "Supplier rank change detected inside 10-minute trigger window" in ext_log.message


def test_activity_logging_l1_rank_change_trigger(client, db, test_buyer, test_suppliers):
    """
    Test Trigger C: L1_RANK_CHANGE inside trigger window:
    - Supplier 1 bids 10000 (L1).
    - Supplier 2 bids 12000 (inside window, becomes L2) -> does NOT change L1 -> NO extension.
    - Supplier 3 bids 8000 (inside window, becomes new L1) -> changes L1 -> EXTENSION occurs.
    """
    now = datetime.now(timezone.utc)
    initial_close = now + timedelta(minutes=6)
    forced_close = now + timedelta(minutes=40)

    rfq_payload = {
        "buyer_id": str(test_buyer.id),
        "title": "Trigger C: L1_RANK_CHANGE Test",
        "baseline_price": 20000.00,
        "bid_start_time": (now - timedelta(hours=1)).isoformat(),
        "bid_close_time": initial_close.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "L1_RANK_CHANGE",
        "items": [{"name": "Item C", "quantity": 1, "unit": "pc"}],
    }
    rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
    rfq_id = rfq_res.json()["id"]

    # 1. Supplier 1 bids 10000 (L1) outside trigger window
    create_bid(db, BidCreate(rfq_id=rfq_id, supplier_id=test_suppliers[0].id, amount=Decimal("10000.00")), event_time=now - timedelta(minutes=20))

    # 2. Supplier 2 bids 12000 (L2) inside window -> L1 remains Supplier 1 -> NO EXTENSION
    bid2 = create_bid(db, BidCreate(rfq_id=rfq_id, supplier_id=test_suppliers[1].id, amount=Decimal("12000.00")), event_time=now)
    assert bid2.auction_extended is False

    # 3. Supplier 3 bids 8000 (becomes new L1) inside window -> L1 changes -> EXTENSION
    bid3 = create_bid(db, BidCreate(rfq_id=rfq_id, supplier_id=test_suppliers[2].id, amount=Decimal("8000.00")), event_time=now)
    assert bid3.auction_extended is True

    # Check Activity Logs
    act_logs = get_rfq_activity_logs(db, rfq_id)
    ext_logs = [l for l in act_logs if l.event_type == EventType.AUCTION_EXTENDED]
    assert len(ext_logs) == 1  # Only 1 extension event
    assert "Lowest bidder (L1) changed" in ext_logs[0].message


# =========================================================================
# 3. Auction Listing & Details Endpoints Tests
# =========================================================================

def test_auction_listing_and_details_endpoints(client, db, test_buyer, test_suppliers):
    """
    Verifies:
    - GET /api/v1/auctions returns list with lowest bid and display status.
    - GET /api/v1/auctions/{id} returns full workspace with configuration, ranked bids, and activity log.
    """
    now = datetime.now(timezone.utc)
    rfq_payload = {
        "buyer_id": str(test_buyer.id),
        "title": "Step 10 Auction Listing Test",
        "baseline_price": 30000.00,
        "bid_start_time": (now - timedelta(hours=1)).isoformat(),
        "bid_close_time": (now + timedelta(hours=2)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=5)).isoformat(),
        "items": [{"name": "Item Listing", "quantity": 5, "unit": "units"}],
    }
    rfq_res = client.post("/api/v1/rfqs", json=rfq_payload)
    rfq_id = rfq_res.json()["id"]

    # Place 2 bids
    client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": str(test_suppliers[0].id), "amount": 25000.00})
    client.post("/api/v1/bids", json={"rfq_id": rfq_id, "supplier_id": str(test_suppliers[1].id), "amount": 22000.00})

    # Test Listing Endpoint
    list_res = client.get("/api/v1/auctions")
    assert list_res.status_code == status.HTTP_200_OK
    auctions = list_res.json()
    assert len(auctions) >= 1
    target_auc = next(a for a in auctions if a["rfq_id"] == rfq_id)
    assert Decimal(str(target_auc["lowest_bid"])) == Decimal("22000.00")
    assert target_auc["lowest_bidder_name"] == test_suppliers[1].name
    assert target_auc["display_status"] in ["Active", "Live"]

    # Test Details Endpoint by Auction ID or RFQ ID
    detail_res = client.get(f"/api/v1/auctions/{target_auc['id']}")
    assert detail_res.status_code == status.HTTP_200_OK
    detail_data = detail_res.json()
    assert detail_data["rfq_title"] == "Step 10 Auction Listing Test"
    assert len(detail_data["bids"]) == 2
    assert detail_data["bids"][0]["rank"] == 1
    assert Decimal(str(detail_data["bids"][0]["amount"])) == Decimal("22000.00")
    assert detail_data["bids"][1]["rank"] == 2
    assert len(detail_data["activity_logs"]) >= 2


# =========================================================================
# 4. Multi-RFQ Data Isolation Test
# =========================================================================

def test_multi_rfq_data_isolation(client, db, test_buyer, test_suppliers):
    """
    Verifies that bids and activity logs for RFQ A do NOT bleed into RFQ B.
    """
    now = datetime.now(timezone.utc)
    # RFQ A
    rfq_a_res = client.post("/api/v1/rfqs", json={
        "buyer_id": str(test_buyer.id),
        "title": "RFQ Isolation A",
        "baseline_price": 10000.00,
        "items": [{"name": "Item A", "quantity": 1, "unit": "pc"}],
    })
    rfq_a_id = rfq_a_res.json()["id"]

    # RFQ B
    rfq_b_res = client.post("/api/v1/rfqs", json={
        "buyer_id": str(test_buyer.id),
        "title": "RFQ Isolation B",
        "baseline_price": 20000.00,
        "items": [{"name": "Item B", "quantity": 1, "unit": "pc"}],
    })
    rfq_b_id = rfq_b_res.json()["id"]

    # Same supplier bids on both RFQs
    client.post("/api/v1/bids", json={"rfq_id": rfq_a_id, "supplier_id": str(test_suppliers[0].id), "amount": 9000.00})
    client.post("/api/v1/bids", json={"rfq_id": rfq_b_id, "supplier_id": str(test_suppliers[0].id), "amount": 18000.00})

    # Verify RFQ A rankings only contain Bid A
    rank_a = client.get(f"/api/v1/rfqs/{rfq_a_id}/ranking").json()
    assert len(rank_a["rankings"]) == 1
    assert Decimal(str(rank_a["rankings"][0]["amount"])) == Decimal("9000.00")

    # Verify RFQ B rankings only contain Bid B
    rank_b = client.get(f"/api/v1/rfqs/{rfq_b_id}/ranking").json()
    assert len(rank_b["rankings"]) == 1
    assert Decimal(str(rank_b["rankings"][0]["amount"])) == Decimal("18000.00")

    # Verify RFQ A activity only contains events for RFQ A
    act_a = client.get(f"/api/v1/rfqs/{rfq_a_id}/activity").json()
    for log in act_a:
        assert log["rfq_id"] == rfq_a_id

