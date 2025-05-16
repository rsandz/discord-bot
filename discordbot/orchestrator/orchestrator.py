from typing import Callable, Sequence
from sqlalchemy.orm import Session
from discordbot.models.event import SystemMessageEvent, UserMessageEvent
from discordbot.models.message import TimeStampedMessage
from discordbot.models.response import EventResponse
from discordbot.services.llm_service import LlmService
from discordbot.services.llm_service.models.invocation_request import LlmInvocationRequest, SystemEventLlmInvocationRequest
from discordbot.services.user_context.models.user_context import UserContext
from discordbot.services.user_context.user_context_service import UserContextService
from contextlib import AsyncExitStack
from discordbot.config import Config
from langchain_core.messages import SystemMessage
import logging
from itertools import chain
from discordbot.tools.tool_provider import ToolProvider
from discordbot.utils.logging.metrics import MetricsLogger
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Orchestrator:
    """Orchestrator that handles events and invokes the LLM."""

    def __init__(self, session_factory: Callable[[], Session], llm_service: LlmService, user_context_service: UserContextService, tool_provider: ToolProvider, metrics_logger: MetricsLogger, config: Config):
        self.session_factory = session_factory
        self.llm_service = llm_service
        self.user_context_service = user_context_service
        self.tool_provider = tool_provider
        self.metrics_logger = metrics_logger
        self.config = config

        self.user_event_system_prompt = SystemMessage(content=config.user_message_base)

    async def handle_user_event(self, event: UserMessageEvent) -> EventResponse:
        with self.metrics_logger.instrumenter(__name__ + ".handle_user_event"):
            async with AsyncExitStack() as exit_stack:
                logger.info(f"Handling user event: {event}")
                session = exit_stack.enter_context(self.session_factory())

                user_context = self.user_context_service.resolve_user_context(session, event.user_id)

                if user_context is None:
                    user_context = self.user_context_service.create_user_context(session, event.user_id, event.user_name)

                merged_message_history = self.merge_chat_history(event.immediate_history, user_context.user_chat_history)
                user_context_system_prompt = self.generate_system_prompt_from_user_context(user_context, event.channel_id)

                llm_request = LlmInvocationRequest(
                    system_messages=[
                        self.user_event_system_prompt, 
                        user_context_system_prompt,
                        SystemMessage(content="The current UTC time is " + datetime.now(timezone.utc).isoformat()),
                        ],
                    chat_history=merged_message_history,
                    primary_message=event.message,
                    tools=await self.tool_provider.get_tools(session, self.metrics_logger, exit_stack),
                )

                response = await self.llm_service.invoke_llm(llm_request)

                self.user_context_service.append_message_to_user_context(session, event.user_id, event.message)
                self.user_context_service.append_message_to_user_context(session, event.user_id, response)
                session.commit()

                return EventResponse(
                    ai_message=response
                )

            raise ValueError("Failed to handle user event")

    async def handle_system_event(self, event: SystemMessageEvent) -> EventResponse:
        with self.metrics_logger.instrumenter(__name__ + ".handle_system_event"):
            async with AsyncExitStack() as exit_stack:
                logger.info(f"Handling system event: {event}")
                session = exit_stack.enter_context(self.session_factory())

                system_event_llm_request = SystemEventLlmInvocationRequest(
                    system_messages=[],
                    chat_history=[],
                    primary_message=event.message,
                    tools=await self.tool_provider.get_tools(session, self.metrics_logger, exit_stack),
                    event_context=event
                )

                response = await self.llm_service.invoke_llm(system_event_llm_request)

                return EventResponse(
                    ai_message=response
                )

            raise ValueError("Failed to handle system event")

    def generate_system_prompt_from_user_context(self, user_context: UserContext, channel_id: str) -> SystemMessage:
        return SystemMessage(content=f"You are talking username {user_context.user_name} and ID {user_context.user_id} in channel {channel_id}")

    def merge_chat_history(self, *histories: Sequence[TimeStampedMessage]) -> Sequence[TimeStampedMessage]:
        unique_messages: dict[str, TimeStampedMessage] = {}

        for message in chain(*histories):
            if message.id is not None and message.id not in unique_messages:
                unique_messages[message.id] = message
            elif message.id is None:
                raise ValueError(f"Message ID for message {message} is None")
            else:
                logger.debug(
                    f"Deduplicate message ID: {message.id}, content: {message.content}"
                )

        return list(unique_messages.values())
