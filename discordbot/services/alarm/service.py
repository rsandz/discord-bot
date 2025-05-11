import logging
from datetime import datetime, timedelta, timezone
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import select

from discordbot.models.event_context import EventContext
from discordbot.services.alarm.orm import Alarm
from discordbot.utils.logging.metrics import MetricsLogger

logger = logging.getLogger(__name__)

# Constants
CHECK_INTERVAL = 60  # Check every minute


class AlarmService:
    """Service for managing and processing alarms."""

    def create_alarm(self, session: Session, trigger_time: str, description: str, user_id: str, channel_id: str) -> str:
        """
        Create a new alarm. All datetime objects are timezone-aware UTC.
        """
        try:
            logger.info(f"Creating alarm for {user_id} at {trigger_time}")
            alarm_time = datetime.fromisoformat(trigger_time)
            if alarm_time.tzinfo is None:
                alarm_time = alarm_time.replace(tzinfo=timezone.utc)
            else:
                alarm_time = alarm_time.astimezone(timezone.utc)
            alarm = Alarm(trigger_time=alarm_time, description=description, user_id=user_id, channel_id=channel_id)
            session.add(alarm)
            logger.info(f"Created Alarm with trigger time {alarm_time}")
            return f"Alarm created with trigger time {alarm_time}"
        except ValueError as e:
            error_msg = f"Failed to parse trigger time: {e}"
            logger.error(error_msg)
            return f"Failed to create alarm: {error_msg}"

    def list_alarms(self, session: Session, user_id: str, include_past: bool = False) -> str:
        """
        List alarms for a user. Only future alarms unless include_past is True. Uses UTC-aware datetime.
        """
        from datetime import datetime, timezone
        query = session.query(Alarm).filter(Alarm.user_id == user_id)
        now = datetime.now(timezone.utc)
        if not include_past:
            query = query.filter(Alarm.trigger_time > now)
        alarms = query.order_by(Alarm.trigger_time).all()
        if not alarms:
            return "No alarms found"
        logger.info(f"Listed {len(alarms)} alarms for user {user_id}")
        return "\n".join(str(alarm) for alarm in alarms)

    def update_alarm(self, session: Session, alarm_id: int, trigger_time: str | None = None, description: str | None = None) -> str:
        """
        Update an alarm. All datetime objects are timezone-aware UTC.
        """
        from datetime import datetime, timezone
        alarm = session.get(Alarm, alarm_id)
        if not alarm:
            logger.warning(f"Attempted to update non-existent alarm {alarm_id}")
            return f"Alarm {alarm_id} not found"
        try:
            if trigger_time:
                alarm_time = datetime.fromisoformat(trigger_time)
                if alarm_time.tzinfo is None:
                    alarm_time = alarm_time.replace(tzinfo=timezone.utc)
                else:
                    alarm_time = alarm_time.astimezone(timezone.utc)
                alarm.trigger_time = alarm_time
            if description:
                alarm.description = description
            logger.info(f"Updated alarm ID {alarm_id}")
            return f"Alarm {alarm_id} updated successfully"
        except ValueError as e:
            error_msg = f"Failed to update alarm: {e}"
            logger.error(error_msg)
            return f"Failed to update alarm: {error_msg}"

    def delete_alarm(self, session: Session, alarm_id: int) -> str:
        """
        Delete an alarm by ID.
        """
        alarm = session.get(Alarm, alarm_id)
        if not alarm:
            logger.warning(f"Attempted to delete non-existent alarm {alarm_id}")
            return f"Alarm {alarm_id} not found"
        session.delete(alarm)
        logger.info(f"Deleted alarm ID {alarm_id}")
        return f"Alarm {alarm_id} deleted successfully"

    def __init__(
        self, session_factory, metrics_logger: MetricsLogger
    ):
        self.session_factory = session_factory
        self.metrics_logger = metrics_logger
        self.check_interval = CHECK_INTERVAL
        self.event_queue = asyncio.Queue()

    async def start(self):
        """Start the alarm checking loop"""
        logger.info("Starting alarm service")
        try:
            while True:
                try:
                    with self.session_factory() as session:
                        await self.delete_old_alarms(session)
                        await self.check_alarms(session)
                        session.commit()
                    next_check_time = datetime.now() + timedelta(
                        seconds=self.check_interval
                    )
                    logger.info(
                        f"Checked alarms - next check time is at {next_check_time}"
                    )
                except Exception as e:
                    error_msg = f"Error checking alarms: {e}"
                    logger.exception(error_msg)
                try:
                    await asyncio.sleep(self.check_interval)
                except asyncio.CancelledError:
                    logger.info("Alarm service received shutdown signal")
                    break
        except asyncio.CancelledError:
            logger.info("Alarm service shutting down...")
        finally:
            logger.info("Alarm service stopped")

    async def delete_old_alarms(self, session):
        """Delete all alarms that have a trigger time older than the check interval"""
        stmt = select(Alarm).where(
            Alarm.trigger_time < datetime.now() - timedelta(seconds=self.check_interval)
        )
        alarms_to_delete = session.execute(stmt).scalars().all()

        # Delete each alarm
        for alarm in alarms_to_delete:
            session.delete(alarm)
            logger.info(f"Deleted alarm ID {alarm.alarm_id}")

    async def check_alarms(self, session: Session):
        """Check for and process any active alarms"""
        now = datetime.now()
        check_from = now - timedelta(seconds=self.check_interval)

        stmt = select(Alarm).where(
            Alarm.trigger_time <= now, Alarm.trigger_time > check_from
        )

        active_alarms = session.execute(stmt).scalars().all()

        for alarm in active_alarms:
            await self.process_alarm(session, alarm)

    async def process_alarm(self, session: Session, alarm: Alarm):
        """Process a triggered alarm by sending it to the LLM"""
        logger.info(f"Processing alarm {alarm.alarm_id}")

        with self.metrics_logger.instrumenter("AlarmService.process_alarm"):
            try:
                # Create a message context for the LLM
                event_context = EventContext(
                    event_source="AlarmService",
                    event_description=f"Processing alarm with description: {alarm.description}",
                    additional_data={"alarm_id": alarm.alarm_id},
                )

                self.event_queue.put_nowait(event_context)
                logger.info(f"Alarm {alarm.alarm_id} processed and added to queue")

                session.delete(alarm)

            except Exception as e:
                error_msg = f"Error processing alarm {alarm.alarm_id}: {e}"
                logger.exception(error_msg) 