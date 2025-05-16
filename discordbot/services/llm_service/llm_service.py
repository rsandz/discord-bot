import logging
from datetime import datetime
from langchain.chat_models.base import BaseChatModel
from langgraph.prebuilt import create_react_agent
from typing import Any

from discordbot.models.message import TimeStampedAIMessage
from discordbot.services.llm_service import LlmInvocationRequest
from discordbot.utils.logging.metrics import MetricsLogger

logger = logging.getLogger(__name__)

MAX_AGENT_RECURSION_DEPTH = 16

class LlmService:
    """Service for invoking the LLM"""

    def __init__(
        self,
        model: BaseChatModel,
        metrics_logger: MetricsLogger,
    ):
        self.model: BaseChatModel = model
        self.metrics_logger = metrics_logger

    async def invoke_llm(self, llm_invocattion_request: LlmInvocationRequest) -> TimeStampedAIMessage:
        with self.metrics_logger.instrumenter("LLMService.invoke_llm") as instrumenter:
            agent = create_react_agent(self.model, tools=llm_invocattion_request.tools)
            prompt = llm_invocattion_request.generate_prompt()
            response: dict[str, Any] = await agent.ainvoke(
                {"messages": prompt}, {"recursion_limit": MAX_AGENT_RECURSION_DEPTH}
            )

        for message in response["messages"]:
            logger.info(message)

        last_message = response["messages"][-1]
        token_usage = last_message.response_metadata["token_usage"]["total_tokens"]
        instrumenter.add_metric("tokens_used", token_usage)

        return TimeStampedAIMessage(
            content=last_message.content,
            timestamp=datetime.now(),
            id=last_message.id,
        )
