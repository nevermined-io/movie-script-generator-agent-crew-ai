"""
FastAPI routes for A2A protocol integration.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from src.models.a2a import Task
from src.models.agent_card import AGENT_CARD
from src.controllers.a2a_controller import A2AController

# Create router
router = APIRouter(prefix="/a2a/v1", tags=["A2A Protocol"])

# Initialize controller
controller = A2AController()

@router.get("/agent-card")
async def get_agent_card():
    """
    Get the agent card describing capabilities and parameters.
    
    Returns:
        AgentCard: The agent's capabilities and metadata
    """
    return AGENT_CARD

@router.post("/tasks", response_model=Task)
async def create_task(
    input_data: Dict,
    background_tasks: BackgroundTasks
):
    """
    Create a new script generation task.
    
    Args:
        input_data: Dictionary containing task parameters
        background_tasks: FastAPI background tasks handler
        
    Returns:
        Task: The created task with initial status
    """
    # Create task
    task = controller.create_task(input_data)
    
    # Process task in background if not failed
    if task.status.state != "failed":
        background_tasks.add_task(controller.process_task, task)
    
    return task

@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """
    Get the status and results of a specific task.
    
    Args:
        task_id: ID of the task to retrieve
        
    Returns:
        Task: The task with current status and artifacts if completed
        
    Raises:
        HTTPException: If task is not found
    """
    task = controller.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    return task

@router.get("/tasks", response_model=List[Task])
async def list_tasks(
    session_id: Optional[str] = None,
    state: Optional[str] = None
):
    """
    List all tasks, optionally filtered by session ID and state.
    
    Args:
        session_id: Optional session ID to filter by
        state: Optional task state to filter by
        
    Returns:
        List[Task]: List of matching tasks
    """
    tasks = list(controller.tasks.values())
    
    # Filter by session ID if provided
    if session_id:
        tasks = [t for t in tasks if t.sessionId == session_id]
        
    # Filter by state if provided
    if state:
        tasks = [t for t in tasks if t.status.state == state]
        
    return tasks 