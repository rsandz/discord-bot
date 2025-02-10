import logging
from typing import Optional
from uuid import uuid4

class RequestIdFilter(logging.Filter):
    """Filters log records and adds the current request ID to the record if it exists."""
    def __init__(self):
        super().__init__()
        self.current_request_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.current_request_id or ""
        return True

    def set_request_id(self, request_id: Optional[str]):
        self.current_request_id = request_id

class RequestIdContextManager:
    """Context manager that sets the current request ID and resets it when exiting."""
    def __init__(self, request_id_filter: RequestIdFilter):
        self.request_id_filter = request_id_filter

    def __enter__(self):
        self.request_id_filter.set_request_id(uuid4().hex[:10])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.request_id_filter.set_request_id(None)