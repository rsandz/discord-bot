from sqlalchemy import Integer, DateTime, String
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from discordbot.models.orm.base import Base


class Alarm(Base):
    """Represents an alarm that can trigger at a specific time."""
    
    __tablename__ = "alarm"

    alarm_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, init=False
    )
    trigger_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # User who created this alarm
    user_id: Mapped[str] = mapped_column(String(50), nullable=False) 

    # Channel source of the alarm
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False)
    

    def __str__(self) -> str:
        return f"Alarm {self.alarm_id}: {self.description} (Triggers at {self.trigger_time})" 