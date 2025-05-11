import logging
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import select

from hangoutsscheduler.models.event_context import EventContext
from hangoutsscheduler.services.alarm.orm import Alarm
from hangoutsscheduler.utils.logging.metrics import MetricsLogger

logger = logging.getLogger(__name__)

# Constants
CHECK_INTERVAL = 60  # Check every minute


class AlarmService:
    """Service for managing and processing alarms."""

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
                    logger.exception(f"Error checking alarms: {e}")
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
                logger.exception(f"Error processing alarm {alarm.alarm_id}: {e}") 