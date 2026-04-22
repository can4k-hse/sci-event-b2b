from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSlotSelection(Base):
    __tablename__ = "user_slot_selections"
    __table_args__ = (
        UniqueConstraint("user_id", "slot_id", name="uq_user_slot_selection"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("slots.slot_id", ondelete="CASCADE"), nullable=False
    )
    talk_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("talks.talk_id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
