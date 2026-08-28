import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.rfq_supplier import RFQSupplier
    from app.models.quote import Quote
    from app.models.bid import Bid


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    rfq_associations: Mapped[List["RFQSupplier"]] = relationship(
        "RFQSupplier",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    quotes: Mapped[List["Quote"]] = relationship(
        "Quote",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', email='{self.email}')>"
