import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.schemas.buyer import BuyerCreate

logger = logging.getLogger(__name__)


def create_buyer(db: Session, buyer_in: BuyerCreate) -> Buyer:
    """
    Create a new buyer record with email normalization and duplicate check.
    Raises HTTP 409 if a buyer with the same email already exists.
    """
    normalized_email = buyer_in.email.strip().lower()

    # Case-insensitive duplicate check
    existing_buyer = (
        db.query(Buyer)
        .filter(func.lower(Buyer.email) == normalized_email)
        .first()
    )
    if existing_buyer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A buyer with email '{normalized_email}' already exists",
        )

    buyer = Buyer(
        name=buyer_in.name,
        email=normalized_email,
        company_name=buyer_in.company_name,
    )
    try:
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
        return buyer
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating buyer: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A buyer with email '{normalized_email}' already exists",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating buyer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the buyer.",
        )


def get_buyer_by_id(db: Session, buyer_id: UUID) -> Buyer:
    """
    Retrieve a buyer by UUID.
    Raises HTTP 404 if the buyer does not exist.
    """
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Buyer with id '{buyer_id}' not found",
        )
    return buyer


def get_buyer_by_email(db: Session, email: str) -> Optional[Buyer]:
    """
    Retrieve a buyer by email address (case-insensitive).
    """
    normalized_email = email.strip().lower()
    return (
        db.query(Buyer)
        .filter(func.lower(Buyer.email) == normalized_email)
        .first()
    )


def list_buyers(
    db: Session, skip: int = 0, limit: int = 100, email: Optional[str] = None
) -> List[Buyer]:
    """
    List buyers ordered by creation date descending with pagination and optional email filter.
    """
    query = db.query(Buyer)
    if email:
        query = query.filter(func.lower(Buyer.email) == email.strip().lower())
    return (
        query.order_by(Buyer.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

