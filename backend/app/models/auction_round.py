import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AuctionRoundStatus

if TYPE_CHECKING:
    from app.models.auction import Auction
    from app.models.bid import Bid


class AuctionRound(Base):
    __tablename__ = "auction_rounds"
    __table_args__ = (
        UniqueConstraint("auction_id", "round_number", name="uq_auction_round_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[AuctionRoundStatus] = mapped_column(
        SAEnum(AuctionRoundStatus, name="auction_round_status_enum", native_enum=False),
        default=AuctionRoundStatus.PENDING,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    auction: Mapped["Auction"] = relationship("Auction", back_populates="rounds")
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="round",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AuctionRound(id={self.id}, auction_id={self.auction_id}, round_number={self.round_number}, status='{self.status}')>"
