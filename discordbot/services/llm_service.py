from contextlib import AsyncExitStack
import logging
from datetime import datetime
import datetime as dt
from typing import Any, Callable, List, Sequence
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticToolsParser
from langgraph.prebuilt import create_react_agent

from sqlalchemy.orm import Session

from discordbot.constants import USER_MESSAGE_TYPE, AI_MESSAGE_TYPE
from discordbot.models.event_context import EventContext
from discordbot.models.message_context import ChatMessage, MessageContext
from discordbot.utils.logging.metrics import Instrumenter, MetricsLogger
from discordbot.tools.tool_provider import ToolProvider

logger = logging.getLogger(__name__)

MAX_AGENT_RECURSION_DEPTH = 16

SYSTEM_EVENT_PROMPT = "You are a helpful assistant that's responding to a system event. Outputs of this invocation aren't directly outputted to the user. If the intention isn't clear, you can just do nothing."

UserPromptTransformer = Callable[[list[BaseMessage]], list[BaseMessage]]


class LlmService:

    def __init__(
        self,
        model: BaseChatModel,
        tool_provider: ToolProvider,
        metrics_logger: MetricsLogger,
        user_message_base_prompt: str,
        user_prompts_transformer: Sequence[UserPromptTransformer] = [],
    ):
        self.model: BaseChatModel = model
        self.user_message_base_prompt = SystemMessage(user_message_base_prompt)
        self.tool_provider = tool_provider
        self.metrics_logger = metrics_logger
        self.user_prompts_transformer: Sequence[UserPromptTransformer] = []

    def respond_to_system_event(self, event_context: EventContext, session: Session):
        with self.metrics_logger.instrumenter(
            "LLMService.respond_to_system_message"
        ) as instrumenter:
            logger.info(f"Responding to system message: {event_context}")

            prompt = [
                SystemMessage(SYSTEM_EVENT_PROMPT),
                SystemMessage(
                    f"Current Time: {datetime.now().astimezone().isoformat()}"
                ),
                SystemMessage(
                    f"Event Source: {event_context.event_source}, Event Description: {event_context.event_description}, Additional Data: {event_context.additional_data}"
                ),
            ]

            tools = self.tool_provider.get_system_tools(session, self.metrics_logger)
            last_message = self._invoke_llm(instrumenter, session, prompt, tools)
            return last_message

    async def respond_to_user_message(
        self,
        message_context: MessageContext,
        session: Session,
        additional_transformers: Sequence[UserPromptTransformer] = [],
    ) -> AIMessage:
        with self.metrics_logger.instrumenter(
            "LLMService.respond_to_message"
        ) as instrumenter:
            message = message_context.message
            logger.info(f"Responding to message: {message}")

            prompt: Sequence[BaseMessage] = [
                SystemMessage(f"Current User ID: {message_context.username}"),
                SystemMessage(
                    f"Current Time: {datetime.now().astimezone().isoformat()}"
                ),
                self.user_message_base_prompt,
                *self.encode_context_histories(message_context),
                HumanMessage(message),
            ]

            for transformer in (
                *self.user_prompts_transformer,
                *additional_transformers,
            ):
                prompt = transformer(prompt)

            async with AsyncExitStack() as exit_stack:
                tools = await self.tool_provider.get_tools(session, self.metrics_logger, exit_stack)
                last_message = await self._invoke_llm(instrumenter, session, prompt, tools)
            return last_message

    async def _invoke_llm(
        self,
        instrumenter: Instrumenter,
        session: Session,
        prompt: Sequence[BaseMessage],
        tools: List[BaseTool],
    ) -> AIMessage:
        agent = create_react_agent(self.model, tools=tools)

        # Return the response and log token usage
        response: dict[str, Any] = await agent.ainvoke(
            {"messages": prompt}, {"recursion_limit": MAX_AGENT_RECURSION_DEPTH}
        )
        session.commit()

        for message in response["messages"]:
            logger.info(message)

        last_message = response["messages"][-1]
        token_usage = last_message.response_metadata["token_usage"]["total_tokens"]
        instrumenter.add_metric("tokens_used", token_usage)

        return last_message

    def encode_context_histories(
        self, message_context: MessageContext
    ) -> List[BaseMessage]:
        logger.info(f"Encoding context histories: {message_context}")

        # Collect all messages from all histories
        all_messages: list[ChatMessage] = []
        for chat_history in message_context.histories:
            all_messages.extend(chat_history.messages)

        # Deduplicate messages by ID
        unique_messages: dict[str, ChatMessage] = {}
        for message in all_messages:
            if message.id not in unique_messages:
                unique_messages[message.id] = message
            else:
                logger.debug(
                    f"Deduplicate message ID: {message.id}, content: {message.content}"
                )

        # Sort messages by datetime if available
        # Ensure all datetime objects are timezone-aware before comparison
        def get_comparable_datetime(msg):
            if not hasattr(msg, "datetime") or not msg.datetime:
                return datetime.min.replace(tzinfo=dt.timezone.utc)
            if msg.datetime.tzinfo is None:  # If datetime is naive
                return msg.datetime.replace(tzinfo=dt.timezone.utc)
            return msg.datetime

        sorted_messages = sorted(
            unique_messages.values(),
            key=lambda m: get_comparable_datetime(m),
        )

        # Convert to LangChain message format
        combined_messages = []
        for message in sorted_messages:
            if message.type == USER_MESSAGE_TYPE:
                combined_messages.append(HumanMessage(message.content))
            elif message.type == AI_MESSAGE_TYPE:
                combined_messages.append(AIMessage(message.content))

        return combined_messages
