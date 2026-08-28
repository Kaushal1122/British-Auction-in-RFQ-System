from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuctionStatus, ExtensionTrigger, RFQStatus
from app.schemas.buyer import BuyerResponse
from app.schemas.rfq import RFQItemResponse
from app.schemas.bid import RankedBidItem
from app.schemas.activity_log import ActivityLogResponse


class AuctionListItemResponse(BaseModel):
    id: UUID
    rfq_id: UUID
    rfq_title: str
    currency: str = "USD"
    baseline_price: Optional[Decimal] = None
    lowest_bid: Optional[Decimal] = None
    lowest_bidder_name: Optional[str] = None
    lowest_bidder_id: Optional[UUID] = None
    bid_start_time: Optional[datetime] = None
    bid_close_time: Optional[datetime] = None
    forced_bid_close_time: Optional[datetime] = None
    trigger_window_minutes: int = 10
    extension_duration_minutes: int = 5
    extension_trigger: ExtensionTrigger = ExtensionTrigger.BID_RECEIVED
    status: AuctionStatus = AuctionStatus.SCHEDULED
    display_status: str = "Active"
    total_bids: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuctionDetailFullResponse(BaseModel):
    id: UUID
    rfq_id: UUID
    rfq_title: str
    rfq_description: Optional[str] = None
    rfq_category: Optional[str] = None
    currency: str = "USD"
    baseline_price: Optional[Decimal] = None
    pickup_service_date: Optional[datetime] = None
    rfq_status: RFQStatus = RFQStatus.DRAFT

    # Auction schedule & configuration
    bid_start_time: Optional[datetime] = None
    bid_close_time: Optional[datetime] = None
    forced_bid_close_time: Optional[datetime] = None
    trigger_window_minutes: int = 10
    extension_duration_minutes: int = 5
    extension_trigger: ExtensionTrigger = ExtensionTrigger.BID_RECEIVED
    status: AuctionStatus = AuctionStatus.SCHEDULED
    display_status: str = "Active"
    current_round: int = 1
    created_at: datetime
    updated_at: datetime

    # Metrics
    lowest_bid: Optional[Decimal] = None
    lowest_bidder_name: Optional[str] = None
    total_bids: int = 0

    # Associated nested objects
    buyer: Optional[BuyerResponse] = None
    items: List[RFQItemResponse] = Field(default_factory=list)
    bids: List[RankedBidItem] = Field(default_factory=list)
    activity_logs: List[ActivityLogResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
