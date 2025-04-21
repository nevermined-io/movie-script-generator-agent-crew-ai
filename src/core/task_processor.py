"""
Task processor implementation for the Movie Script Generator Agent
"""
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from datetime import datetime
import asyncio
import json
import uuid
import httpx
from .script_service import ScriptService
from ..models.task import Task, TaskStatus, Message, Artifact, Part, TextPart, TaskState
from ..models.a2a import TaskSendParams, PushNotificationConfig

class TaskProcessor:
    """
    Handles the processing of movie script generation tasks
    """
    
    def __init__(self):
        """
        Initialize the task processor
        """
        self._tasks: Dict[str, Task] = {}
        self._active_sessions: Dict[str, List[str]] = {}
        self._script_service = ScriptService()
        self._push_configs: Dict[str, PushNotificationConfig] = {}
        self._task_updates: Dict[str, asyncio.Queue] = {}
    
    async def create_task(self, task_params: Union[Dict[str, Any], Task]) -> Task:
        """
        Create a new task in SUBMITTED state
        
        Args:
            task_params: Dictionary containing task parameters or Task object
            
        Returns:
            Task: Created task in SUBMITTED state
        """
        # Create task object
        if isinstance(task_params, Task):
            task = task_params
        else:
            params = TaskSendParams(**task_params)
            task = Task.from_params(params)
        
        # Set initial state
        task.status = TaskStatus(
            state=TaskState.SUBMITTED,
            timestamp=datetime.utcnow().isoformat(),
            message=task.status.message
        )
        
        # Store task
        self._tasks[task.id] = task
        
        # Create update queue
        self._task_updates[task.id] = asyncio.Queue()
        
        # Add to session if exists
        if task.sessionId:
            if task.sessionId not in self._active_sessions:
                self._active_sessions[task.sessionId] = []
            self._active_sessions[task.sessionId].append(task.id)
        
        return task
    
    async def process_task_async(self, task_id: str):
        """
        Process a task asynchronously
        
        Args:
            task_id: ID of the task to process
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        
        try:
            # Update status to working
            task.status = TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=task.status.message
            )
            await self._notify_update(task)
            
            # Process the message
            message = task.status.message
            if not message or not message.parts:
                raise ValueError("No message content provided")
            
            # Extract text and metadata
            text_content = ""
            metadata = {}
            for part in message.parts:
                if isinstance(part, TextPart):
                    text_content += part.text or ""
                    if part.metadata and isinstance(part.metadata, dict):
                        metadata.update(part.metadata.get("data", {}))
            
            if not text_content:
                raise ValueError("No text content found in message")
            
            # Determine task type
            task_type = metadata.get("skill_id", "script-generation")
            
            # Process based on task type
            if task_type == "script-generation":
                script, thoughts = await self._script_service.generate_script(text_content, metadata)
                
                # Create outline artifact
                outline_artifact = Artifact(
                    name="outline",
                    description="Script outline",
                    parts=[TextPart(type="text", text=thoughts[0]["content"])]
                )
                task.artifacts = [outline_artifact]
                await self._notify_update(task)
                
                # Create script artifact
                script_artifact = Artifact(
                    name="script",
                    description="Generated script",
                    parts=[TextPart(type="text", text=script)]
                )
                artifacts = [outline_artifact, script_artifact]
            
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Add thoughts artifact
            thoughts_artifact = Artifact(
                name="thoughts",
                description="Processing thoughts and insights",
                parts=[TextPart(type="text", text=json.dumps(thoughts, indent=2))]
            )
            artifacts.append(thoughts_artifact)
            
            # Update task with completion
            task.status = TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=task.status.message
            )
            task.artifacts = artifacts
            await self._notify_update(task)
            
        except Exception as e:
            # Handle errors
            error_msg = Message(
                role="agent",
                parts=[TextPart(type="text", text=str(e))]
            )
            task.status = TaskStatus(
                state=TaskState.FAILED,
                timestamp=datetime.utcnow().isoformat(),
                message=error_msg
            )
            await self._notify_update(task)
    
    async def get_task_updates(self, task_id: str) -> AsyncGenerator[Task, None]:
        """
        Get updates for a task via streaming
        
        Args:
            task_id: ID of the task to get updates for
            
        Yields:
            Task: Task updates
        """
        if task_id not in self._task_updates:
            raise ValueError(f"Task {task_id} not found")
            
        queue = self._task_updates[task_id]
        while True:
            try:
                update = await queue.get()
                yield update
                if update.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
                    break
            except asyncio.CancelledError:
                break
    
    async def _notify_update(self, task: Task):
        """
        Notify task update to subscribers and push notification endpoints
        
        Args:
            task: Updated task
        """
        # Add to update queue
        if task.id in self._task_updates:
            await self._task_updates[task.id].put(task)
        
        # Send push notification if configured
        if task.id in self._push_configs:
            config = self._push_configs[task.id]
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        config.url,
                        json=task.to_dict(),
                        headers=config.headers or {}
                    )
            except Exception as e:
                # Log error but don't fail the task
                print(f"Failed to send push notification: {e}")
    
    async def cancel_task(self, task_id: str) -> Task:
        """
        Cancel a task in progress
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus(
            state=TaskState.CANCELED,
            timestamp=datetime.utcnow().isoformat()
        )
        await self._notify_update(task)
        return task
    
    async def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task
    
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> PushNotificationConfig:
        """
        Configure push notifications for a task
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
            
        self._push_configs[task_id] = config
        return config
    
    async def get_push_notification(self, task_id: str) -> Optional[PushNotificationConfig]:
        """
        Get push notification configuration for a task
        """
        return self._push_configs.get(task_id)
    
    def get_session_tasks(self, session_id: str) -> List[Task]:
        """
        Get all tasks for a session
        """
        task_ids = self._active_sessions.get(session_id, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks] 