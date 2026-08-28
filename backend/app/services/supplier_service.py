import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate

logger = logging.getLogger(__name__)


def create_supplier(db: Session, supplier_in: SupplierCreate) -> Supplier:
    """
    Create a new supplier record with email normalization and duplicate check.
    Raises HTTP 409 if a supplier with the same email already exists.
    """
    normalized_email = supplier_in.email.strip().lower()

    # Case-insensitive duplicate check
    existing_supplier = (
        db.query(Supplier)
        .filter(func.lower(Supplier.email) == normalized_email)
        .first()
    )
    if existing_supplier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A supplier with email '{normalized_email}' already exists",
        )

    supplier = Supplier(
        name=supplier_in.name,
        email=normalized_email,
        company_name=supplier_in.company_name,
    )
    try:
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        return supplier
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating supplier: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A supplier with email '{normalized_email}' already exists",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating supplier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the supplier.",
        )


def get_supplier_by_id(db: Session, supplier_id: UUID) -> Supplier:
    """
    Retrieve a supplier by UUID.
    Raises HTTP 404 if the supplier does not exist.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with id '{supplier_id}' not found",
        )
    return supplier


def get_supplier_by_email(db: Session, email: str) -> Optional[Supplier]:
    """
    Retrieve a supplier by email address (case-insensitive).
    """
    normalized_email = email.strip().lower()
    return (
        db.query(Supplier)
        .filter(func.lower(Supplier.email) == normalized_email)
        .first()
    )


def list_suppliers(
    db: Session, skip: int = 0, limit: int = 100, email: Optional[str] = None
) -> List[Supplier]:
    """
    List suppliers ordered by creation date descending with pagination and optional email filter.
    """
    query = db.query(Supplier)
    if email:
        query = query.filter(func.lower(Supplier.email) == email.strip().lower())
    return (
        query.order_by(Supplier.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

