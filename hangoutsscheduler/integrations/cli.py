import asyncio
import logging
from typing import Callable

from sqlalchemy.orm import Session

from hangoutsscheduler.services.llm_service import LlmService
from hangoutsscheduler.services.user_context_service import UserContextService
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
from hangoutsscheduler.utils.logging.request_id_filter import RequestIdContextManager
from hangoutsscheduler.utils.validator import MessageValidator

logger = logging.getLogger(__name__)

class CliIntegration:
    """Runs the application in CLI."""
    def __init__(
        self,
        session_factory: Callable[[], Session],
        user_context_service: UserContextService,
        llm_service: LlmService,
        validator: MessageValidator,
        metrics_logger: MetricsLogger,
        request_id_context_manager: RequestIdContextManager,
        user_name: str
    ):
        self.session_factory = session_factory
        self.user_context_service = user_context_service
        self.llm_service = llm_service
        self.validator = validator
        self.metrics_logger = metrics_logger
        self.request_id_context_manager = request_id_context_manager
        self.user_name = user_name
    
    async def start(self):
        logger.info("Starting CLI Integration")

        while True:
            try:
                # Use asyncio.to_thread for blocking input() operation
                message = await asyncio.to_thread(input, "User: ")
                
                with self.session_factory() as session, self.metrics_logger, self.request_id_context_manager:
                    validated_message = self.validator.validate_message(message)
                    message_context = self.user_context_service.resolve_chat_history(session, self.user_name, validated_message)
                    response = await self.llm_service.respond_to_user_message(message_context, session)
                    self.user_context_service.update_with_llm_response(session, self.user_name, response.content)
                    print("Assistant: " + str(response.content))
            except Exception as e:
                logger.exception(f"Error in chat loop: {e}")
                print("An error occurred: " + str(e))
            except (asyncio.CancelledError, KeyboardInterrupt):
                logger.info("CLI Integration received shutdown signal")
                break

        logger.info("CLI Integration stopped")