from sqlalchemy import Integer, DateTime, String
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Alarm(Base):
    __tablename__ = 'alarm'
    
    alarm_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    trigger_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

