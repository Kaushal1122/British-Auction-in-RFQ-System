import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RFQSupplierStatus

if TYPE_CHECKING:
    from app.models.rfq import RFQ
    from app.models.supplier import Supplier


class RFQSupplier(Base):
    __tablename__ = "rfq_suppliers"
    __table_args__ = (
        UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_supplier"),
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
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[RFQSupplierStatus] = mapped_column(
        SAEnum(RFQSupplierStatus, name="rfq_supplier_status_enum", native_enum=False),
        default=RFQSupplierStatus.INVITED,
        nullable=False,
    )

    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="suppliers")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="rfq_associations")

    def __repr__(self) -> str:
        return f"<RFQSupplier(rfq_id={self.rfq_id}, supplier_id={self.supplier_id}, status='{self.status}')>"
