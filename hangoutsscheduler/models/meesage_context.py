from dataclasses import dataclass, field
from typing import Any, List

@dataclass
class MessageContext:
    message: str
    username: str
    history: List[Any] = field(default_factory=list)