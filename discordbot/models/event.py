
from dataclasses import dataclass

from discordbot.models.message import TimeStampedMessage, TimeStampedHumanMessage, TimeStampedSystemMessage


@dataclass
class Event:
    """Represents an event the LLM can respond to."""

    event_description: str
    """Description of what triggered the event."""

    message: TimeStampedHumanMessage
    """Message that triggered the event."""

@dataclass
class UserMessageEvent(Event):
    """Represents a user message event the LLM can respond to.
    
    Assumes that the event occurs in a space that other users have access to (e.g. chat room).
    Assumes the LLM can receive events from multiple channels/rooms/etc. (e.g. Discord Channel).
    """

    user_id: str
    """ID of the user who triggered the event. This is not the human readable name."""

    user_name: str
    """Human readable name of the user who triggered the event."""

    channel_id: str
    """ID of the channel where the event occurred."""

    immediate_history: list[TimeStampedMessage]
    """Immediate history of the channel before the event occurred."""

@dataclass
class SystemMessageEvent(Event):
    """Represents a system message event the LLM can respond to."""

    event_source: str
    """Source of the event."""

    additional_data: dict
    """Additional data associated with the event."""
