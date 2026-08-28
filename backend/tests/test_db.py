import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

# Ensure backend root is in sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.db.database import engine, SessionLocal, get_db
from app.db.base import Base
from app.main import app
from app.models import (
    Buyer,
    Supplier,
    RFQ,
    RFQItem,
    RFQSupplier,
    Quote,
    Auction,
    AuctionRound,
    Bid,
    ActivityLog,
    RFQStatus,
    RFQSupplierStatus,
    QuoteStatus,
    AuctionStatus,
    AuctionRoundStatus,
    ActorType,
    EventType,
)


def test_database_settings_loaded():
    """Verify that settings correctly load project config and database URL."""
    assert settings.PROJECT_NAME == "British Auction RFQ System"
    assert settings.DATABASE_URL is not None
    assert "british_auction" in settings.DATABASE_URL


def test_database_connection():
    """Verify direct connection to the database via SQLAlchemy engine."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_required_tables_exist():
    """Verify all 10 core entity tables exist in the database."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    expected_tables = {
        "buyers",
        "suppliers",
        "rfqs",
        "rfq_items",
        "rfq_suppliers",
        "quotes",
        "auctions",
        "auction_rounds",
        "bids",
        "activity_logs",
    }
    
    for table in expected_tables:
        assert table in existing_tables, f"Expected table '{table}' not found in database"


def test_table_foreign_keys_and_indexes():
    """Verify foreign keys and indexes on key tables."""
    inspector = inspect(engine)
    
    # Check RFQ Foreign Keys
    rfq_fks = inspector.get_foreign_keys("rfqs")
    assert any(fk["referred_table"] == "buyers" for fk in rfq_fks)
    
    # Check Auction Foreign Keys & Unique Constraint
    auction_fks = inspector.get_foreign_keys("auctions")
    assert any(fk["referred_table"] == "rfqs" for fk in auction_fks)
    
    # Check RFQSupplier Unique Constraints
    rfq_sup_uniques = inspector.get_unique_constraints("rfq_suppliers")
    assert any(
        set(u["column_names"]) == {"rfq_id", "supplier_id"}
        for u in rfq_sup_uniques
    )
    
    # Check AuctionRound Unique Constraints
    round_uniques = inspector.get_unique_constraints("auction_rounds")
    assert any(
        set(u["column_names"]) == {"auction_id", "round_number"}
        for u in round_uniques
    )

    # Check Bid Unique Constraints
    bid_uniques = inspector.get_unique_constraints("bids")
    assert any(
        set(u["column_names"]) == {"auction_id", "supplier_id"}
        for u in bid_uniques
    )


def test_health_db_endpoint(client: TestClient):
    """Verify GET /api/v1/health/db returns 200 OK and connected status."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_model_instantiation_and_enums():
    """Verify models and enums are properly defined and can be instantiated."""
    buyer = Buyer(name="Test Buyer", email="buyer@test.com", company_name="Buyer Corp")
    assert buyer.name == "Test Buyer"
    assert buyer.email == "buyer@test.com"
    
    supplier = Supplier(name="Test Supplier", email="supplier@test.com", company_name="Supplier Corp")
    assert supplier.name == "Test Supplier"
    
    assert RFQStatus.DRAFT.value == "DRAFT"
    assert RFQSupplierStatus.INVITED.value == "INVITED"
    assert QuoteStatus.SUBMITTED.value == "SUBMITTED"
    assert AuctionStatus.SCHEDULED.value == "SCHEDULED"
    assert AuctionRoundStatus.ACTIVE.value == "ACTIVE"
    assert ActorType.BUYER.value == "BUYER"
    assert EventType.BID_SUBMITTED.value == "BID_SUBMITTED"
