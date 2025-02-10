import logging
from logging.handlers import RotatingFileHandler
import time
from typing import Optional
from .logging_config import LOGGING_DIR

MAX_LOG_SIZE_BYTES = 1024*1024*1024  # 1GB

class MetricsLogger:
    """Logs metrics to a file.
    
    Flush should be called at the end of each request.
    """
    def __init__(self, request_id_filter=None, log_file='metrics.log', metrics_sublogger: Optional[str] = None):
        self.request_id_filter = request_id_filter
        self.log_file = log_file

        if metrics_sublogger:
            self.logger = logging.getLogger('hangoutsscheduler.metrics.'+metrics_sublogger)
        else:
            self.logger = logging.getLogger('hangoutsscheduler.metrics')
        self.logger.setLevel(logging.INFO)

        # Set up file handler
        handler = RotatingFileHandler(f'{LOGGING_DIR}/{log_file}', maxBytes=MAX_LOG_SIZE_BYTES, backupCount=5)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s\t%(request_id)s\t%(message)s'))

        if request_id_filter:
            handler.addFilter(request_id_filter)

        # Configure logger
        self.logger.handlers = [handler]
        self.logger.propagate = False
        self.metrics_buffer = {}


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()

    def __del__(self):
        self.flush()
    
    def add_metric(self, metric_name, value):
        self.metrics_buffer[metric_name] = value

    def flush(self):
        if len(self.metrics_buffer) == 0:
            return
        formatted_metrics = {f"{k}:{v}" for k, v in self.metrics_buffer.items()}
        metrics_string = ",".join(formatted_metrics)
        self.logger.info(metrics_string)
        self.metrics_buffer.clear()

    def instrumenter(self, operation_name):
        return Instrumenter(MetricsLogger(self.request_id_filter, self.log_file), operation_name)


class Instrumenter:
    """Instruments a block of code. 
    
    Use this instead of calling metrics logger directly.
    """

    def __init__(self, metrics_logger: MetricsLogger, operation_name: str):
        self.metrics_logger = metrics_logger
        self.operation_name = operation_name
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        self.metrics_logger.add_metric(f"duration", end_time - self.start_time)
        self.metrics_logger.add_metric(f"operation", self.operation_name)

        if exc_type:
            self.metrics_logger.add_metric("failure", 1.0)
        else:
            self.metrics_logger.add_metric("failure", 0.0)

    def add_metric(self, metric_name, value):
        self.metrics_logger.add_metric(metric_name, value)