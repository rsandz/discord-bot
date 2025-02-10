from typing import List, Optional
from sqlalchemy.orm import Session
from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from hangoutsscheduler.models.orm.event import Event
from hangoutsscheduler.tools.messaging_tools import MessagingTools, NotifyAllUsersInput
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
from hangoutsscheduler.tools.event_tools import CreateEventInput, SearchEventsInput, ListEventsInput, EventTools
from hangoutsscheduler.tools.alarm_tools import (
    AlarmTools, CreateAlarmInput, UpdateAlarmInput,
    DeleteAlarmInput, ListAlarmsInput
)


class ToolProvider:
    """Provides tools for interacting with the database"""
    def __init__(self):
        self.event_tools = EventTools()
        self.alarm_tools = AlarmTools()
        self.messaging_tools = MessagingTools()


    def get_system_tools(self, session: Session, metrics_logger: MetricsLogger) -> List[BaseTool]:
        """Tools for responding to system events."""
        return [
            StructuredTool(
                name="notify_all_users",
                description="Send a message to all users",
                args_schema=NotifyAllUsersInput,
                coroutine=lambda **kwargs: self.messaging_tools.notify_all(session, metrics_logger, **kwargs)
            )
        ]


    def get_tools(self, session: Session, metrics_logger: MetricsLogger) -> List[BaseTool]:
        return [
            StructuredTool(
                name="create_event",
                description="Create a new event with title, start time, and end time. An event also creates an alarm as a reminder automatically.",
                args_schema=CreateEventInput,
                func=lambda **kwargs: self.event_tools.create_event(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="search_events",
                description="Search for events by title",
                args_schema=SearchEventsInput,
                func=lambda **kwargs: self.event_tools.search_events_by_title(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="list_events",
                description="List events with pagination. Use page parameter to navigate through pages",
                args_schema=ListEventsInput,
                func=lambda **kwargs: self.event_tools.list_events(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="create_alarm",
                description="Create a new alarm with trigger time and description",
                args_schema=CreateAlarmInput,
                func=lambda **kwargs: self.alarm_tools.create_alarm(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="update_alarm",
                description="Update an existing alarm's trigger time or description",
                args_schema=UpdateAlarmInput,
                func=lambda **kwargs: self.alarm_tools.update_alarm(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="delete_alarm",
                description="Delete an existing alarm",
                args_schema=DeleteAlarmInput,
                func=lambda **kwargs: self.alarm_tools.delete_alarm(session, metrics_logger, **kwargs)
            ),
            StructuredTool(
                name="list_alarms",
                description="List all alarms, optionally including past alarms",
                args_schema=ListAlarmsInput,
                func=lambda **kwargs: self.alarm_tools.list_alarms(session, metrics_logger, **kwargs)
            )
        ]
