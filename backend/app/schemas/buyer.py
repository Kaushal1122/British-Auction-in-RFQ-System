from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class BuyerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Buyer name")
    email: EmailStr = Field(..., description="Unique email address")
    company_name: Optional[str] = Field(None, max_length=255, description="Company or organization name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Email cannot be empty or whitespace only")
        return v.strip().lower()

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            return v_str if v_str else None
        return None


class BuyerCreate(BuyerBase):
    pass


class BuyerResponse(BuyerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
