import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AuctionStatus, ExtensionTrigger

if TYPE_CHECKING:
    from app.models.rfq import RFQ
    from app.models.auction_round import AuctionRound
    from app.models.bid import Bid
    from app.models.activity_log import ActivityLog


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    forced_bid_close_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    trigger_window_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        server_default="10",
        nullable=False,
    )
    extension_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        nullable=False,
    )
    extension_trigger: Mapped[ExtensionTrigger] = mapped_column(
        SAEnum(ExtensionTrigger, name="extension_trigger_enum", native_enum=False),
        default=ExtensionTrigger.BID_RECEIVED,
        server_default=ExtensionTrigger.BID_RECEIVED.value,
        nullable=False,
    )
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AuctionStatus] = mapped_column(
        SAEnum(AuctionStatus, name="auction_status_enum", native_enum=False),
        default=AuctionStatus.SCHEDULED,
        nullable=False,
        index=True,
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
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="auction")
    rounds: Mapped[List["AuctionRound"]] = relationship(
        "AuctionRound",
        back_populates="auction",
        cascade="all, delete-orphan",
        order_by="AuctionRound.round_number",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="auction",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="auction",
        cascade="all, delete-orphan",
    )

    @property
    def bid_close_time(self) -> Optional[datetime]:
        """Alias for end_time."""
        return self.end_time

    @bid_close_time.setter
    def bid_close_time(self, value: Optional[datetime]):
        self.end_time = value

    @property
    def trigger_window(self) -> int:
        """Alias for trigger_window_minutes."""
        return self.trigger_window_minutes

    @trigger_window.setter
    def trigger_window(self, value: int):
        self.trigger_window_minutes = value

    @property
    def extension_duration(self) -> int:
        """Alias for extension_duration_minutes."""
        return self.extension_duration_minutes

    @extension_duration.setter
    def extension_duration(self, value: int):
        self.extension_duration_minutes = value

    def __repr__(self) -> str:
        return f"<Auction(id={self.id}, rfq_id={self.rfq_id}, status='{self.status}', current_round={self.current_round})>"
