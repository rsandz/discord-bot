import logging
from datetime import datetime
from typing import Any, List
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticToolsParser
from langgraph.prebuilt import create_react_agent

from sqlalchemy.orm import Session

from hangoutsscheduler.constants import USER_MESSAGE_TYPE, SYSTEM_MESSAGE_TYPE, AI_MESSAGE_TYPE
from hangoutsscheduler.models.event_context import EventContext
from hangoutsscheduler.models.meesage_context import MessageContext
from hangoutsscheduler.utils.logging.metrics import Instrumenter, MetricsLogger
from hangoutsscheduler.tools.tool_provider import ToolProvider

logger = logging.getLogger(__name__)

MAX_AGENT_RECURSION_DEPTH = 16

SYSTEM_EVENT_PROMPT = "You are a helpful assistant that's responding to a system event. Outputs of this invocation aren't directly outputted to the user. If the intention isn't clear, you can just do nothing."

class LlmService():

    def __init__(self, model: BaseChatModel, tool_provider: ToolProvider, metrics_logger: MetricsLogger, prompt):
        self.model: BaseChatModel = model
        self.system_message = SystemMessage(prompt)
        self.tool_provider = tool_provider
        # Initialize metrics logger
        self.metrics_logger = metrics_logger

    def respond_to_system_event(self, event_context: EventContext, session: Session):
        with self.metrics_logger.instrumenter("LLMService.respond_to_system_message") as instrumenter:
            logger.info(f"Responding to system message: {event_context}")

            prompt = [
                SystemMessage(SYSTEM_EVENT_PROMPT),
                SystemMessage(f"Current Time: {datetime.now().astimezone().isoformat()}"),
                SystemMessage(f"Event Source: {event_context.event_source}, Event Description: {event_context.event_description}, Additional Data: {event_context.additional_data}"),
            ]

            tools = self.tool_provider.get_system_tools(session, self.metrics_logger)
            last_message = self._invoke_llm(instrumenter, session, prompt, tools) # type: ignore
            return last_message


    async def respond_to_user_message(self, message_context: MessageContext, session: Session) -> str:
        with self.metrics_logger.instrumenter("LLMService.respond_to_message") as instrumenter:
            message = message_context.message
            logger.info(f"Responding to message: {message}")

            # Include chat history in the prompt
            history_messages = []
            for h in message_context.history:
                if h['type'] == USER_MESSAGE_TYPE:
                    history_messages.append(HumanMessage(h['content']))
                elif h['type'] in [AI_MESSAGE_TYPE]:
                    history_messages.append(AIMessage(h['content']))    

            prompt = [
                SystemMessage(f"Current User: {message_context.username}"),
                SystemMessage(f"Current Time: {datetime.now().astimezone().isoformat()}"),
                self.system_message,
                *history_messages,
                message
            ]

            tools = self.tool_provider.get_tools(session, self.metrics_logger)
            last_message = await self._invoke_llm(instrumenter, session, prompt, tools)
            return last_message

    async def _invoke_llm(self, instrumenter: Instrumenter, session: Session, prompt: List[BaseMessage], tools: List[BaseTool]) -> str:
        if len(tools) > 0:
            agent = create_react_agent(self.model, tools=tools)
        else:
            agent = self.model

        # Return the response and log token usage
        response: Any = await agent.ainvoke({"messages": prompt}, {"recursion_limit": MAX_AGENT_RECURSION_DEPTH}) # type: ignore
        session.commit()
        
        for message in response["messages"]:
            logger.info(message)


        last_message = response["messages"][-1]
        token_usage = last_message.response_metadata['token_usage']['total_tokens']
        instrumenter.add_metric('tokens_used', token_usage)

        return last_message
