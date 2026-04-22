from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Talk(Base):
    __tablename__ = "talks"

    talk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("slots.slot_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    slot: Mapped["Slot"] = relationship(back_populates="talks")  # noqa: F821
