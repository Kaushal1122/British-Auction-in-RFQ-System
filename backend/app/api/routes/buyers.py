from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.buyer import BuyerCreate, BuyerResponse
from app.services.buyer_service import (
    create_buyer,
    get_buyer_by_id,
    list_buyers,
)

router = APIRouter()


@router.post(
    "",
    response_model=BuyerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new buyer",
    description="Creates a new buyer with a unique email address and returns the created buyer record.",
)
def create_buyer_endpoint(
    buyer_in: BuyerCreate,
    db: Session = Depends(get_db),
) -> BuyerResponse:
    """
    Create a new buyer profile:
    - **name**: Buyer contact name (required)
    - **email**: Unique email address (required, normalized to lowercase)
    - **company_name**: Company or organization name (optional)
    """
    return create_buyer(db=db, buyer_in=buyer_in)


@router.get(
    "/{buyer_id}",
    response_model=BuyerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get buyer by ID",
    description="Retrieves buyer details for a given buyer UUID.",
)
def get_buyer_endpoint(
    buyer_id: UUID,
    db: Session = Depends(get_db),
) -> BuyerResponse:
    """
    Retrieve a buyer profile by UUID:
    - **buyer_id**: UUID of the buyer
    """
    return get_buyer_by_id(db=db, buyer_id=buyer_id)


@router.get(
    "",
    response_model=List[BuyerResponse],
    status_code=status.HTTP_200_OK,
    summary="List buyers",
    description="Returns a list of buyers ordered by creation date descending.",
)
def list_buyers_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    email: Optional[str] = Query(None, description="Optional filter by exact email address"),
    db: Session = Depends(get_db),
) -> List[BuyerResponse]:
    """
    List buyers with pagination and optional email filter.
    """
    return list_buyers(db=db, skip=skip, limit=limit, email=email)


