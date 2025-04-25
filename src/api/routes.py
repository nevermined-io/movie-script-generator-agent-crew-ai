"""
FastAPI routes for the Movie Script Generator Agent.
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from src.core.generator import MovieScriptGenerator
from src.api.models import ScriptRequest, ScriptResponse
from src.models.a2a import Task, PushNotificationConfig
from src.controllers.a2a_controller import controller, TaskRequest
from src.utils.logger import logger
import json

# Create router
router = APIRouter()

# Initialize generator
generator = MovieScriptGenerator()

@router.get("/.well-known/openapi.json")
async def get_openapi_spec():
    """
    Get the OpenAPI specification for this API.
    
    @returns {object} The OpenAPI specification
    """
    with open(".well-known/openapi.json", "r") as f:
        return JSONResponse(content=json.loads(f.read()))

@router.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Get the agent card describing this agent's capabilities.
    
    @returns {object} The agent card object
    """
    return await controller.get_agent_card()

@router.post("/tasks/send", response_model=Task)
async def create_task(input_data: TaskRequest):
    """
    Create a new script generation task.
    
    @param {TaskRequest} input_data The task request data
    @returns {Task} The created task
    """
    logger.log_script_generation(
        task_id="api",
        status="task_requested",
        metadata=input_data.model_dump()
    )
    return await controller.send_task(input_data)

@router.post("/tasks/sendSubscribe")
async def send_task_streaming(request: TaskRequest):
    """
    Create and process a new task with streaming updates.
    
    @param {TaskRequest} request The task request data
    @returns {StreamingResponse} Stream of task updates
    """
    return await controller.send_task_streaming(request)

@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """
    Get the current state of a task.
    
    @param {string} task_id The task ID to look up
    @returns {Task} The task object
    @throws {404} If task not found
    """
    logger.log_script_generation(
        task_id=task_id,
        status="task_status_checked",
        metadata={}
    )
    return await controller.get_task(task_id)

@router.post("/tasks/{task_id}/cancel", response_model=Task)
async def cancel_task(task_id: str):
    """
    Cancel a task in progress.
    
    @param {string} task_id The task ID to cancel
    @returns {Task} The updated task object
    @throws {404} If task not found
    @throws {400} If task already finished
    """
    logger.log_script_generation(
        task_id=task_id,
        status="cancellation_requested",
        metadata={}
    )
    return await controller.cancel_task(task_id)

@router.get("/tasks", response_model=List[Task])
async def list_tasks(session_id: Optional[str] = None, state: Optional[str] = None):
    """
    List all tasks, optionally filtered by session ID and state.
    
    @param {string} session_id Optional session ID to filter by
    @param {string} state Optional task state to filter by
    @returns {Task[]} List of matching tasks
    """
    logger.log_script_generation(
        task_id="api",
        status="tasks_listed",
        metadata={
            "session_id": session_id,
            "state": state
        }
    )
    return await controller.list_tasks(session_id=session_id, state=state)

@router.post("/tasks/{task_id}/pushNotification", response_model=PushNotificationConfig)
async def set_push_notification(task_id: str, config: PushNotificationConfig):
    """
    Set push notification configuration for a task.
    
    @param {string} task_id The task ID
    @param {PushNotificationConfig} config The notification configuration
    @returns {PushNotificationConfig} The saved configuration
    @throws {404} If task not found
    """
    return await controller.set_push_notification(task_id, config)

@router.get("/tasks/{task_id}/pushNotification", response_model=PushNotificationConfig)
async def get_push_notification(task_id: str):
    """
    Get push notification configuration for a task.
    
    @param {string} task_id The task ID
    @returns {PushNotificationConfig} The notification configuration
    @throws {404} If task or config not found
    """
    return await controller.get_push_notification(task_id)

@router.post("/generate-script", response_model=ScriptResponse, deprecated=True)
async def generate_script(request: ScriptRequest) -> Dict[str, Any]:
    """
    Legacy endpoint for direct script generation.
    
    @deprecated Use /tasks/send instead
    @param {ScriptRequest} request The script generation parameters
    @returns {ScriptResponse} The generated script
    @throws {500} If script generation fails
    """
    logger.log_script_generation(
        task_id="legacy",
        status="direct_generation_requested",
        metadata=request.model_dump()
    )
    try:
        script = await generator.generate_script(
            title=request.title,
            tags=request.tags,
            idea=request.idea,
            lyrics=request.lyrics,
            duration=request.duration
        )
        logger.log_script_generation(
            task_id="legacy",
            status="direct_generation_completed",
            metadata=request.model_dump()
        )
        return script
    except Exception as e:
        logger.log_script_generation(
            task_id="legacy",
            status="direct_generation_failed",
            metadata=request.model_dump(),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e)) 