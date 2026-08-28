from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.bid import BidCreate, BidResponse
from app.services.bid_service import create_bid, get_bid_by_id, list_bids_for_rfq

router = APIRouter()


@router.post(
    "",
    response_model=BidResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a supplier bid against an RFQ",
    description="Validates supplier eligibility, RFQ readiness, and item association before atomically creating a bid record.",
)
def create_bid_endpoint(
    bid_in: BidCreate,
    db: Session = Depends(get_db),
) -> BidResponse:
    """
    Submit a supplier bid:
    - **rfq_id**: UUID of the target RFQ
    - **supplier_id**: UUID of the bidding supplier
    - **amount**: Numeric bid amount >= 0
    - **rfq_item_id**: Optional UUID of the line item being bid upon
    """
    return create_bid(db=db, bid_in=bid_in)


@router.get(
    "/{bid_id}",
    response_model=BidResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bid by ID",
    description="Retrieves full bid details including supplier profile and auction metadata.",
)
def get_bid_endpoint(
    bid_id: UUID,
    db: Session = Depends(get_db),
) -> BidResponse:
    """
    Retrieve bid details by UUID:
    - **bid_id**: UUID of the bid
    """
    return get_bid_by_id(db=db, bid_id=bid_id)


@router.get(
    "/rfq/{rfq_id}",
    response_model=List[BidResponse],
    status_code=status.HTTP_200_OK,
    summary="List bids for an RFQ",
    description="Retrieves all bids submitted for an RFQ's auction.",
)
def list_rfq_bids_endpoint(
    rfq_id: UUID,
    db: Session = Depends(get_db),
) -> List[BidResponse]:
    """
    List bids for a specific RFQ.
    """
    return list_bids_for_rfq(db=db, rfq_id=rfq_id)
