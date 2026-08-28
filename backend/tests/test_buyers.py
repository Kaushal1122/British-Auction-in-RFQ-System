import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer


def test_create_buyer_success(client: TestClient, cleanup_tracker):
    """Verify successful buyer creation with 201 Created and correct fields."""
    unique_email = f"john.doe.{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "John Doe",
        "email": unique_email,
        "company_name": "Acme Manufacturing",
    }
    response = client.post("/api/v1/buyers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == unique_email.lower()
    assert data["company_name"] == "Acme Manufacturing"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    cleanup_tracker.track_buyer(uuid.UUID(data["id"]))


def test_create_buyer_email_normalization(client: TestClient, cleanup_tracker):
    """Verify email whitespace trimming and lowercasing."""
    unique_user = uuid.uuid4().hex[:8]
    raw_email = f"  Alice.{unique_user}@EXAMPLE.COM  "
    payload = {
        "name": "Alice Smith",
        "email": raw_email,
    }
    response = client.post("/api/v1/buyers", json=payload)
    assert response.status_code == 201
    data = response.json()
    expected_email = f"alice.{unique_user}@example.com"
    assert data["email"] == expected_email
    cleanup_tracker.track_buyer(uuid.UUID(data["id"]))


def test_create_buyer_duplicate_email_rejected(client: TestClient, cleanup_tracker):
    """Verify duplicate email (including case variations) returns 409 Conflict."""
    unique_email = f"duplicate.buyer.{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Buyer One",
        "email": unique_email.upper(),
        "company_name": "First Corp",
    }
    resp1 = client.post("/api/v1/buyers", json=payload)
    assert resp1.status_code == 201
    buyer_id = resp1.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(buyer_id))

    # Attempt to create second buyer with identical email in lowercase
    payload2 = {
        "name": "Buyer Two",
        "email": unique_email.lower(),
        "company_name": "Second Corp",
    }
    resp2 = client.post("/api/v1/buyers", json=payload2)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_get_existing_buyer(client: TestClient, cleanup_tracker):
    """Verify GET /api/v1/buyers/{buyer_id} retrieves buyer details."""
    unique_email = f"lookup.buyer.{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Lookup Buyer",
        "email": unique_email,
        "company_name": "Lookup Ltd",
    }
    create_resp = client.post("/api/v1/buyers", json=payload)
    assert create_resp.status_code == 201
    buyer_id = create_resp.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(buyer_id))

    get_resp = client.get(f"/api/v1/buyers/{buyer_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == buyer_id
    assert data["name"] == "Lookup Buyer"
    assert data["email"] == unique_email.lower()
    assert data["company_name"] == "Lookup Ltd"


def test_get_non_existing_buyer_returns_404(client: TestClient):
    """Verify GET /api/v1/buyers/{non_existent_id} returns 404 Not Found."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/buyers/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_buyer_validation_errors(client: TestClient):
    """Verify validation errors for empty name, invalid email, etc. return 422."""
    # Empty name
    resp1 = client.post("/api/v1/buyers", json={"name": "   ", "email": "valid@email.com"})
    assert resp1.status_code == 422

    # Missing name
    resp2 = client.post("/api/v1/buyers", json={"email": "valid@email.com"})
    assert resp2.status_code == 422

    # Invalid email format
    resp3 = client.post("/api/v1/buyers", json={"name": "Valid Name", "email": "not-an-email"})
    assert resp3.status_code == 422


def test_get_buyer_invalid_uuid_returns_422(client: TestClient):
    """Verify invalid UUID string in URL returns 422 Unprocessable Entity."""
    response = client.get("/api/v1/buyers/not-a-valid-uuid")
    assert response.status_code == 422


def test_list_buyers_success(client: TestClient, cleanup_tracker):
    """Verify GET /api/v1/buyers returns 200 and list of buyers."""
    unique_suffix = uuid.uuid4().hex[:6]
    b1_resp = client.post("/api/v1/buyers", json={
        "name": f"List Buyer 1 {unique_suffix}",
        "email": f"list1_{unique_suffix}@example.com",
        "company_name": "Corp 1",
    })
    b2_resp = client.post("/api/v1/buyers", json={
        "name": f"List Buyer 2 {unique_suffix}",
        "email": f"list2_{unique_suffix}@example.com",
        "company_name": "Corp 2",
    })
    assert b1_resp.status_code == 201
    assert b2_resp.status_code == 201

    b1_id = b1_resp.json()["id"]
    b2_id = b2_resp.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(b1_id))
    cleanup_tracker.track_buyer(uuid.UUID(b2_id))

    list_resp = client.get("/api/v1/buyers?limit=100")
    assert list_resp.status_code == 200
    buyers = list_resp.json()
    assert isinstance(buyers, list)
    assert len(buyers) >= 2

    ids = [b["id"] for b in buyers]
    assert b1_id in ids
    assert b2_id in ids

    # Check response schema fields
    first_match = next(b for b in buyers if b["id"] == b1_id)
    assert "name" in first_match
    assert "email" in first_match
    assert "company_name" in first_match
    assert "created_at" in first_match
    assert "updated_at" in first_match


def test_list_buyers_pagination(client: TestClient, cleanup_tracker):
    """Verify pagination with skip and limit parameters."""
    unique_suffix = uuid.uuid4().hex[:6]
    created_ids = []
    for i in range(3):
        resp = client.post("/api/v1/buyers", json={
            "name": f"Paging Buyer {i} {unique_suffix}",
            "email": f"paging_{i}_{unique_suffix}@example.com",
        })
        assert resp.status_code == 201
        b_id = resp.json()["id"]
        cleanup_tracker.track_buyer(uuid.UUID(b_id))
        created_ids.append(b_id)

    # Request limit=2
    resp_limit = client.get("/api/v1/buyers?limit=2")
    assert resp_limit.status_code == 200
    data = resp_limit.json()
    assert len(data) == 2

    # Request skip=1, limit=2
    resp_skip = client.get("/api/v1/buyers?skip=1&limit=2")
    assert resp_skip.status_code == 200
    data_skip = resp_skip.json()
    assert len(data_skip) == 2


def test_same_buyer_can_create_multiple_rfqs(client: TestClient, cleanup_tracker):
    """Verify that a single existing buyer can be associated with multiple RFQs."""
    unique_suffix = uuid.uuid4().hex[:6]
    buyer_resp = client.post("/api/v1/buyers", json={
        "name": f"Multi RFQ Buyer {unique_suffix}",
        "email": f"multirfq_{unique_suffix}@example.com",
        "company_name": "Multi RFQ Industries",
    })
    assert buyer_resp.status_code == 201
    buyer_id = buyer_resp.json()["id"]
    cleanup_tracker.track_buyer(uuid.UUID(buyer_id))

    # Create RFQ 1 with Buyer A
    rfq1_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Procurement Project Alpha",
        "description": "First RFQ for Buyer A",
        "currency": "USD",
        "baseline_price": 50000.0,
        "items": [
            {"name": "Part Alpha", "quantity": 100, "unit": "units"}
        ],
    })
    assert rfq1_resp.status_code == 201
    rfq1_id = rfq1_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq1_id))
    assert rfq1_resp.json()["buyer_id"] == buyer_id

    # Create RFQ 2 with SAME Buyer A
    rfq2_resp = client.post("/api/v1/rfqs", json={
        "buyer_id": buyer_id,
        "title": "Procurement Project Beta",
        "description": "Second RFQ for SAME Buyer A",
        "currency": "USD",
        "baseline_price": 75000.0,
        "items": [
            {"name": "Part Beta", "quantity": 50, "unit": "units"}
        ],
    })
    assert rfq2_resp.status_code == 201
    rfq2_id = rfq2_resp.json()["id"]
    cleanup_tracker.track_rfq(uuid.UUID(rfq2_id))
    assert rfq2_resp.json()["buyer_id"] == buyer_id

    # Verify both RFQs exist and belong to the same buyer
    get_rfq1 = client.get(f"/api/v1/rfqs/{rfq1_id}")
    get_rfq2 = client.get(f"/api/v1/rfqs/{rfq2_id}")
    assert get_rfq1.status_code == 200
    assert get_rfq2.status_code == 200
    assert get_rfq1.json()["buyer_id"] == buyer_id
    assert get_rfq2.json()["buyer_id"] == buyer_id

