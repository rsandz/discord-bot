from dataclasses import dataclass
from typing import Sequence

from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from discordbot.models.event import SystemMessageEvent

@dataclass
class LlmInvocationRequest:
    """Represents the data passed to an LLM on invocation."""

    system_messages: Sequence[SystemMessage]
    """The system messages to provide to the LLM."""

    chat_history: Sequence[BaseMessage]
    """The message history to provide to the LLM."""

    primary_message: HumanMessage
    """The primary message that the LLM will respond to."""

    tools: Sequence[BaseTool]
    """The tools to make available to the LLM."""

    def generate_prompt(self) -> Sequence[BaseMessage]:
        """Generate the prompt that langchain will use to invoke the LLM."""
        return [
            *self.system_messages,
            *self.chat_history,
            self.primary_message,
        ]

@dataclass
class SystemEventLlmInvocationRequest(LlmInvocationRequest):
    """Represents the data passed to an LLM on invocation for a system event like an alarm."""

    event_context: SystemMessageEvent
    """The event context to provide to the LLM."""

    def generate_prompt(self) -> Sequence[BaseMessage]:
        """Generate the prompt that langchain will use to invoke the LLM."""
        return [
            SystemMessage(
                "You are a helpful assistant that's responding to a system event. Outputs of this invocation aren't directly outputted to the user. If the intention isn't clear, you can just do nothing."
                f"Event Source: {self.event_context.event_source}, "
                f"Event Description: {self.event_context.event_description}, "
                f"Additional Data: {self.event_context.additional_data}"
            ),
            *super().generate_prompt()
        ]