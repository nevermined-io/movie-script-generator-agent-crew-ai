"""
Server-Sent Events (SSE) models for A2A protocol
"""
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field
from src.models.task import TaskStatus, Artifact

class TaskStatusUpdateEvent(BaseModel):
    """
    Event model for status updates in SSE.
    Sent to update clients on task progress.
    """
    id: str
    status: TaskStatus
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[Artifact]] = None

    def format_sse(self) -> str:
        """
        Format the event as an SSE message
        
        Returns:
            str: Formatted SSE message
        """
        json_data = self.json()
        return f"event: status_update\ndata: {json_data}\n\n"

class TaskArtifactUpdateEvent(BaseModel):
    """
    Event model for artifact updates in SSE.
    Sent when a new artifact part is available.
    """
    id: str
    artifact: Artifact
    metadata: Optional[Dict[str, Any]] = None

    def format_sse(self) -> str:
        """
        Format the event as an SSE message
        
        Returns:
            str: Formatted SSE message
        """
        json_data = self.json()
        return f"event: artifact\ndata: {json_data}\n\n"

class TaskErrorEvent(BaseModel):
    """
    Event model for error notifications in SSE.
    Sent when an error occurs during task processing.
    """
    id: str
    error: Dict[str, Any] = Field(
        ...,
        description="Error details with code, message and optional data",
        example={
            "code": -32602,
            "message": "Invalid request format",
            "data": {"details": "Required field 'idea' is missing"}
        }
    )

    def format_sse(self) -> str:
        """
        Format the event as an SSE message
        
        Returns:
            str: Formatted SSE message
        """
        json_data = self.json()
        return f"event: error\ndata: {json_data}\n\n"

class SSEKeepAliveEvent(BaseModel):
    """
    Event model for keep-alive messages in SSE.
    Sent periodically to keep the connection open.
    """
    timestamp: str

    def format_sse(self) -> str:
        """
        Format the event as an SSE comment (keep-alive)
        
        Returns:
            str: Formatted SSE comment
        """
        return f": keep-alive {self.timestamp}\n\n" 