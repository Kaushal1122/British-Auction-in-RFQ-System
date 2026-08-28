from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActorType, EventType


class ActivityLogResponse(BaseModel):
    id: UUID
    rfq_id: Optional[UUID] = None
    auction_id: Optional[UUID] = None
    actor_type: ActorType
    actor_id: Optional[UUID] = None
    event_type: EventType
    message: str
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
