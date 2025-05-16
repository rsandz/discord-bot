from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from discordbot.services.alarm.orm import Alarm
from discordbot.utils.logging.metrics import MetricsLogger

import logging

logger = logging.getLogger(__name__)

# Constants
ISO_FORMAT = "YYYY-MM-DDTHH:MM:SS±HH:MM"


class CreateAlarmInput(BaseModel):
    trigger_time: str = Field(
        ..., description=f"When the alarm should trigger in ISO format {ISO_FORMAT}"
    )
    description: str = Field(
        ...,
        description="""
            Description/instructions for the alarm. 
            You should describe what the alarm is for and what should be done when the alarm is triggered.
            Example output:
                AlarmDescription: This alarm is to notify the the user, Bob, about his birthday on 2025-05-11 at 12:00.
                Action: When the alarm is triggered, I should notify Bob about his birthday.
        """,
    )
    user_id: str = Field(
        ...,
        description="""
            ID of the user who created the alarm. 
            This is used to identify which user the alarm is created for.
        """,
    )
    channel_id: str = Field(
        ...,
        description="""
            ID of the channel where the alarm was created.
            This is used to identify which channel the alarm is created from.
        """,
    )


class UpdateAlarmInput(BaseModel):
    alarm_id: int = Field(..., description="ID of the alarm to update")
    trigger_time: Optional[str] = Field(
        None, description=f"New trigger time in ISO format {ISO_FORMAT}"
    )
    description: Optional[str] = Field(None, description="New description")


class DeleteAlarmInput(BaseModel):
    alarm_id: int = Field(..., description="ID of the alarm to delete")


class ListAlarmsInput(BaseModel):
    user_id: str = Field(..., description="ID of the user to list alarms for")
    include_past: bool = Field(
        default=True, description="Whether to include past alarms in the list"
    )


class AlarmToolAdapter:
    """Adapter for LLM to interact with alarms."""

    def __init__(self, alarm_service):
        self.alarm_service = alarm_service

    def create_alarm(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        trigger_time: str,
        description: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.create_alarm"):
            return self.alarm_service.create_alarm(session, trigger_time, description, user_id, channel_id)

    def list_alarms(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        user_id: str,
        include_past: bool = False,
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.list_alarms"):
            return self.alarm_service.list_alarms(session, user_id, include_past)

    def update_alarm(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        alarm_id: int,
        trigger_time: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.update_alarm"):
            return self.alarm_service.update_alarm(session, alarm_id, trigger_time, description)

    def delete_alarm(
        self, session: Session, metrics_logger: MetricsLogger, alarm_id: int
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.delete_alarm"):
            return self.alarm_service.delete_alarm(session, alarm_id)