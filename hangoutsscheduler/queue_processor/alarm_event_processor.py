import logging
import asyncio
from typing import Callable
from sqlalchemy.orm import Session
from hangoutsscheduler.models.event_context import EventContext
from hangoutsscheduler.services.llm_service import LlmService

logger = logging.getLogger(__name__)

async def alarm_event_processor(
    event_queue: asyncio.Queue[EventContext],
    llm_service: LlmService,
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
                response = await llm_service.respond_to_system_event(event_context, session)
                logger.info(f"LLM responded to event id {event_context.additional_data['alarm_id']} with response {response.content}")
        except Exception as e:
            logger.exception(f"Error processing event from queue: {e}")
