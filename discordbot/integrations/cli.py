import asyncio
from datetime import datetime
import logging
from typing import Callable
import uuid

from sqlalchemy.orm import Session

from discordbot.models.event import UserMessageEvent
from discordbot.models.message import TimeStampedHumanMessage
from discordbot.utils.logging.metrics import MetricsLogger
from discordbot.utils.logging.request_id_filter import RequestIdContextManager
from discordbot.utils.validator import MessageValidator
from discordbot.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class CliIntegration:
    """Runs the application in CLI."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        validator: MessageValidator,
        metrics_logger: MetricsLogger,
        request_id_context_manager: RequestIdContextManager,
        user_name: str,
        orchestrator: Orchestrator,
    ):
        self.session_factory = session_factory
        self.validator = validator
        self.metrics_logger = metrics_logger
        self.request_id_context_manager = request_id_context_manager
        self.user_name = user_name
        self.orchestrator = orchestrator

    async def start(self):
        logger.info("Starting CLI Integration")
        history = []

        while True:
            try:
                # Use asyncio.to_thread for blocking input() operation
                message = await asyncio.to_thread(input, "User: ")

                with (
                    self.session_factory() as session,
                    self.metrics_logger,
                    self.request_id_context_manager,
                ):
                    validated_message = self.validator.validate_message(message)

                    human_message = TimeStampedHumanMessage(
                            content=validated_message,
                            timestamp=datetime.now(),
                            id=str(uuid.uuid4())
                        )
                
                    user_event = UserMessageEvent(
                        event_description="User CLI Message",
                        user_id=self.user_name,
                        user_name=self.user_name,
                        channel_id="CLI",
                        immediate_history=history,
                        message=human_message,
                    )

                    event_response = await self.orchestrator.handle_user_event(user_event)

                    print("Assistant: " + str(event_response.ai_message.content))

                    history.append(human_message)
                    history.append(event_response.ai_message)

            except Exception as e:
                logger.exception(f"Error in chat loop: {e}")
                print("An error occurred: " + str(e))
            except (asyncio.CancelledError, KeyboardInterrupt):
                logger.info("CLI Integration received shutdown signal")
                break

        logger.info("CLI Integration stopped")
