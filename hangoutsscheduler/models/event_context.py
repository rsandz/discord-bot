from dataclasses import dataclass, field


@dataclass
class EventContext:
    """Represents an event the LLM can respond to."""

    event_source: str
    event_description: str
    additional_data: dict = field(default_factory=dict)
