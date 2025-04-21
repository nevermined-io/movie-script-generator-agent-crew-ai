"""
Logging system that logs both locally and through the Nevermined Payments API.
"""
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class PaymentsAPIHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Nevermined Payments API.
    
    @param api_key - Nevermined Payments API key
    @param api_url - Nevermined Payments API URL
    """
    def __init__(self, api_key: str, api_url: str):
        super().__init__()
        self.api_key = api_key
        self.api_url = api_url
        
    def emit(self, record: logging.LogRecord) -> None:
        """
        Send log record to Nevermined Payments API.
        
        @param record - Log record to send
        """
        try:
            # TODO: Implement actual API call when Nevermined Payments API is available
            # For now, just print to stderr
            print(f"[Payments API] {self.format(record)}", file=sys.stderr)
        except Exception as e:
            print(f"Error sending log to Payments API: {e}", file=sys.stderr)

class MovieScriptLogger:
    """
    Logger class that handles both local and Payments API logging.
    """
    def __init__(
        self,
        name: str = "movie_script_generator",
        level: int = logging.INFO,
        log_file: Optional[str] = "movie_script_generator.log",
        payments_api_key: Optional[str] = None,
        payments_api_url: Optional[str] = None
    ):
        """
        Initialize logger with both local and API handlers.
        
        @param name - Logger name
        @param level - Logging level
        @param log_file - Local log file path
        @param payments_api_key - Nevermined Payments API key
        @param payments_api_url - Nevermined Payments API URL
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Add Payments API handler if credentials provided
        if payments_api_key and payments_api_url:
            payments_handler = PaymentsAPIHandler(payments_api_key, payments_api_url)
            payments_handler.setFormatter(file_formatter)
            self.logger.addHandler(payments_handler)
    
    def log_script_generation(
        self,
        task_id: str,
        status: str,
        metadata: Dict[str, Any],
        error: Optional[str] = None
    ) -> None:
        """
        Log script generation event.
        
        @param task_id - Task identifier
        @param status - Current task status
        @param metadata - Task metadata
        @param error - Error message if any
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "status": status,
            "metadata": metadata
        }
        
        if error:
            log_data["error"] = error
            self.logger.error(f"Script generation failed - Task {task_id}: {error}", extra=log_data)
        else:
            self.logger.info(f"Script generation {status} - Task {task_id}", extra=log_data)

# Create singleton instance
logger = MovieScriptLogger(
    payments_api_key=os.getenv("NEVERMINED_PAYMENTS_API_KEY"),
    payments_api_url=os.getenv("NEVERMINED_PAYMENTS_API_URL")
) 