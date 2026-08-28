import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auction import Auction
    from app.models.auction_round import AuctionRound
    from app.models.supplier import Supplier


class Bid(Base):
    __tablename__ = "bids"
    __allow_unmapped__ = True
    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_bid_amount_positive"),
        UniqueConstraint("auction_id", "supplier_id", name="uq_bid_auction_supplier"),
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
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auction_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Quote breakdown details from PDF specification
    carrier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    freight_charges: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    origin_charges: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    destination_charges: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    transit_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    validity_of_quote: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Transient helper fields for response serialization
    rfq_id: Optional[uuid.UUID] = None
    auction_end_time: Optional[datetime] = None
    auction_extended: Optional[bool] = None
    extension_reason: Optional[str] = None

    # Relationships
    auction: Mapped["Auction"] = relationship("Auction", back_populates="bids")
    round: Mapped["AuctionRound"] = relationship("AuctionRound", back_populates="bids")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="bids")

    def __repr__(self) -> str:
        return f"<Bid(id={self.id}, auction_id={self.auction_id}, supplier_id={self.supplier_id}, amount={self.amount})>"
