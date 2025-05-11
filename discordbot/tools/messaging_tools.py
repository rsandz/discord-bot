import logging
import asyncio
from typing import Callable, List, Union, Awaitable
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from hangoutsscheduler.utils.logging.metrics import MetricsLogger

logger = logging.getLogger(__name__)


class NotifyAllUsersInput(BaseModel):
    message: str = Field(..., description="The message to send to all users")


class MessagingTools:
    """Tools to send messages to users."""

    def __init__(self):
        self._listeners: List[
            Union[Callable[[str], None], Callable[[str], Awaitable[None]]]
        ] = []

    def add_message_listener(
        self, callback: Union[Callable[[str], None], Callable[[str], Awaitable[None]]]
    ) -> None:
        self._listeners.append(callback)

    def remove_message_listener(
        self, callback: Union[Callable[[str], None], Callable[[str], Awaitable[None]]]
    ) -> None:
        self._listeners.remove(callback)

    async def notify_all(
        self, session: Session, metrics_logger: MetricsLogger, message: str
    ) -> None:
        with metrics_logger.instrumenter("MessagingTools.notify_all"):
            for listener in self._listeners:
                logger.info(f"Notifying listener {listener.__name__}")
                if asyncio.iscoroutinefunction(listener):
                    await listener(message)
                else:
                    listener(message)
