from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hangoutsscheduler.models.orm import Base

class Event(Base):
    """Represents a calendar event."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    title: Mapped[str] = mapped_column(index=True)
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarm.alarm_id"), init=False, nullable=True)

    alarm: Mapped["Alarm"] = relationship(default=None) # type: ignore
    attendees: Mapped[List["Attendee"]] = relationship(back_populates="event", default_factory=list) # type: ignore
