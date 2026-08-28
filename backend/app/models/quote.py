import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, DateTime, Enum as SAEnum, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuoteStatus

if TYPE_CHECKING:
    from app.models.rfq import RFQ
    from app.models.supplier import Supplier


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_quote_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
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
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        SAEnum(QuoteStatus, name="quote_status_enum", native_enum=False),
        default=QuoteStatus.SUBMITTED,
        nullable=False,
    )

    submitted_at: Mapped[datetime] = mapped_column(
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
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="quotes")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="quotes")

    def __repr__(self) -> str:
        return f"<Quote(id={self.id}, rfq_id={self.rfq_id}, supplier_id={self.supplier_id}, amount={self.amount})>"
