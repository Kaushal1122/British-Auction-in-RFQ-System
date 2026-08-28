import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.supplier import Supplier


def test_create_supplier_success(client: TestClient, db: Session, cleanup_tracker):
    """Verify successful creation of a new supplier."""
    unique_email = f"supplier_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Acme Industrial Supplies",
        "email": unique_email,
        "company_name": "Acme Corp",
    }

    response = client.post("/api/v1/suppliers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Industrial Supplies"
    assert data["email"] == unique_email.lower()
    assert data["company_name"] == "Acme Corp"
    assert "id" in data
    cleanup_tracker.track_supplier(uuid.UUID(data["id"]))


def test_create_supplier_email_normalization(client: TestClient, db: Session, cleanup_tracker):
    """Verify supplier email is normalized to lowercase."""
    unique_name = f"sup_{uuid.uuid4().hex[:6]}"
    payload = {
        "name": "Normalized Supplier",
        "email": f"  {unique_name.upper()}@EXAMPLE.COM  ",
    }

    response = client.post("/api/v1/suppliers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == f"{unique_name}@example.com"
    cleanup_tracker.track_supplier(uuid.UUID(data["id"]))


def test_create_supplier_duplicate_email_rejected(client: TestClient, db: Session, cleanup_tracker):
    """Verify duplicate email rejection (409 Conflict)."""
    unique_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Supplier One",
        "email": unique_email,
    }

    resp1 = client.post("/api/v1/suppliers", json=payload)
    assert resp1.status_code == 201
    cleanup_tracker.track_supplier(uuid.UUID(resp1.json()["id"]))

    # Duplicate attempt
    resp2 = client.post("/api/v1/suppliers", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_get_existing_supplier(client: TestClient, db: Session, cleanup_tracker):
    """Verify retrieving an existing supplier by ID."""
    unique_email = f"retrieve_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/v1/suppliers", json={"name": "Retrievable Supplier", "email": unique_email})
    assert resp.status_code == 201
    supplier_id = resp.json()["id"]
    cleanup_tracker.track_supplier(uuid.UUID(supplier_id))

    get_resp = client.get(f"/api/v1/suppliers/{supplier_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Retrievable Supplier"
    assert get_resp.json()["id"] == supplier_id


def test_get_non_existing_supplier_returns_404(client: TestClient):
    """Verify 404 for nonexistent supplier UUID."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/suppliers/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_supplier_validation_errors(client: TestClient):
    """Verify validation errors for missing/invalid fields."""
    # Missing name
    r1 = client.post("/api/v1/suppliers", json={"email": "valid@test.com"})
    assert r1.status_code == 422

    # Empty name
    r2 = client.post("/api/v1/suppliers", json={"name": "   ", "email": "valid@test.com"})
    assert r2.status_code == 422

    # Invalid email
    r3 = client.post("/api/v1/suppliers", json={"name": "Supplier", "email": "not-an-email"})
    assert r3.status_code == 422


def test_list_suppliers(client: TestClient, db: Session, cleanup_tracker):
    """Verify listing suppliers with pagination and descending created_at order."""
    unique_suffix = uuid.uuid4().hex[:6]
    s1_resp = client.post("/api/v1/suppliers", json={"name": f"List Sup 1 {unique_suffix}", "email": f"list1_{unique_suffix}@example.com"})
    s2_resp = client.post("/api/v1/suppliers", json={"name": f"List Sup 2 {unique_suffix}", "email": f"list2_{unique_suffix}@example.com"})
    assert s1_resp.status_code == 201
    assert s2_resp.status_code == 201

    cleanup_tracker.track_supplier(uuid.UUID(s1_resp.json()["id"]))
    cleanup_tracker.track_supplier(uuid.UUID(s2_resp.json()["id"]))

    list_resp = client.get("/api/v1/suppliers?limit=100")
    assert list_resp.status_code == 200
    suppliers = list_resp.json()
    assert isinstance(suppliers, list)
    assert len(suppliers) >= 2

    ids = [s["id"] for s in suppliers]
    assert s1_resp.json()["id"] in ids
    assert s2_resp.json()["id"] in ids

