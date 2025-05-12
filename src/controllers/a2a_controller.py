"""
A2A Protocol controller implementation.
"""
from datetime import datetime
from typing import Dict, Optional, List, Any
from uuid import uuid4
import asyncio
import json
import time
import os

from fastapi import HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..models.task import TaskState, TaskStatus, Message, TextPart
from ..models.a2a import Task, PushNotificationConfig
from ..models.agent_card import AGENT_CARD
from ..core.generator import MovieScriptGenerator
from ..models.script_artifact import create_script_artifact
from ..core.domain_models import ExtractedScene, TransformedScene, ScriptMetadata, ScriptCharacter
from ..utils.logger import logger
from ..models.sse import TaskStatusUpdateEvent, TaskArtifactUpdateEvent, TaskErrorEvent, SSEKeepAliveEvent

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
            self._initialized = True
    
    async def get_agent_card(self):
        """Return the agent card describing this agent's capabilities."""
        return AGENT_CARD

    async def send_task(self, *, title: str, tags: list, idea: str, lyrics: str = None, duration: int = None, sessionId: str = None) -> Task:
        """Create and process a new task (A2A strict params)."""
        task_id = str(uuid4())
        # Log task creation
        logger.log_script_generation(
            task_id=task_id,
            status="created",
            metadata={
                "title": title,
                "tags": tags,
                "idea": idea,
                "lyrics": lyrics,
                "duration": duration,
                "session_id": sessionId,
            }
        )
        # Create initial task with submitted status
        task = Task(
            id=task_id,
            sessionId=sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="agent",
                    parts=[TextPart(type="text", text="Starting script generation...")]
                )
            ),
            metadata={
                "title": title,
                "tags": tags,
                "idea": idea,
                "lyrics": lyrics,
                "duration": duration
            }
        )
        # Store task
        self.tasks[task_id] = task
        # Start background processing
        asyncio.create_task(self._process_task(task, TaskRequest(
            title=title,
            tags=tags,
            idea=idea,
            lyrics=lyrics,
            duration=duration,
            sessionId=sessionId
        )))
        return task
        
    async def _process_task(self, task: Task, request: TaskRequest):
        """Process task in background."""
        try:
            # Update status to working
            task.status = TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="agent",
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
                    ExtractedScene(**scene)
                    for scene in result["scenes"]
                ]

                # Create transformed scenes
                transformed_scenes = [
                    TransformedScene(
                        sceneNumber=i + 1,
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
                        role="agent",
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
                        role="agent",
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
                    role="agent",
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
        if task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
            raise HTTPException(status_code=400, detail="Task already finished")
        
        task.status = TaskStatus(
            state=TaskState.CANCELLED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="agent",
                parts=[TextPart(type="text", text="Task cancelled by user request")]
            )
        )

        # Log cancellation
        logger.log_script_generation(
            task_id=task_id,
            status="cancelled",
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

    def _create_status_update_event(self, task: Task, final: bool = False) -> str:
        """Create a formatted SSE status update event."""
        # For final and completed events, it is important to include the artifact in the result
        # to comply with the A2A format that requires the last status_update to include everything
        result = {
            "id": task.id,
            "status": task.status,
            "final": final,
        }
        
        # Include metadata if exists
        if task.metadata:
            result["metadata"] = task.metadata
            
        # Include artifacts in the final event if they exist
        if final and task.status.state == TaskState.COMPLETED and task.artifacts:
            result["artifacts"] = task.artifacts
            
        # Convert to Pydantic model to use its serialization
        event = TaskStatusUpdateEvent(**result)
        return event.format_sse()
        
    def _create_artifact_event(self, task: Task, artifact_index: int = 0) -> str:
        """Create a formatted SSE artifact event."""
        if not task.artifacts or len(task.artifacts) <= artifact_index:
            return None
            
        event = TaskArtifactUpdateEvent(
            id=task.id,
            artifact=task.artifacts[artifact_index],
            metadata=task.metadata
        )
        return event.format_sse()
        
    def _create_error_event(self, task_id: str, code: int, message: str, details: Any = None) -> str:
        """Create a formatted SSE error event."""
        error_data = {
            "code": code,
            "message": message
        }
        
        if details:
            error_data["data"] = {"details": details}
            
        event = TaskErrorEvent(
            id=task_id,
            error=error_data
        )
        return event.format_sse()
        
    def _create_keep_alive_event(self) -> str:
        """Create a formatted SSE keep-alive event."""
        event = SSEKeepAliveEvent(timestamp=datetime.utcnow().isoformat())
        return event.format_sse()

    async def send_task_streaming(self, request: TaskRequest) -> StreamingResponse:
        """
        Create and process a new task with streaming updates.
        If DEMO_MODE is active, returns a demo JSON after 10 seconds.
        """
        if os.environ.get("DEMO_MODE", "false").lower() == "true":
            demo_path = os.path.join(os.path.dirname(__file__), "demo_response.json")
            with open(demo_path, "r") as f:
                demo_json = json.load(f)
            async def demo_stream():
                await asyncio.sleep(3)
                yield f"event: completion\ndata: {json.dumps(demo_json)}\n\n"
            return StreamingResponse(
                demo_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        try:
            task = await self.send_task(
                title=request.title,
                tags=request.tags,
                idea=request.idea,
                lyrics=request.lyrics,
                duration=request.duration,
                sessionId=request.sessionId
            )
            
            async def event_stream():
                """Generate SSE events for task updates."""
                try:
                    # Initial status update
                    yield self._create_status_update_event(task)
                    
                    last_state = task.status.state
                    had_error = False
                    sent_final_update = False
                    
                    # Keep track of last activity time for keep-alive messages
                    last_activity = time.time()
                    
                    while True:
                        current_time = time.time()
                        current_task = self.tasks.get(task.id)
                        
                        if not current_task:
                            # Task not found, send error and break
                            yield self._create_error_event(
                                task_id=task.id, 
                                code=-32000, 
                                message="Task not found",
                                details="Task may have been deleted"
                            )
                            break
                        
                        # Send a keep-alive comment every 15 seconds if no other activity
                        if current_time - last_activity > 15:
                            yield self._create_keep_alive_event()
                            last_activity = current_time
                            continue
                        
                        # Check for state changes
                        current_state = current_task.status.state
                        state_changed = current_state != last_state
                        
                        if state_changed:
                            # State changed, send a status update
                            last_state = current_state
                            last_activity = current_time
                            
                            # Check if task failed
                            if current_state == TaskState.FAILED:
                                # Send error event for failed tasks
                                error_message = "Task processing failed"
                                if current_task.status.message and current_task.status.message.parts:
                                    for part in current_task.status.message.parts:
                                        if hasattr(part, 'text'):
                                            error_message = part.text
                                            break
                                
                                yield self._create_error_event(
                                    task_id=task.id,
                                    code=-32500,
                                    message=error_message
                                )
                                had_error = True
                                break
                            
                            # For completed states, only send the update if we have the artifacts
                            # Otherwise, wait for the artifacts to be available
                            if current_state == TaskState.COMPLETED and not current_task.artifacts:
                                # Do not send the update until we have the artifacts
                                pass
                            elif current_state == TaskState.CANCELLED:
                                # For cancelled states, send the final status update immediately
                                yield self._create_status_update_event(current_task, final=True)
                                sent_final_update = True
                                break
                            elif current_state != TaskState.COMPLETED:
                                # For other states that are not completed, send the normal update
                                yield self._create_status_update_event(current_task, final=False)
                        
                        # If the state is completed and we have artifacts, first send an artifact event
                        # followed by the final status_update with the artifacts included
                        if current_state == TaskState.COMPLETED and current_task.artifacts and not sent_final_update:
                            # First send the artifact as a separate event
                            yield self._create_artifact_event(current_task)
                            
                            # Then send the final status with the artifacts included
                            yield self._create_status_update_event(current_task, final=True)
                            
                            sent_final_update = True
                            last_activity = current_time
                            break
                        
                        # Wait before checking again
                        await asyncio.sleep(0.5)
                except Exception as e:
                    # Capture errors during streaming and send as A2A error event
                    error_message = f"Error during streaming: {str(e)}"
                    logger.log_script_generation(
                        task_id=task.id if task else "unknown",
                        status="streaming_error",
                        metadata={"error": error_message}
                    )
                    yield self._create_error_event(
                        task_id=task.id if task else "unknown",
                        code=-32000,
                        message=error_message
                    )
                
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable proxy buffering
                }
            )
            
        except Exception as e:
            # Capture errors during task creation
            error_message = f"Error creating task: {str(e)}"
            logger.log_script_generation(
                task_id="streaming_error",
                status="task_creation_failed",
                metadata={"error": error_message}
            )
            
            # Create a stream that only sends the error message and ends
            async def error_stream():
                yield self._create_error_event(
                    task_id="error",
                    code=-32500,
                    message=error_message
                )
            
            return StreamingResponse(
                error_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

def process_scene(scene_data: Dict[str, Any]) -> ExtractedScene:
    """Process raw scene data into an ExtractedScene object"""
    return ExtractedScene(
        # ... scene processing logic ...
    )

# Create singleton instance
controller = A2AController()

router = APIRouter()

@router.post("/tasks/send")
async def send_task_rpc(request: Request):
    """
    Endpoint compatible with A2A JSON-RPC 2.0 for sending tasks.
    Only accepts requests strictly following the A2A protocol.
    """
    body = await request.json()
    # Validate JSON-RPC 2.0 structure
    if (
        not isinstance(body, dict)
        or body.get("jsonrpc") != "2.0"
        or body.get("method") != "tasks/send"
        or "params" not in body
    ):
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC 2.0 request for A2A protocol.")
    params = body["params"]

    # Required fields
    task_id = params.get("id")
    session_id = params.get("sessionId")
    message = params.get("message")
    metadata = params.get("metadata", {})
    if not task_id or not message or "role" not in message or "parts" not in message:
        raise HTTPException(status_code=400, detail="Missing required A2A fields in params.")

    # Extract text part (A2A allows multiple parts, but we expect at least one text part)
    text_part = next((p for p in message["parts"] if p.get("type") == "text"), None)
    if not text_part:
        raise HTTPException(status_code=400, detail="At least one text part required in message.parts.")

    title = metadata.get("title")
    tags = metadata.get("tags")
    idea = metadata.get("idea")
    lyrics = metadata.get("lyrics")
    duration = metadata.get("duration")

    if not title or not tags or not idea:
        raise HTTPException(status_code=400, detail="Missing required movie script parameters in metadata (title, tags, idea).")
    # Build TaskRequest
    task_request = TaskRequest(
        title=title,
        tags=tags,
        idea=idea,
        lyrics=lyrics,
        duration=duration,
        sessionId=session_id
    )
    # Use the existing controller logic
    task = await controller.send_task(
        title=title,
        tags=tags,
        idea=idea,
        lyrics=lyrics,
        duration=duration,
        sessionId=session_id
    )
    return task 