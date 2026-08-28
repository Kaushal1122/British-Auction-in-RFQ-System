from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.rfq import RFQCreate, RFQDetailResponse, RFQListItemResponse
from app.schemas.bid import RFQRankingResponse
from app.schemas.activity_log import ActivityLogResponse
from app.services.rfq_service import create_rfq, get_rfq_by_id, list_rfqs
from app.services.bid_service import get_rfq_bid_ranking, get_rfq_activity_logs

router = APIRouter()



@router.post(
    "",
    response_model=RFQDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an RFQ with items",
    description="Atomically creates an RFQ along with all provided line items and logs the RFQ_CREATED activity event.",
)
def create_rfq_endpoint(
    rfq_in: RFQCreate,
    db: Session = Depends(get_db),
) -> RFQDetailResponse:
    """
    Create a new RFQ (Request for Quotation) with multi-line items:
    - **buyer_id**: UUID of an existing buyer
    - **title**: RFQ title (required)
    - **description**: Detailed requirements (optional)
    - **category**: Category name (optional)
    - **currency**: 3-letter currency code (defaults to USD)
    - **baseline_price**: Ceiling/baseline price >= 0
    - **items**: Array of items (at least 1 item required)
    """
    return create_rfq(db=db, rfq_in=rfq_in)


@router.get(
    "/{rfq_id}",
    response_model=RFQDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get RFQ by ID",
    description="Retrieves full RFQ details including associated line items and buyer profile.",
)
def get_rfq_endpoint(
    rfq_id: UUID,
    db: Session = Depends(get_db),
) -> RFQDetailResponse:
    """
    Retrieve full details for an RFQ:
    - **rfq_id**: UUID of the RFQ
    """
    return get_rfq_by_id(db=db, rfq_id=rfq_id)


@router.get(
    "/{rfq_id}/ranking",
    response_model=RFQRankingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bid rankings for an RFQ",
    description="Calculates and returns deterministic bid rankings (lowest amount = Rank 1) for all valid bids submitted against an RFQ.",
)
def get_rfq_ranking_endpoint(
    rfq_id: UUID,
    db: Session = Depends(get_db),
) -> RFQRankingResponse:
    """
    Retrieve bid rankings for an RFQ:
    - **rfq_id**: UUID of the target RFQ
    - Lowest bid receives Rank 1
    - Deterministic tie-breaking by submission timestamp and UUID
    - Returns empty rankings list if no bids have been placed
    """
    return get_rfq_bid_ranking(db=db, rfq_id=rfq_id)


@router.get(
    "/{rfq_id}/activity",
    response_model=List[ActivityLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get RFQ Activity Logs",
    description="Retrieves chronological activity log events for an RFQ (bid submissions, extensions, creations).",
)
def get_rfq_activity_endpoint(
    rfq_id: UUID,
    db: Session = Depends(get_db),
) -> List[ActivityLogResponse]:
    return get_rfq_activity_logs(db=db, rfq_id=rfq_id)


@router.get(
    "",
    response_model=List[RFQListItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List RFQs",
    description="Returns a list of RFQs with summary info and items count.",
)
def list_rfqs_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=100, description="Limit for pagination"),
    db: Session = Depends(get_db),
) -> List[RFQListItemResponse]:
    """
    List RFQs ordered by creation date descending.
    """
    return list_rfqs(db=db, skip=skip, limit=limit)

