from typing import List
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from hangoutsscheduler.models.orm.alarm import Alarm
from hangoutsscheduler.models.orm.event import Event
from hangoutsscheduler.utils.logging.metrics import MetricsLogger

import logging

logger = logging.getLogger(__name__)

class CreateEventInput(BaseModel):
    title: str = Field(..., description="The title of the event")
    start_time: str = Field(..., description="Start time of the event")
    end_time: str = Field(..., description="End time of the event")

class SearchEventsInput(BaseModel):
    title: str = Field(..., description="The title of the event to retrieve")

class ListEventsInput(BaseModel):
    page: int = Field(default=1, description="Page number to retrieve (starts from 1)")
    per_page: int = Field(default=5, description="Number of events per page")

class EventTools:
    def search_events_by_title(self, session: Session, metrics_logger: MetricsLogger, title: str) -> str:
        with metrics_logger.instrumenter("EventTools.search_events_by_title"):
            events = session.query(Event).filter(
                Event.title.ilike(f"%{title}%")
            ).all()
            logger.info(f"Retrieved event by title: {title} returned {events}")

            if not events:
                return f"Event {title} not found"
                
            return str(events)

    def create_event(self, session: Session, metrics_logger: MetricsLogger, title: str, start_time: str, end_time: str) -> str:
        with metrics_logger.instrumenter("EventTools.create_event"):
            start_datetime = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")

            event = Event(title=title, start_time=start_datetime, end_time=end_datetime)
            session.add(event)

            alarm = Alarm(trigger_time=start_datetime, description=f"Alarm for event with title '{title}' that is now starting.")
            event.alarm = alarm
            session.add(alarm)

            logger.info(f"Event {title} created successfully")

            return f"Event {title} created successfully"

    def list_events(self, session: Session, metrics_logger: MetricsLogger, page: int = 1, per_page: int = 5) -> str:
        with metrics_logger.instrumenter("EventTools.list_events"):
            total_count = session.query(Event).count()
            if total_count == 0:
                return "No events found"

            offset = (page - 1) * per_page
            events = session.query(Event).order_by(Event.start_time).offset(offset).limit(per_page).all()
            total_pages = (total_count + per_page - 1) // per_page

        events_str = [f"Page {page} of {total_pages} (Total events: {total_count})", "-" * 50]
        for event in events:
            events_str.append(str(event))

        if page < total_pages:
            events_str.append(f"\nUse page={page + 1} to see the next page")
        if page > 1:
            events_str.append(f"Use page={page - 1} to see the previous page")

        logger.info(f"Listed {len(events)} events.")
        return "\n".join(events_str)
