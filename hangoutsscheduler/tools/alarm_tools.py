from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from hangoutsscheduler.models.orm.alarm import Alarm
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
import logging

logger = logging.getLogger(__name__)

class CreateAlarmInput(BaseModel):
    trigger_time: str = Field(..., description="When the alarm should trigger ISO format (YYYY-MM-DDTHH:MM:SS)")
    description: str = Field(..., description="Description/instructions for the alarm. It should be actionable by you when the alarm triggers.")

class UpdateAlarmInput(BaseModel):
    alarm_id: int = Field(..., description="ID of the alarm to update")
    trigger_time: Optional[str] = Field(None, description="New trigger time ISO format (YYYY-MM-DDTHH:MM:SS)")
    description: Optional[str] = Field(None, description="New description")

class DeleteAlarmInput(BaseModel):
    alarm_id: int = Field(..., description="ID of the alarm to delete")

class ListAlarmsInput(BaseModel):
    include_past: bool = Field(default=False, description="Whether to include past alarms")

class AlarmTools:
    def create_alarm(self, session: Session, metrics_logger: MetricsLogger, trigger_time: str, description: str) -> str:
        with metrics_logger.instrumenter("AlarmTools.create_alarm"):
            try:
                alarm_time = datetime.fromisoformat(trigger_time)
                alarm = Alarm(trigger_time=alarm_time, description=description)  
                session.add(alarm)
                logger.info(f"Created alarm ID {alarm.alarm_id}")
                return f"Alarm created with ID {alarm.alarm_id}"
            except ValueError as e:
                logger.error(f"Failed to parse trigger time: {e}")
                return f"Failed to create alarm: Invalid time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"

    def list_alarms(self, session: Session, metrics_logger: MetricsLogger, include_past: bool = False) -> str:
        with metrics_logger.instrumenter("AlarmTools.list_alarms"):
            query = session.query(Alarm)
            if not include_past:
                query = query.filter(Alarm.trigger_time > datetime.now())
            alarms = query.order_by(Alarm.trigger_time).all()
            
            if not alarms:
                return "No alarms found"
                
            logger.info(f"Listed {len(alarms)} alarms")
            return "\n".join(str(alarm) for alarm in alarms)

    def update_alarm(self, session: Session, metrics_logger: MetricsLogger,
                    alarm_id: int, trigger_time: Optional[str] = None,
                    description: Optional[str] = None) -> str:
        with metrics_logger.instrumenter("AlarmTools.update_alarm"):
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
                return f"Failed to update alarm: Invalid time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"

    def delete_alarm(self, session: Session, metrics_logger: MetricsLogger, alarm_id: int) -> str:
        with metrics_logger.instrumenter("AlarmTools.delete_alarm"):
            alarm = session.get(Alarm, alarm_id)
            if not alarm:
                logger.warning(f"Attempted to delete non-existent alarm {alarm_id}")
                return f"Alarm {alarm_id} not found"
            
            session.delete(alarm)
            logger.info(f"Deleted alarm ID {alarm_id}")
            return f"Alarm {alarm_id} deleted successfully"
