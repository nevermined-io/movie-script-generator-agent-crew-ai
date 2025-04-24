"""
Task-related models for A2A protocol
"""
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class TaskState(str, Enum):
    """
    Valid task states according to A2A protocol
    """
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INPUT_REQUIRED = "input-required"

class Part(BaseModel):
    """
    Base class for message and artifact parts
    """
    type: str
    metadata: Optional[Dict[str, Any]] = None

class TextPart(Part):
    """
    Text part for messages and artifacts
    """
    type: str = "text"
    text: str

class InlineDataPart(Part):
    """
    Inline data part for messages and artifacts
    """
    type: str = "inline-data"
    mimeType: str
    data: str  # Base64-encoded data

class ReferenceDataPart(Part):
    """
    Reference data part for messages and artifacts
    """
    type: str = "reference-data"
    mimeType: str
    reference: Dict[str, str]  # Contains URL

class Message(BaseModel):
    """
    Message model for A2A protocol
    """
    role: str
    parts: List[Union[TextPart, InlineDataPart, ReferenceDataPart]]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "role": self.role,
            "parts": [part.dict() for part in self.parts],
            "metadata": self.metadata or {}
        }

class TaskStatus(BaseModel):
    """
    Task status model for A2A protocol
    """
    state: TaskState
    timestamp: str
    message: Optional[Message] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "state": self.state,
            "timestamp": self.timestamp,
            "message": self.message.to_dict() if self.message else None
        }

class Artifact(BaseModel):
    """
    Artifact model for A2A protocol
    """
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Union[TextPart, InlineDataPart, ReferenceDataPart]]
    index: Optional[int] = None
    append: Optional[bool] = None
    lastChunk: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "parts": [part.dict() for part in self.parts],
            "index": self.index,
            "append": self.append,
            "lastChunk": self.lastChunk,
            "metadata": self.metadata or {}
        }

class Task(BaseModel):
    """
    Task model for A2A protocol
    """
    id: str
    sessionId: Optional[str] = None
    status: TaskStatus
    artifacts: Optional[List[Artifact]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "sessionId": self.sessionId,
            "status": self.status.to_dict(),
            "artifacts": [a.to_dict() for a in (self.artifacts or [])],
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_params(cls, params: 'TaskSendParams') -> 'Task':
        """
        Create a task from TaskSendParams
        """
        return cls(
            id=params.id,
            sessionId=params.sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(**params.message) if isinstance(params.message, dict) else params.message
            ),
            metadata=params.metadata
        )

class PushNotificationConfig(BaseModel):
    """
    Configuration for push notifications
    """
    url: str
    token: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None

class TaskPushNotificationConfig(BaseModel):
    """
    Push notification configuration for a task
    """
    id: str
    pushNotificationConfig: PushNotificationConfig 