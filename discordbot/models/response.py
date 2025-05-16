
from dataclasses import dataclass

from discordbot.models.message import TimeStampedAIMessage

@dataclass
class EventResponse:
    """Response from Discord bot to be processed by integrations."""

    ai_message: TimeStampedAIMessage
    """Content of the response."""
