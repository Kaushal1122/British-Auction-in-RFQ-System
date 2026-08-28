import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.activity_log import ActivityLog
from app.models.enums import RFQStatus, AuctionStatus, AuctionRoundStatus, ExtensionTrigger, EventType, ActorType
from app.schemas.rfq import RFQCreate, RFQItemCreate
from app.services.rfq_service import create_rfq



@pytest.fixture
def sample_buyer(client: TestClient, cleanup_tracker) -> dict:
    """Fixture providing a newly created buyer for RFQ tests."""
    email = f"rfq.buyer.{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Procurement Officer",
        "email": email,
        "company_name": "Global Logistics Inc",
    }
    resp = client.post("/api/v1/buyers", json=payload)
    assert resp.status_code == 201
    buyer_data = resp.json()
    cleanup_tracker.track_buyer(uuid.UUID(buyer_data["id"]))
    return buyer_data


def test_create_rfq_multiple_items(client: TestClient, sample_buyer: dict, cleanup_tracker):
    """Verify RFQ creation with multiple line items."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Industrial Bearing & Pump Procurement",
        "description": "Bulk procurement for Q3 facility upgrades",
        "category": "Industrial Machinery",
        "currency": "USD",
        "baseline_price": 50000.00,
        "items": [
            {
                "name": "Steel Roller Bearing",
                "description": "High load 50mm bore",
                "quantity": 100,
                "unit": "units",
            },
            {
                "name": "Hydraulic Pump 5HP",
                "description": "Variable displacement pump",
                "quantity": 20,
                "unit": "units",
            },
            {
                "name": "High Pressure Seal Kit",
                "description": "NBR O-ring assortment",
                "quantity": 50,
                "unit": "sets",
            },
        ],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["title"] == payload["title"]
    assert data["status"] == "DRAFT"
    assert data["currency"] == "USD"
    assert float(data["baseline_price"]) == 50000.00
    assert data["buyer_id"] == sample_buyer["id"]
    assert len(data["items"]) == 3

    # Check item details
    item_names = [it["name"] for it in data["items"]]
    assert "Steel Roller Bearing" in item_names
    assert "Hydraulic Pump 5HP" in item_names
    assert "High Pressure Seal Kit" in item_names

    cleanup_tracker.track_rfq(uuid.UUID(data["id"]))


def test_create_rfq_single_item(client: TestClient, sample_buyer: dict, cleanup_tracker):
    """Verify RFQ creation with exactly one line item."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Single Equipment Procurement",
        "baseline_price": 12000.50,
        "items": [
            {
                "name": "CNC Milling Spindle",
                "quantity": 1,
                "unit": "unit",
            }
        ],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Single Equipment Procurement"
    assert data["currency"] == "USD"  # Defaults to USD
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "CNC Milling Spindle"
    assert float(data["items"][0]["quantity"]) == 1.0

    cleanup_tracker.track_rfq(uuid.UUID(data["id"]))


def test_create_rfq_invalid_buyer_rejected(client: TestClient):
    """Verify RFQ creation fails with 404 if buyer does not exist."""
    fake_buyer_id = str(uuid.uuid4())
    payload = {
        "buyer_id": fake_buyer_id,
        "title": "Invalid Buyer RFQ",
        "baseline_price": 1000.00,
        "items": [{"name": "Test Item", "quantity": 10, "unit": "units"}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 404
    assert f"Buyer with id '{fake_buyer_id}' not found" in response.json()["detail"]


def test_create_rfq_missing_or_empty_title_rejected(client: TestClient, sample_buyer: dict):
    """Verify empty/whitespace title is rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "    ",
        "baseline_price": 1000.00,
        "items": [{"name": "Test Item", "quantity": 10}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_create_rfq_negative_baseline_price_rejected(client: TestClient, sample_buyer: dict):
    """Verify negative baseline price is rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Negative Price RFQ",
        "baseline_price": -50.00,
        "items": [{"name": "Test Item", "quantity": 10}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_create_rfq_empty_items_rejected(client: TestClient, sample_buyer: dict):
    """Verify empty items list is rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "No Items RFQ",
        "baseline_price": 1000.00,
        "items": [],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_create_rfq_invalid_quantity_rejected(client: TestClient, sample_buyer: dict):
    """Verify items with quantity <= 0 are rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Zero Quantity RFQ",
        "baseline_price": 1000.00,
        "items": [{"name": "Test Item", "quantity": 0, "unit": "units"}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_create_rfq_invalid_currency_rejected(client: TestClient, sample_buyer: dict):
    """Verify non 3-character/invalid currency is rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Invalid Currency RFQ",
        "currency": "US1",
        "baseline_price": 1000.00,
        "items": [{"name": "Test Item", "quantity": 5}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_get_rfq_detail(client: TestClient, sample_buyer: dict, cleanup_tracker):
    """Verify GET /api/v1/rfqs/{rfq_id} returns complete RFQ, buyer info, and line items."""
    create_payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Precision Sensors Order",
        "category": "Electronics",
        "baseline_price": 25000.00,
        "items": [
            {"name": "Pressure Sensor 0-10 Bar", "quantity": 40, "unit": "pcs"},
            {"name": "Temperature Transducer", "quantity": 15, "unit": "pcs"},
        ],
    }
    create_resp = client.post("/api/v1/rfqs", json=create_payload)
    assert create_resp.status_code == 201
    rfq_id = create_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq_id))

    get_resp = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == rfq_id
    assert data["title"] == "Precision Sensors Order"
    assert data["status"] == "DRAFT"
    assert data["buyer"]["id"] == sample_buyer["id"]
    assert data["buyer"]["email"] == sample_buyer["email"]
    assert len(data["items"]) == 2


def test_get_non_existing_rfq_returns_404(client: TestClient):
    """Verify GET /api/v1/rfqs/{non_existent_id} returns 404 Not Found."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/rfqs/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_rfqs(client: TestClient, sample_buyer: dict, cleanup_tracker):
    """Verify GET /api/v1/rfqs lists RFQs with correct summary fields."""
    rfq1_payload = {
        "buyer_id": sample_buyer["id"],
        "title": "List Test RFQ 1",
        "baseline_price": 5000.00,
        "items": [{"name": "Item A", "quantity": 10}],
    }
    resp1 = client.post("/api/v1/rfqs", json=rfq1_payload)
    assert resp1.status_code == 201
    cleanup_tracker.track_rfq(uuid.UUID(resp1.json()["id"]))

    list_resp = client.get("/api/v1/rfqs")
    assert list_resp.status_code == 200
    rfqs = list_resp.json()
    assert isinstance(rfqs, list)
    assert len(rfqs) >= 1

    matching = next((r for r in rfqs if r["id"] == resp1.json()["id"]), None)
    assert matching is not None
    assert matching["title"] == "List Test RFQ 1"
    assert matching["items_count"] == 1
    assert "baseline_price" in matching
    assert "currency" in matching
    assert "status" in matching
    assert "created_at" in matching


def test_rfq_and_items_persisted_in_database(client: TestClient, sample_buyer: dict, db: Session, cleanup_tracker):
    """Verify RFQ, RFQ items, and ActivityLog are actually persisted in PostgreSQL."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Database Persistence Check RFQ",
        "description": "Verifying database write",
        "category": "Test Category",
        "baseline_price": 75000.00,
        "items": [
            {"name": "Turbine Valve", "quantity": 4, "unit": "units"},
            {"name": "Gasket Pack", "quantity": 12, "unit": "packs"},
        ],
    }
    resp = client.post("/api/v1/rfqs", json=payload)
    assert resp.status_code == 201
    rfq_id = uuid.UUID(resp.json()["id"])
    cleanup_tracker.track_rfq(rfq_id)

    # Query database directly using session
    db_rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    assert db_rfq is not None
    assert db_rfq.title == "Database Persistence Check RFQ"
    assert db_rfq.status == RFQStatus.DRAFT
    assert db_rfq.baseline_price == Decimal("75000.00")

    # Check RFQ items in db
    db_items = db.query(RFQItem).filter(RFQItem.rfq_id == rfq_id).all()
    assert len(db_items) == 2
    item_names = {it.name for it in db_items}
    assert "Turbine Valve" in item_names
    assert "Gasket Pack" in item_names

    # Check ActivityLog in db
    db_logs = db.query(ActivityLog).filter(ActivityLog.rfq_id == rfq_id).all()
    assert len(db_logs) == 1
    assert db_logs[0].event_type == EventType.RFQ_CREATED
    assert db_logs[0].actor_type == ActorType.BUYER
    assert db_logs[0].actor_id == uuid.UUID(sample_buyer["id"])


def test_failed_rfq_transaction_leaves_no_orphan_records(db: Session, sample_buyer: dict):
    """
    Verify transaction atomicity: if an exception occurs during the transaction
    (e.g., database constraint failure or runtime error), no RFQ or items remain in DB.
    """
    buyer_uuid = uuid.UUID(sample_buyer["id"])
    initial_rfq_count = db.query(RFQ).filter(RFQ.buyer_id == buyer_uuid).count()
    initial_item_count = db.query(RFQItem).count()
    initial_log_count = db.query(ActivityLog).count()

    # Construct invalid RFQCreate with an item that triggers a DB error when saving
    # Let's test that if create_rfq is called and fails mid-transaction, everything rolls back
    rfq_in = RFQCreate(
        buyer_id=buyer_uuid,
        title="Transaction Rollback Test RFQ",
        baseline_price=Decimal("1000.00"),
        items=[
            RFQItemCreate(name="Valid Item", quantity=Decimal("5.0"), unit="units"),
        ],
    )

    # Simulate failure by passing an invalid item or forcing a failure during commit
    try:
        # Create an RFQItem directly with invalid DB constraint
        rfq = RFQ(
            buyer_id=buyer_uuid,
            title="Rollback RFQ",
            baseline_price=Decimal("1000.00"),
            status=RFQStatus.DRAFT,
        )
        db.add(rfq)
        db.flush()

        # Add an item violating database check constraint (quantity <= 0)
        invalid_item = RFQItem(
            rfq_id=rfq.id,
            name="Invalid Item",
            quantity=Decimal("-5.0"),  # Violates check_rfq_item_quantity_positive constraint
            unit="units",
        )
        db.add(invalid_item)
        db.commit()
    except Exception:
        db.rollback()

    # Verify no new RFQs or items were committed
    final_rfq_count = db.query(RFQ).filter(RFQ.buyer_id == buyer_uuid).count()
    final_item_count = db.query(RFQItem).count()
    final_log_count = db.query(ActivityLog).count()

    assert final_rfq_count == initial_rfq_count
    assert final_item_count == initial_item_count
    assert final_log_count == initial_log_count


# ==============================================================================
# STEP 8 PRE-REQUISITE TESTS: AUCTION SCHEDULE & BRITISH AUCTION CONFIGURATION
# ==============================================================================

def test_create_rfq_with_valid_auction_timing_and_configuration(client: TestClient, sample_buyer: dict, db: Session, cleanup_tracker):
    """Verify RFQ creation with full valid auction schedule and British auction extension parameters."""
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 11, 30, 0, tzinfo=timezone.utc)
    pickup_date = datetime(2026, 9, 15, 9, 0, 0, tzinfo=timezone.utc)

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Industrial Valve Procurement",
        "description": "High pressure valve components",
        "category": "Industrial Machinery",
        "currency": "USD",
        "baseline_price": 60000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "pickup_service_date": pickup_date.isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger": "BID_RECEIVED",
        "items": [
            {"name": "Control Valve DN50", "quantity": 10, "unit": "units"}
        ],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 201
    data = response.json()
    rfq_id = uuid.UUID(data["id"])
    cleanup_tracker.track_rfq(rfq_id)

    # Verify response contains top-level timing and auction object
    assert data["title"] == "Industrial Valve Procurement"
    assert data["trigger_window_minutes"] == 10
    assert data["extension_duration_minutes"] == 5
    assert data["extension_trigger"] == "BID_RECEIVED"
    assert data["auction"] is not None
    assert data["auction"]["trigger_window_minutes"] == 10
    assert data["auction"]["extension_duration_minutes"] == 5
    assert data["auction"]["extension_trigger"] == "BID_RECEIVED"
    assert data["auction"]["status"] == "SCHEDULED"

    # Verify directly in PostgreSQL
    db_rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    assert db_rfq is not None
    assert db_rfq.pickup_service_date is not None
    assert db_rfq.auction is not None
    assert db_rfq.auction.start_time == start_time
    assert db_rfq.auction.end_time == close_time
    assert db_rfq.auction.forced_bid_close_time == forced_close
    assert db_rfq.auction.trigger_window_minutes == 10
    assert db_rfq.auction.extension_duration_minutes == 5
    assert db_rfq.auction.extension_trigger == ExtensionTrigger.BID_RECEIVED

    # Verify initial round in PostgreSQL
    rounds = db.query(AuctionRound).filter(AuctionRound.auction_id == db_rfq.auction.id).all()
    assert len(rounds) == 1
    assert rounds[0].round_number == 1
    assert rounds[0].status == AuctionRoundStatus.PENDING


def test_create_rfq_forced_close_before_bid_close_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails if forced close time is earlier than bid close time."""
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 10, 30, 0, tzinfo=timezone.utc)  # Invalid: earlier than close

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Invalid Forced Close RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422
    assert "Forced close time must be later than bid close time" in str(response.json())


def test_create_rfq_forced_close_equal_to_bid_close_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails if forced close time is exactly equal to bid close time."""
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)  # Invalid: equal to close

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Equal Forced Close RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422
    assert "Forced close time must be later than bid close time" in str(response.json())


def test_create_rfq_bid_close_before_start_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails if bid close time is earlier than bid start time."""
    start_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)  # Invalid: earlier than start
    forced_close = datetime(2026, 9, 1, 13, 0, 0, tzinfo=timezone.utc)

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Invalid Chronology RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422
    assert "Bid close time must be later than bid start time" in str(response.json())


def test_create_rfq_non_positive_trigger_window_rejected(client: TestClient, sample_buyer: dict):
    """Verify trigger window <= 0 is rejected with 422."""
    for invalid_x in [0, -5]:
        payload = {
            "buyer_id": sample_buyer["id"],
            "title": "Invalid Trigger Window RFQ",
            "baseline_price": 5000.00,
            "trigger_window_minutes": invalid_x,
            "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
        }
        response = client.post("/api/v1/rfqs", json=payload)
        assert response.status_code == 422


def test_create_rfq_non_positive_extension_duration_rejected(client: TestClient, sample_buyer: dict):
    """Verify extension duration <= 0 is rejected with 422."""
    for invalid_y in [0, -10]:
        payload = {
            "buyer_id": sample_buyer["id"],
            "title": "Invalid Duration RFQ",
            "baseline_price": 5000.00,
            "extension_duration_minutes": invalid_y,
            "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
        }
        response = client.post("/api/v1/rfqs", json=payload)
        assert response.status_code == 422


@pytest.mark.parametrize("trigger_type", ["BID_RECEIVED", "ANY_RANK_CHANGE", "L1_RANK_CHANGE"])
def test_create_rfq_all_extension_triggers_accepted(client: TestClient, sample_buyer: dict, cleanup_tracker, trigger_type: str):
    """Verify all 3 British Auction extension trigger modes are accepted and persisted."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": f"Trigger Mode {trigger_type} RFQ",
        "baseline_price": 10000.00,
        "extension_trigger": trigger_type,
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["extension_trigger"] == trigger_type
    assert data["auction"]["extension_trigger"] == trigger_type
    cleanup_tracker.track_rfq(uuid.UUID(data["id"]))


def test_create_rfq_invalid_extension_trigger_rejected(client: TestClient, sample_buyer: dict):
    """Verify unrecognized extension trigger is rejected with 422."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Invalid Trigger RFQ",
        "baseline_price": 10000.00,
        "extension_trigger": "INVALID_TRIGGER_TYPE",
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_get_rfq_returns_persisted_auction_configuration(client: TestClient, sample_buyer: dict, cleanup_tracker):
    """Verify GET /api/v1/rfqs/{rfq_id} returns all persisted auction configuration fields."""
    start_time = datetime(2026, 9, 5, 14, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 5, 15, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 5, 15, 45, 0, tzinfo=timezone.utc)

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Config Retrieval Test RFQ",
        "baseline_price": 85000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "trigger_window_minutes": 15,
        "extension_duration_minutes": 8,
        "extension_trigger": "ANY_RANK_CHANGE",
        "items": [{"name": "Sensor Unit", "quantity": 5, "unit": "pcs"}],
    }

    create_resp = client.post("/api/v1/rfqs", json=payload)
    assert create_resp.status_code == 201
    rfq_id = create_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq_id))

    # Retrieve via GET
    get_resp = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["id"] == rfq_id
    assert data["trigger_window_minutes"] == 15
    assert data["extension_duration_minutes"] == 8
    assert data["extension_trigger"] == "ANY_RANK_CHANGE"
    assert data["auction"]["trigger_window_minutes"] == 15
    assert data["auction"]["extension_duration_minutes"] == 8
    assert data["auction"]["extension_trigger"] == "ANY_RANK_CHANGE"


def test_create_rfq_start_equal_close_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails if bid start time is equal to bid close time."""
    start_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)  # Invalid: start == close
    forced_close = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Start Equal Close RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422
    assert "Bid close time must be later than bid start time" in str(response.json())


def test_create_rfq_start_after_forced_close_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails if bid start time is later than forced close time."""
    start_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    close_time = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    forced_close = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)  # Invalid: start > forced

    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Start After Forced Close RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": start_time.isoformat(),
        "bid_close_time": close_time.isoformat(),
        "forced_bid_close_time": forced_close.isoformat(),
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422


def test_create_rfq_invalid_datetime_format_rejected(client: TestClient, sample_buyer: dict):
    """Verify RFQ creation fails with 422 if datetime string format is invalid."""
    payload = {
        "buyer_id": sample_buyer["id"],
        "title": "Invalid Date Format RFQ",
        "baseline_price": 5000.00,
        "bid_start_time": "invalid-datetime-string",
        "bid_close_time": "another-invalid-date",
        "forced_bid_close_time": "not-a-valid-timestamp",
        "items": [{"name": "Test Item", "quantity": 1, "unit": "units"}],
    }

    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422

