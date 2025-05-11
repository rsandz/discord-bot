from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from hangoutsscheduler.services.alarm.orm import Alarm
from hangoutsscheduler.utils.logging.metrics import MetricsLogger

import logging

logger = logging.getLogger(__name__)

# Constants
ISO_FORMAT = "yyyy-MM-ddTHH:mm:ss±hh:mm (or Z for UTC)"


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
    include_past: bool = Field(
        default=False, description="Whether to include past alarms in the list"
    )


class AlarmToolAdapter:
    """Adapter for LLM to interact with alarms."""

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
            try:
                alarm_time = datetime.fromisoformat(trigger_time)
                alarm = Alarm(trigger_time=alarm_time, description=description, user_id=user_id, channel_id=channel_id)
                session.add(alarm)
                logger.info(f"Created alarm ID {alarm.alarm_id}")
                return f"Alarm created with ID {alarm.alarm_id}"
            except ValueError as e:
                logger.error(f"Failed to parse trigger time: {e}")
                return f"Failed to create alarm: Invalid time format. Use ISO format {ISO_FORMAT}"

    def list_alarms(
        self,
        session: Session,
        user_id: str,
        metrics_logger: MetricsLogger,
        include_past: bool = False,
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.list_alarms"):
            query = session.query(Alarm).filter(Alarm.user_id == user_id)
            if not include_past:
                query = query.filter(Alarm.trigger_time > datetime.now())
            alarms = query.order_by(Alarm.trigger_time).all()

            if not alarms:
                return "No alarms found"

            logger.info(f"Listed {len(alarms)} alarms")
            return "\n".join(str(alarm) for alarm in alarms)

    def update_alarm(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        alarm_id: int,
        trigger_time: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.update_alarm"):
            alarm = session.get(Alarm, alarm_id)
            if not alarm:
                logger.warning(f"Attempted to update non-existent alarm {alarm_id}")
                return f"Alarm {alarm_id} not found"

            try:
                if trigger_time:
                    alarm.trigger_time = datetime.fromisoformat(trigger_time)
                if description:
                    alarm.description = description

                logger.info(f"Updated alarm ID {alarm_id}")
                return f"Alarm {alarm_id} updated successfully"
            except ValueError as e:
                logger.error(f"Failed to update alarm: {e}")
                return f"Failed to update alarm: Invalid time format. Use ISO format {ISO_FORMAT}"

    def delete_alarm(
        self, session: Session, metrics_logger: MetricsLogger, alarm_id: int
    ) -> str:
        with metrics_logger.instrumenter("AlarmToolAdapter.delete_alarm"):
            alarm = session.get(Alarm, alarm_id)
            if not alarm:
                logger.warning(f"Attempted to delete non-existent alarm {alarm_id}")
                return f"Alarm {alarm_id} not found"

            session.delete(alarm)
            logger.info(f"Deleted alarm ID {alarm_id}")
            return f"Alarm {alarm_id} deleted successfully" 