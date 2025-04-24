"""
A2A Protocol data models
"""
from typing import Dict, Any, Optional, List, Union, Set
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime
from src.models.task import TaskState, TaskStatus, Message, Artifact, TextPart

class AgentProvider(BaseModel):
    """
    Information about the agent provider
    """
    organization: str
    url: Optional[str] = None

class AgentCapabilities(BaseModel):
    """
    Agent capabilities
    """
    streaming: Optional[bool] = True
    pushNotifications: Optional[bool] = True
    stateTransitionHistory: Optional[bool] = True

class AgentAuthentication(BaseModel):
    """
    Agent authentication requirements
    """
    schemes: List[str]
    credentials: Optional[str] = None

class AgentSkill(BaseModel):
    """
    Agent skill definition
    """
    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None

class AgentCard(BaseModel):
    """
    Agent metadata and capabilities
    """
    name: str
    description: Optional[str] = None
    url: str
    provider: Optional[AgentProvider] = None
    version: str
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities
    authentication: Optional[AgentAuthentication] = None
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    skills: List[AgentSkill]

class TaskSendParams(BaseModel):
    """
    Parameters for sending a task
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: Dict[str, Any]
    sessionId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    acceptedOutputModes: Optional[List[str]] = Field(
        default=["text"],
        description="List of output modes the client can handle"
    )

    @validator("acceptedOutputModes")
    def validate_output_modes(cls, v: Optional[List[str]]) -> List[str]:
        """Validate that output modes are supported"""
        if not v:
            return ["text"]
            
        valid_modes = {"text", "markdown", "html", "json"}
        invalid_modes = set(v) - valid_modes
        if invalid_modes:
            raise ValueError(
                f"Unsupported output modes: {invalid_modes}. "
                f"Supported modes are: {valid_modes}"
            )
        return v

class PushNotificationConfig(BaseModel):
    """
    Push notification configuration
    """
    url: str
    events: List[str]
    headers: Optional[Dict[str, str]] = None
    token: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None

class ArtifactPart(BaseModel):
    """
    Part of an artifact in the A2A protocol
    """
    mimeType: str
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]]

class Task(BaseModel):
    """
    A2A Task model representing a task in the system
    """
    id: str
    sessionId: Optional[str] = None
    status: TaskStatus
    metadata: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[Artifact]] = None
    history: Optional[List[TaskStatus]] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_params(cls, params: TaskSendParams) -> 'Task':
        """
        Create a Task instance from TaskSendParams
        
        Args:
            params (TaskSendParams): The parameters to create the task from
            
        Returns:
            Task: A new Task instance
        """
        return cls(
            id=params.id,
            sessionId=params.sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Task submitted")]
                )
            ),
            metadata=params.metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary representation
        
        Returns:
            Dict[str, Any]: Dictionary representation of the task
        """
        return self.dict(exclude_none=True) 