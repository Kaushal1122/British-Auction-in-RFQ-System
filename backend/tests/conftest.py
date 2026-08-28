import os
import sys
from typing import Generator, List
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure backend root is on sys.path
backend_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.db.database import SessionLocal
from app.models.buyer import Buyer
from app.models.supplier import Supplier
from app.models.rfq import RFQ
from app.models.rfq_item import RFQItem
from app.models.auction import Auction
from app.models.auction_round import AuctionRound
from app.models.bid import Bid
from app.models.activity_log import ActivityLog


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Test client fixture for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Direct database session fixture with automatic session close."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cleanup_tracker(db: Session):
    """
    Tracks created entities (buyers, suppliers, rfqs, bids) during a test and automatically deletes
    them during teardown to keep the database isolated and clean.
    """
    created_buyer_ids: List[UUID] = []
    created_supplier_ids: List[UUID] = []
    created_rfq_ids: List[UUID] = []
    created_bid_ids: List[UUID] = []

    class Tracker:
        def track_buyer(self, buyer_id: UUID):
            if buyer_id not in created_buyer_ids:
                created_buyer_ids.append(buyer_id)

        def track_supplier(self, supplier_id: UUID):
            if supplier_id not in created_supplier_ids:
                created_supplier_ids.append(supplier_id)

        def track_rfq(self, rfq_id: UUID):
            if rfq_id not in created_rfq_ids:
                created_rfq_ids.append(rfq_id)

        def track_bid(self, bid_id: UUID):
            if bid_id not in created_bid_ids:
                created_bid_ids.append(bid_id)

    tracker = Tracker()
    yield tracker

    # Teardown: delete tracked records in correct dependency order
    try:
        for bid_id in created_bid_ids:
            db.query(Bid).filter(Bid.id == bid_id).delete(synchronize_session=False)

        for rfq_id in created_rfq_ids:
            auctions = db.query(Auction).filter(Auction.rfq_id == rfq_id).all()
            for auc in auctions:
                db.query(Bid).filter(Bid.auction_id == auc.id).delete(synchronize_session=False)
                db.query(AuctionRound).filter(AuctionRound.auction_id == auc.id).delete(synchronize_session=False)
                db.query(ActivityLog).filter(ActivityLog.auction_id == auc.id).delete(synchronize_session=False)
                db.query(Auction).filter(Auction.id == auc.id).delete(synchronize_session=False)

            db.query(ActivityLog).filter(ActivityLog.rfq_id == rfq_id).delete(synchronize_session=False)
            db.query(RFQItem).filter(RFQItem.rfq_id == rfq_id).delete(synchronize_session=False)
            db.query(RFQ).filter(RFQ.id == rfq_id).delete(synchronize_session=False)

        for buyer_id in created_buyer_ids:
            rfqs = db.query(RFQ).filter(RFQ.buyer_id == buyer_id).all()
            for rfq in rfqs:
                auctions = db.query(Auction).filter(Auction.rfq_id == rfq.id).all()
                for auc in auctions:
                    db.query(Bid).filter(Bid.auction_id == auc.id).delete(synchronize_session=False)
                    db.query(AuctionRound).filter(AuctionRound.auction_id == auc.id).delete(synchronize_session=False)
                    db.query(ActivityLog).filter(ActivityLog.auction_id == auc.id).delete(synchronize_session=False)
                    db.query(Auction).filter(Auction.id == auc.id).delete(synchronize_session=False)

                db.query(ActivityLog).filter(ActivityLog.rfq_id == rfq.id).delete(synchronize_session=False)
                db.query(RFQItem).filter(RFQItem.rfq_id == rfq.id).delete(synchronize_session=False)
                db.query(RFQ).filter(RFQ.id == rfq.id).delete(synchronize_session=False)
            db.query(Buyer).filter(Buyer.id == buyer_id).delete(synchronize_session=False)

        for supplier_id in created_supplier_ids:
            db.query(Bid).filter(Bid.supplier_id == supplier_id).delete(synchronize_session=False)
            db.query(Supplier).filter(Supplier.id == supplier_id).delete(synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()

