from typing import List
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from hangoutsscheduler.models.orm.alarm import Alarm
from hangoutsscheduler.models.orm.event import Event
from hangoutsscheduler.utils.logging.metrics import MetricsLogger

import logging

logger = logging.getLogger(__name__)

ISO_FORMAT = "yyyy-MM-ddTHH:mm:ss±hh:mm (or Z for UTC)"


class CreateEventInput(BaseModel):
    title: str = Field(..., description="The title of the event")
    start_time: str = Field(
        ..., description=f"Start time of the event in ISO format {ISO_FORMAT}"
    )
    end_time: str = Field(
        ..., description=f"End time of the event in ISO format {ISO_FORMAT}"
    )


class SearchEventsInput(BaseModel):
    title: str = Field(..., description="The title of the event to retrieve")


class ListEventsInput(BaseModel):
    page: int = Field(default=1, description="Page number to retrieve (starts from 1)")
    per_page: int = Field(default=5, description="Number of events per page")


class EventTools:
    def search_events_by_title(
        self, session: Session, metrics_logger: MetricsLogger, title: str
    ) -> str:
        with metrics_logger.instrumenter("EventTools.search_events_by_title"):
            events = session.query(Event).filter(Event.title.ilike(f"%{title}%")).all()
            logger.info(f"Retrieved event by title: {title} returned {events}")

            if not events:
                return f"Event {title} not found"

            return str(events)

    def create_event(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        title: str,
        start_time: str,
        end_time: str,
    ) -> str:
        try:
            with metrics_logger.instrumenter("EventTools.create_event"):
                # Try parsing with timezone offset
                start_datetime = datetime.fromisoformat(start_time)
                end_datetime = datetime.fromisoformat(end_time)

                event = Event(
                    title=title, start_time=start_datetime, end_time=end_datetime
                )
                session.add(event)

                alarm = Alarm(
                    trigger_time=start_datetime,
                    description=f"Alarm for event with title '{title}' that is now starting.",
                )
                event.alarm = alarm
                session.add(alarm)

                logger.info(
                    f"Event {title} created successfully with start time {start_datetime} and end time {end_datetime}"
                )
                return f"Event '{title}' created successfully"
        except ValueError as e:
            error_msg = f"Failed to create event: Invalid datetime format. Please use ISO format {ISO_FORMAT}"
            logger.error(f"{error_msg}. Error: {e}")
            return error_msg

    def list_events(
        self,
        session: Session,
        metrics_logger: MetricsLogger,
        page: int = 1,
        per_page: int = 5,
    ) -> str:
        with metrics_logger.instrumenter("EventTools.list_events"):
            total_count = session.query(Event).count()
            if total_count == 0:
                return "No events found"

            offset = (page - 1) * per_page
            events = (
                session.query(Event)
                .order_by(Event.start_time)
                .offset(offset)
                .limit(per_page)
                .all()
            )
            total_pages = (total_count + per_page - 1) // per_page

        events_str = [
            f"Page {page} of {total_pages} (Total events: {total_count})",
            "-" * 50,
        ]
        for event in events:
            events_str.append(str(event))

        if page < total_pages:
            events_str.append(f"\nUse page={page + 1} to see the next page")
        if page > 1:
            events_str.append(f"Use page={page - 1} to see the previous page")

        logger.info(f"Listed {len(events)} events.")
        return "\n".join(events_str)
