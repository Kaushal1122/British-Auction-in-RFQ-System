import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, DateTime, Enum as SAEnum, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RFQStatus

if TYPE_CHECKING:
    from app.models.buyer import Buyer
    from app.models.rfq_item import RFQItem
    from app.models.rfq_supplier import RFQSupplier
    from app.models.quote import Quote
    from app.models.auction import Auction
    from app.models.activity_log import ActivityLog


class RFQ(Base):
    __tablename__ = "rfqs"
    __table_args__ = (
        CheckConstraint("baseline_price >= 0", name="check_rfq_baseline_price_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    baseline_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[RFQStatus] = mapped_column(
        SAEnum(RFQStatus, name="rfq_status_enum", native_enum=False),
        default=RFQStatus.DRAFT,
        nullable=False,
        index=True,
    )
    pickup_service_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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
    buyer: Mapped["Buyer"] = relationship("Buyer", back_populates="rfqs")
    items: Mapped[List["RFQItem"]] = relationship(
        "RFQItem",
        back_populates="rfq",
        cascade="all, delete-orphan",
    )
    suppliers: Mapped[List["RFQSupplier"]] = relationship(
        "RFQSupplier",
        back_populates="rfq",
        cascade="all, delete-orphan",
    )
    quotes: Mapped[List["Quote"]] = relationship(
        "Quote",
        back_populates="rfq",
        cascade="all, delete-orphan",
    )
    auction: Mapped[Optional["Auction"]] = relationship(
        "Auction",
        back_populates="rfq",
        uselist=False,
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="rfq",
        cascade="all, delete-orphan",
    )

    @property
    def items_count(self) -> int:
        """Helper property to return the number of items in this RFQ."""
        return len(self.items) if self.items is not None else 0

    @property
    def bid_start_time(self) -> Optional[datetime]:
        """Helper property to return the auction start time."""
        return self.auction.start_time if self.auction is not None else None

    @property
    def bid_close_time(self) -> Optional[datetime]:
        """Helper property to return the auction end/close time."""
        return self.auction.end_time if self.auction is not None else None

    @property
    def forced_bid_close_time(self) -> Optional[datetime]:
        """Helper property to return the auction forced bid close time."""
        return self.auction.forced_bid_close_time if self.auction is not None else None

    @property
    def trigger_window_minutes(self) -> int:
        """Helper property to return the trigger window in minutes."""
        return self.auction.trigger_window_minutes if self.auction is not None else 10

    @property
    def extension_duration_minutes(self) -> int:
        """Helper property to return the extension duration in minutes."""
        return self.auction.extension_duration_minutes if self.auction is not None else 5

    @property
    def extension_trigger(self) -> Optional[object]:
        """Helper property to return the extension trigger enum."""
        return self.auction.extension_trigger if self.auction is not None else None

    def __repr__(self) -> str:
        return f"<RFQ(id={self.id}, title='{self.title}', status='{self.status}')>"

