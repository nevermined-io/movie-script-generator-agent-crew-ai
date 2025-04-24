"""
Data models for the A2A protocol client
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TaskStatus:
    """
    Represents the status of a task in the A2A protocol
    
    @param state: Current state of the task
    @param message: Optional message with details about the state
    @param timestamp: When this status was recorded
    """
    state: str
    message: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskStatus':
        """
        Create a TaskStatus from a dictionary
        
        @param data: Dictionary with status data
        @returns: TaskStatus instance
        """
        return cls(
            state=data["state"],
            message=data.get("message"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat())
        )

@dataclass
class TaskArtifact:
    """
    Represents an artifact produced by a task
    
    @param parts: Content parts of the artifact
    @param name: Optional name of the artifact
    @param index: Optional index for ordering
    @param mime_type: Optional MIME type of the content
    """
    parts: List[Dict[str, Any]]
    name: Optional[str] = None
    index: Optional[int] = None
    mime_type: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskArtifact':
        """
        Create a TaskArtifact from a dictionary
        
        @param data: Dictionary with artifact data
        @returns: TaskArtifact instance
        """
        return cls(
            parts=data["parts"],
            name=data.get("name"),
            index=data.get("index"),
            mime_type=data.get("mimeType")
        ) 