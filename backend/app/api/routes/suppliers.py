from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.supplier import SupplierCreate, SupplierResponse
from app.services.supplier_service import (
    create_supplier,
    get_supplier_by_id,
    list_suppliers,
)

router = APIRouter()


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new supplier",
    description="Creates a new supplier record with unique email address normalization.",
)
def create_supplier_endpoint(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
) -> SupplierResponse:
    """
    Create a new supplier profile:
    - **name**: Supplier representative or company contact name (required)
    - **email**: Unique email address (required, normalized to lowercase)
    - **company_name**: Company or business name (optional)
    """
    return create_supplier(db=db, supplier_in=supplier_in)


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
    summary="Get supplier by ID",
    description="Retrieves supplier details for a given supplier UUID.",
)
def get_supplier_endpoint(
    supplier_id: UUID,
    db: Session = Depends(get_db),
) -> SupplierResponse:
    """
    Retrieve a supplier profile by UUID:
    - **supplier_id**: UUID of the supplier
    """
    return get_supplier_by_id(db=db, supplier_id=supplier_id)


@router.get(
    "",
    response_model=List[SupplierResponse],
    status_code=status.HTTP_200_OK,
    summary="List suppliers",
    description="Returns a list of suppliers ordered by creation date descending.",
)
def list_suppliers_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    email: Optional[str] = Query(None, description="Optional filter by exact email address"),
    db: Session = Depends(get_db),
) -> List[SupplierResponse]:
    """
    List suppliers with pagination and optional email filter.
    """
    return list_suppliers(db=db, skip=skip, limit=limit, email=email)

