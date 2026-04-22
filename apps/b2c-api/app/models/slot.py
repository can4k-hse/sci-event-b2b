from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Slot(Base):
    __tablename__ = "slots"

    slot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False, index=True
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    event: Mapped["Event"] = relationship(back_populates="slots")  # noqa: F821
    talks: Mapped[list["Talk"]] = relationship(  # noqa: F821
        back_populates="slot", cascade="all, delete-orphan"
    )
