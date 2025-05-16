from datetime import datetime
import logging
import asyncio
from typing import Callable
from sqlalchemy.orm import Session
from discordbot.models.event import SystemMessageEvent
from discordbot.models.event_context import EventContext
from discordbot.models.message import TimeStampedHumanMessage
from discordbot.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

async def alarm_event_processor(
    event_queue: asyncio.Queue[EventContext],
    orchestrator: Orchestrator,
    session_factory: Callable[[], Session],
) -> None:
    """
    Continuously process events from the alarm event queue and invoke the LLM for each event.
    """
    logger.info("Alarm event processor started")
    while True:
        event_context = await event_queue.get()
        logger.info(f"Processing event from queue: {event_context}")
        try:
            with session_factory() as session:
                system_event = SystemMessageEvent(
                    event_description="Alarm event triggered at a specified time.",
                    message=TimeStampedHumanMessage(content=event_context.event_description, timestamp=datetime.now()),
                    event_source="AlarmService",
                    additional_data={"alarm_id": event_context.additional_data['alarm_id']},
                )
                response = await orchestrator.handle_system_event(system_event)
                logger.info(f"LLM responded to event id {event_context.additional_data['alarm_id']} with response {response.ai_message.content}")
        except Exception as e:
            logger.exception(f"Error processing event from queue: {e}")
