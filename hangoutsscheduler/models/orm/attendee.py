from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hangoutsscheduler.models.orm import Base


class Attendee(Base):
    """Represents a user that is attending an event."""

    __tablename__ = "attendee"

    username: Mapped[str] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"), primary_key=True, init=False
    )

    event: Mapped["Event"] = relationship(back_populates="attendees", default=None) # type: ignore
