from typing import List, Optional
from sqlalchemy.orm import Session
from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from discordbot.tools.messaging_tools import MessagingTools, NotifyAllUsersInput
from discordbot.utils.logging.metrics import MetricsLogger
from discordbot.services.alarm import AlarmService
from discordbot.services.alarm import (
    AlarmToolAdapter,
    CreateAlarmInput,
    UpdateAlarmInput,
    DeleteAlarmInput,
    ListAlarmsInput,
)


class ToolProvider:
    """Provides tools for interacting with the database"""

    def __init__(self, alarm_service: AlarmService):
        self.alarm_tools = AlarmToolAdapter(alarm_service)
        self.messaging_tools = MessagingTools()

    def get_system_tools(
        self, session: Session, metrics_logger: MetricsLogger
    ) -> List[BaseTool]:
        """Tools for responding to system events."""
        return [
            StructuredTool(
                name="notify_all_users",
                description="Send a message to all users",
                args_schema=NotifyAllUsersInput,
                coroutine=lambda **kwargs: self.messaging_tools.notify_all(
                    session, metrics_logger, **kwargs
                ),
            )
        ]

    def get_tools(
        self, session: Session, metrics_logger: MetricsLogger
    ) -> List[BaseTool]:
        return [
            StructuredTool(
                name="create_alarm",
                description="Create a new alarm with trigger time and description",
                args_schema=CreateAlarmInput,
                func=lambda **kwargs: self.alarm_tools.create_alarm(
                    session, metrics_logger, **kwargs
                ),
            ),
            StructuredTool(
                name="update_alarm",
                description="Update an existing alarm's trigger time or description",
                args_schema=UpdateAlarmInput,
                func=lambda **kwargs: self.alarm_tools.update_alarm(
                    session, metrics_logger, **kwargs
                ),
            ),
            StructuredTool(
                name="delete_alarm",
                description="Delete an existing alarm",
                args_schema=DeleteAlarmInput,
                func=lambda **kwargs: self.alarm_tools.delete_alarm(
                    session, metrics_logger, **kwargs
                ),
            ),
            StructuredTool(
                name="list_alarms",
                description="List all alarms",
                args_schema=ListAlarmsInput,
                func=lambda **kwargs: self.alarm_tools.list_alarms(
                    session, metrics_logger, **kwargs
                ),
            ),
        ]
