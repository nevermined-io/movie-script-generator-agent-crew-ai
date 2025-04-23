"""
A2A Protocol controller implementation.
"""
from datetime import datetime
from typing import Dict, Optional, List, Any
from uuid import uuid4
import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..models.task import TaskState, TaskStatus, Message, TextPart
from ..models.a2a import Task, PushNotificationConfig
from ..models.agent_card import AGENT_CARD
from ..core.generator import MovieScriptGenerator
from ..models.script_artifact import create_script_artifact
from ..core.domain_models import ExtractedScene, TransformedScene, ScriptMetadata, ScriptCharacter
from ..utils.logger import logger

class TaskRequest(BaseModel):
    """Request model for task creation."""
    title: str
    tags: list[str]
    idea: str
    lyrics: Optional[str] = None
    duration: Optional[int] = None
    sessionId: Optional[str] = None

class A2AController:
    """Controller for A2A protocol integration."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance is created (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(A2AController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the controller with a task store."""
        if not self._initialized:
            self.tasks: Dict[str, Task] = {}
            self.push_configs: Dict[str, PushNotificationConfig] = {}
            self.generator = MovieScriptGenerator()
            self.router = APIRouter()
            self._setup_routes()
            self._initialized = True
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        self.router.add_api_route(
            "/agent-card",
            self.get_agent_card,
            methods=["GET"]
        )
        self.router.add_api_route(
            "/tasks/send",
            self.send_task,
            methods=["POST"],
            response_model=Task
        )
        self.router.add_api_route(
            "/tasks/sendSubscribe",
            self.send_task_streaming,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/tasks/{task_id}",
            self.get_task,
            methods=["GET"],
            response_model=Task
        )
        self.router.add_api_route(
            "/tasks/{task_id}/cancel",
            self.cancel_task,
            methods=["POST"],
            response_model=Task
        )
        self.router.add_api_route(
            "/tasks",
            self.list_tasks,
            methods=["GET"],
            response_model=List[Task]
        )
        self.router.add_api_route(
            "/tasks/{task_id}/pushNotification",
            self.set_push_notification,
            methods=["POST"],
            response_model=PushNotificationConfig
        )
        self.router.add_api_route(
            "/tasks/{task_id}/pushNotification",
            self.get_push_notification,
            methods=["GET"],
            response_model=PushNotificationConfig
        )
    
    async def get_agent_card(self):
        """Return the agent card describing this agent's capabilities."""
        return AGENT_CARD

    async def send_task(self, request: TaskRequest) -> Task:
        """Create and process a new task."""
        task_id = str(uuid4())
        
        # Log task creation
        logger.log_script_generation(
            task_id=task_id,
            status="created",
            metadata={
                "title": request.title,
                "tags": request.tags,
                "idea": request.idea,
                "lyrics": request.lyrics,
                "duration": request.duration,
                "session_id": request.sessionId,
            }
        )
        
        # Create initial task with submitted status
        task = Task(
            id=task_id,
            sessionId=request.sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Starting script generation...")]
                )
            ),
            metadata={
                "title": request.title,
                "tags": request.tags,
                "idea": request.idea,
                "lyrics": request.lyrics,
                "duration": request.duration
            }
        )
        
        # Store task
        self.tasks[task_id] = task
        
        # Start background processing
        asyncio.create_task(self._process_task(task, request))
        
        
        return task
        
    async def _process_task(self, task: Task, request: TaskRequest):
        """Process task in background."""
        try:
            # Update status to working
            task.status = TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Generating movie script...")]
                )
            )

            # Log task started
            logger.log_script_generation(
                task_id=task.id,
                status="started",
                metadata=task.metadata
            )
            
            # Generate the script in a separate thread to avoid blocking
            try:
                # Run the blocking operation in a separate thread
                result = await asyncio.to_thread(
                    self.generator.generate_script,
                    title=request.title,
                    tags=request.tags,
                    idea=request.idea,
                    lyrics=request.lyrics,
                    duration=request.duration
                )
                
                if not result:
                    raise Exception("Failed to generate script - empty result")
                    
                # Create extracted scenes
                extracted_scenes = [
                    ExtractedScene(
                        sceneNumber=i + 1,
                        startTime="00:00",  # These should be calculated based on duration
                        endTime="00:00",    # These should be calculated based on duration
                        shotType=scene.get("shot_type", ""),
                        cameraMovement=scene.get("camera_movement", ""),
                        cameraEquipment=scene.get("camera_equipment", ""),
                        location=scene.get("location", ""),
                        lightingSetup=scene.get("lighting_setup", {}),
                        colorPalette=scene.get("color_palette", []),
                        visualReferences=scene.get("visual_references", []),
                        characterActions=scene.get("character_actions", {}),
                        transitionType=scene.get("transition_type", ""),
                        specialNotes=scene.get("special_notes", [])
                    )
                    for i, scene in enumerate(result["scenes"])
                ]

                # Create transformed scenes
                transformed_scenes = [
                    TransformedScene(
                        sceneNumber=i + 1,
                        description=scene.get("description", ""),
                        prompt=scene.get("prompt", ""),
                        charactersInScene=scene.get("characters_in_scene", []),
                        settingId=scene.get("setting_id", ""),
                        duration=scene.get("duration", 0),
                        technicalDetails=scene.get("technical_details", {})
                    )
                    for i, scene in enumerate(result.get("transformedScenes", []))
                ]
                
                # Create metadata
                metadata = ScriptMetadata(
                    title=request.title,
                    genre_tags=request.tags,
                    duration=request.duration,
                    total_scenes=len(extracted_scenes),
                    characters=[
                        ScriptCharacter(**char)
                        for char in result.get("characters", [])
                    ]
                )
                
                # Create and attach artifact
                task.artifacts = [
                    create_script_artifact(
                        script_text=result["script"],
                        scenes=extracted_scenes,
                        transformed_scenes=transformed_scenes,
                        metadata=metadata
                    )
                ]
                
                # Update task with completion status
                task.status = TaskStatus(
                    state=TaskState.COMPLETED,
                    timestamp=datetime.utcnow().isoformat(),
                    message=Message(
                        role="assistant",
                        parts=[TextPart(type="text", text=f"Successfully generated script for '{request.title}'")]
                    )
                )
                
                # Log completion
                logger.log_script_generation(
                    task_id=task.id,
                    status="completed",
                    metadata=task.metadata
                )
                
            except Exception as e:
                error_message = f"Failed to generate script: {str(e)}"
                
                # Update task with error status
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    timestamp=datetime.utcnow().isoformat(),
                    message=Message(
                        role="assistant",
                        parts=[TextPart(type="text", text=error_message)]
                    )
                )
                
                # Log error
                logger.log_script_generation(
                    task_id=task.id,
                    status="error",
                    metadata={
                        **task.metadata,
                        "error": error_message
                    }
                )
                
        except Exception as e:
            error_message = f"Task processing failed: {str(e)}"
            
            # Update task with error status
            task.status = TaskStatus(
                state=TaskState.FAILED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text=error_message)]
                )
            )
            
            # Log error
            logger.log_script_generation(
                task_id=task.id,
                status="error",
                metadata={
                    **task.metadata,
                    "error": error_message
                }
            )

    async def get_task(self, task_id: str) -> Task:
        """Get the current state of a task."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return self.tasks[task_id]

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task in progress."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = self.tasks[task_id]
        if task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
            raise HTTPException(status_code=400, detail="Task already finished")
        
        task.status = TaskStatus(
            state=TaskState.CANCELED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Task canceled by user request")]
            )
        )

        # Log cancellation
        logger.log_script_generation(
            task_id=task_id,
            status="canceled",
            metadata=task.metadata
        )
        
        return task

    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[Task]:
        """List all tasks, optionally filtered by session ID and state."""
        tasks = list(self.tasks.values())
        
        # Filter by session ID if provided
        if session_id:
            tasks = [t for t in tasks if t.sessionId == session_id]
            
        # Filter by state if provided
        if state:
            tasks = [t for t in tasks if t.status.state == state]
            
        return tasks

    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> PushNotificationConfig:
        """Set push notification configuration for a task."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        try:
            self.push_configs[task_id] = config
            return config
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_push_notification(self, task_id: str) -> PushNotificationConfig:
        """Get push notification configuration for a task."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        try:
            config = self.push_configs.get(task_id)
            if not config:
                raise HTTPException(status_code=404, detail=f"No push notification config found for task {task_id}")
            return config
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def send_task_streaming(self, request: TaskRequest) -> StreamingResponse:
        """Create and process a new task with streaming updates."""
        task = await self.send_task(request)
        
        async def event_stream():
            """Generate SSE events for task updates."""
            while True:
                current_task = self.tasks.get(task.id)
                if not current_task:
                    break
                    
                yield f"data: {current_task.json()}\n\n"
                
                if current_task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                    break
                    
                await asyncio.sleep(1)
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream"
        )

def process_scene(scene_data: Dict[str, Any]) -> ExtractedScene:
    """Process raw scene data into an ExtractedScene object"""
    return ExtractedScene(
        # ... scene processing logic ...
    )

# Create singleton instance
controller = A2AController()
router = controller.router 