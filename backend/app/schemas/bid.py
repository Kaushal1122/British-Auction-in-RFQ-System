from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.supplier import SupplierResponse


class BidBase(BaseModel):
    amount: Decimal = Field(..., ge=Decimal(0), description="Bid amount submitted by the supplier (must be >= 0)")
    carrier_name: Optional[str] = Field(None, max_length=255, description="Carrier / logistics provider name")
    freight_charges: Optional[Decimal] = Field(None, ge=Decimal(0), description="Freight charges component (must be >= 0)")
    origin_charges: Optional[Decimal] = Field(None, ge=Decimal(0), description="Origin handling charges component (must be >= 0)")
    destination_charges: Optional[Decimal] = Field(None, ge=Decimal(0), description="Destination charges component (must be >= 0)")
    transit_time: Optional[str] = Field(None, max_length=100, description="Estimated transit time (e.g., '5 days')")
    validity_of_quote: Optional[str] = Field(None, max_length=100, description="Validity period of quote (e.g., '30 days')")

    @field_validator("amount")
    @classmethod
    def validate_amount_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Bid amount must be greater than or equal to 0")
        return v


class BidCreate(BidBase):
    rfq_id: UUID = Field(..., description="UUID of the target RFQ")
    supplier_id: UUID = Field(..., description="UUID of the bidding supplier")
    rfq_item_id: Optional[UUID] = Field(None, description="Optional UUID of the specific RFQ line item being bid on")


class BidResponse(BidBase):
    id: UUID
    auction_id: UUID
    round_id: UUID
    supplier_id: UUID
    submitted_at: datetime
    is_valid: bool
    rfq_id: Optional[UUID] = None
    supplier: Optional[SupplierResponse] = None
    auction_end_time: Optional[datetime] = None
    auction_extended: Optional[bool] = None
    extension_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RankedBidItem(BaseModel):
    rank: int = Field(..., ge=1, description="Sequential position rank (1 = lowest bid)")
    bid_id: UUID = Field(..., description="UUID of the bid")
    supplier_id: UUID = Field(..., description="UUID of the bidding supplier")
    supplier_name: Optional[str] = Field(None, description="Name of the bidding supplier")
    supplier_company: Optional[str] = Field(None, description="Company name of the supplier")
    amount: Decimal = Field(..., description="Bid amount")
    carrier_name: Optional[str] = Field(None, description="Carrier name")
    freight_charges: Optional[Decimal] = Field(None, description="Freight charges")
    origin_charges: Optional[Decimal] = Field(None, description="Origin charges")
    destination_charges: Optional[Decimal] = Field(None, description="Destination charges")
    transit_time: Optional[str] = Field(None, description="Transit time")
    validity_of_quote: Optional[str] = Field(None, description="Validity of quote")
    submitted_at: datetime = Field(..., description="Timestamp when bid was submitted")
    is_valid: bool = Field(True, description="Whether the bid is valid")
    rfq_item_id: Optional[UUID] = Field(None, description="Optional RFQ line item UUID")
    supplier: Optional[SupplierResponse] = Field(None, description="Full supplier profile details if available")

    model_config = ConfigDict(from_attributes=True)


class RFQRankingResponse(BaseModel):
    rfq_id: UUID = Field(..., description="UUID of the RFQ")
    rfq_title: str = Field(..., description="Title of the RFQ")
    currency: str = Field("USD", description="Currency code of the RFQ")
    baseline_price: Optional[Decimal] = Field(None, description="Baseline/ceiling price of the RFQ")
    total_bids: int = Field(0, description="Total number of valid ranked bids")
    rankings: List[RankedBidItem] = Field(default_factory=list, description="Ordered list of ranked bids")

    model_config = ConfigDict(from_attributes=True)


