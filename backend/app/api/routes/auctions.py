from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auction import AuctionListItemResponse, AuctionDetailFullResponse
from app.schemas.activity_log import ActivityLogResponse
from app.services.bid_service import list_auctions, get_auction_detail, get_rfq_activity_logs

router = APIRouter()


@router.get(
    "",
    response_model=List[AuctionListItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List all British Auctions",
    description="Retrieves a list of all British Auctions with RFQ details, current lowest bid, countdown timers, and dynamic status.",
)
def list_auctions_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=100, description="Limit for pagination"),
    db: Session = Depends(get_db),
) -> List[AuctionListItemResponse]:
    return list_auctions(db=db, skip=skip, limit=limit)


@router.get(
    "/{identifier}",
    response_model=AuctionDetailFullResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Auction Details by Auction ID or RFQ ID",
    description="Retrieves complete auction workspace details including British Auction configuration, supplier bids sorted with L1/L2/L3 rankings and quote details, and activity log history.",
)
def get_auction_detail_endpoint(
    identifier: UUID,
    db: Session = Depends(get_db),
) -> AuctionDetailFullResponse:
    return get_auction_detail(db=db, identifier=identifier)


@router.get(
    "/{identifier}/activity",
    response_model=List[ActivityLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Auction Activity Log",
    description="Retrieves chronological activity log events (bid submissions, automatic extensions with trigger reasons).",
)
def get_auction_activity_endpoint(
    identifier: UUID,
    db: Session = Depends(get_db),
) -> List[ActivityLogResponse]:
    # Support lookup by RFQ ID or Auction ID
    detail = get_auction_detail(db=db, identifier=identifier)
    return detail.activity_logs
