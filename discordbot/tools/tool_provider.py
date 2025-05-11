from contextlib import AsyncExitStack
from typing import List
from sqlalchemy.orm import Session
from langchain.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

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

    def __init__(self, alarm_service: AlarmService, mcp_config: dict):
        self.alarm_tools = AlarmToolAdapter(alarm_service)
        self.messaging_tools = MessagingTools()
        self.mcp_config = mcp_config

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

    async def get_tools(
        self, session: Session, metrics_logger: MetricsLogger, exit_stack: AsyncExitStack
    ) -> List[BaseTool]:
        tools = []

        mcp_client = await exit_stack.enter_async_context(MultiServerMCPClient(self.mcp_config))
        tools.extend(mcp_client.get_tools())

        tools.extend([
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
        ])
        return tools
