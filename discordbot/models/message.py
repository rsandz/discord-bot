from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

class TimeStampedMessage(BaseMessage):
    """Base class for time-stamped messages."""

    timestamp: datetime
    """The datetime of the message."""


class TimeStampedHumanMessage(HumanMessage, TimeStampedMessage):
    """A time-stamped human message."""
    pass

class TimeStampedAIMessage(AIMessage, TimeStampedMessage):
    """A time-stamped AI message."""
    pass

class TimeStampedSystemMessage(SystemMessage, TimeStampedMessage):
    """A time-stamped system message."""
    pass