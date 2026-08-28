from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.enums import RFQStatus, ExtensionTrigger, AuctionStatus
from app.schemas.buyer import BuyerResponse


class RFQItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Item name / part identifier")
    description: Optional[str] = Field(None, description="Detailed item specifications")
    quantity: Decimal = Field(..., gt=Decimal(0), description="Quantity required (must be > 0)")
    unit: str = Field("units", min_length=1, max_length=50, description="Unit of measurement (e.g., units, kg, sets)")

    @field_validator("name", "unit")
    @classmethod
    def check_not_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            return v_str if v_str else None
        return None


class RFQItemCreate(RFQItemBase):
    pass


class RFQItemResponse(RFQItemBase):
    id: UUID
    rfq_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuctionResponse(BaseModel):
    id: UUID
    rfq_id: UUID
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    bid_close_time: Optional[datetime] = None
    forced_bid_close_time: Optional[datetime] = None
    trigger_window_minutes: int = 10
    extension_duration_minutes: int = 5
    extension_trigger: ExtensionTrigger = ExtensionTrigger.BID_RECEIVED
    status: AuctionStatus = AuctionStatus.SCHEDULED
    current_round: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RFQBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="RFQ Title")
    description: Optional[str] = Field(None, description="Procurement description and guidelines")
    category: Optional[str] = Field(None, max_length=100, description="Procurement industry category")
    currency: str = Field("USD", min_length=3, max_length=3, description="3-character currency code")
    baseline_price: Decimal = Field(..., ge=Decimal(0), description="Budget baseline price (must be >= 0)")
    pickup_service_date: Optional[datetime] = Field(None, description="Expected pickup / service delivery date")

    # Auction Schedule & British Auction Extension Configuration
    bid_start_time: Optional[datetime] = Field(None, description="Bidding opening datetime")
    bid_close_time: Optional[datetime] = Field(None, description="Scheduled bidding close datetime")
    forced_bid_close_time: Optional[datetime] = Field(None, description="Forced bidding close datetime (hard cap)")
    trigger_window_minutes: Optional[int] = Field(10, gt=0, description="Trigger monitoring window in minutes before close (must be > 0)")
    extension_duration_minutes: Optional[int] = Field(5, gt=0, description="Duration in minutes added upon extension (must be > 0)")
    extension_trigger: Optional[ExtensionTrigger] = Field(ExtensionTrigger.BID_RECEIVED, description="British Auction extension trigger mode")

    @field_validator("title")
    @classmethod
    def check_title_not_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def check_currency_code(cls, v: str) -> str:
        if not v or not v.strip():
            return "USD"
        v_trimmed = v.strip()
        if len(v_trimmed) != 3 or not v_trimmed.isalpha() or not v_trimmed.isupper():
            raise ValueError("Currency must be a valid 3-letter uppercase alphabetic currency code (e.g., USD, EUR, GBP)")
        return v_trimmed

    @field_validator("description", "category")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            return v_str if v_str else None
        return None

    @field_validator("trigger_window_minutes")
    @classmethod
    def validate_trigger_window(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Trigger window must be greater than 0 minutes")
        return v

    @field_validator("extension_duration_minutes")
    @classmethod
    def validate_extension_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Extension duration must be greater than 0 minutes")
        return v

    @model_validator(mode="before")
    @classmethod
    def map_aliases_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Support alias keys
            if "bid_start_at" in data and "bid_start_time" not in data:
                data["bid_start_time"] = data["bid_start_at"]
            if "start_time" in data and "bid_start_time" not in data:
                data["bid_start_time"] = data["start_time"]

            if "bid_close_at" in data and "bid_close_time" not in data:
                data["bid_close_time"] = data["bid_close_at"]
            if "end_time" in data and "bid_close_time" not in data:
                data["bid_close_time"] = data["end_time"]

            if "forced_bid_close_at" in data and "forced_bid_close_time" not in data:
                data["forced_bid_close_time"] = data["forced_bid_close_at"]

            if "trigger_window" in data and "trigger_window_minutes" not in data:
                data["trigger_window_minutes"] = data["trigger_window"]

            if "extension_duration" in data and "extension_duration_minutes" not in data:
                data["extension_duration_minutes"] = data["extension_duration"]
        return data

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RFQCreate(RFQBase):
    buyer_id: UUID = Field(..., description="UUID of the creating Buyer")
    items: List[RFQItemCreate] = Field(..., min_length=1, description="List of items (minimum 1 item required)")

    @model_validator(mode="after")
    def validate_chronological_times(self) -> "RFQCreate":
        # 1. Validate Bid Start vs Bid Close
        if self.bid_start_time is not None and self.bid_close_time is not None:
            start_t = self.bid_start_time.replace(tzinfo=timezone.utc) if self.bid_start_time.tzinfo is None else self.bid_start_time
            close_t = self.bid_close_time.replace(tzinfo=timezone.utc) if self.bid_close_time.tzinfo is None else self.bid_close_time
            if close_t <= start_t:
                raise ValueError("Bid close time must be later than bid start time")

        # 2. Validate Bid Close vs Forced Bid Close (Critical Assignment Rule)
        if self.bid_close_time is not None and self.forced_bid_close_time is not None:
            close_t = self.bid_close_time.replace(tzinfo=timezone.utc) if self.bid_close_time.tzinfo is None else self.bid_close_time
            forced_t = self.forced_bid_close_time.replace(tzinfo=timezone.utc) if self.forced_bid_close_time.tzinfo is None else self.forced_bid_close_time
            if forced_t <= close_t:
                raise ValueError("Forced close time must be later than bid close time")

        # 3. Validate Bid Start vs Forced Bid Close
        if self.bid_start_time is not None and self.forced_bid_close_time is not None:
            start_t = self.bid_start_time.replace(tzinfo=timezone.utc) if self.bid_start_time.tzinfo is None else self.bid_start_time
            forced_t = self.forced_bid_close_time.replace(tzinfo=timezone.utc) if self.forced_bid_close_time.tzinfo is None else self.forced_bid_close_time
            if forced_t <= start_t:
                raise ValueError("Forced close time must be later than bid start time")

        return self



class RFQListItemResponse(RFQBase):
    id: UUID
    buyer_id: UUID
    status: RFQStatus
    items_count: int = Field(0, description="Count of items included in this RFQ")
    created_at: datetime
    updated_at: datetime
    auction: Optional[AuctionResponse] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RFQDetailResponse(RFQBase):
    id: UUID
    buyer_id: UUID
    status: RFQStatus
    created_at: datetime
    updated_at: datetime
    buyer: Optional[BuyerResponse] = None
    items: List[RFQItemResponse] = Field(default_factory=list)
    auction: Optional[AuctionResponse] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

