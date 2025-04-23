"""
Task processor implementation for the Movie Script Generator Agent
"""
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from datetime import datetime
import asyncio
import json
import uuid
import httpx
import markdown
from .script_service import ScriptService
from ..models.task import Task, TaskStatus, Message, Artifact, Part, TextPart, TaskState
from ..models.a2a import TaskSendParams, PushNotificationConfig

class TaskProcessor:
    """
    Handles the processing of movie script generation tasks
    """
    
    # Define supported output modes
    SUPPORTED_MODES = {
        "text": "text/plain",
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json"
    }
    
    def __init__(self):
        """
        Initialize the task processor
        """
        self._tasks: Dict[str, Task] = {}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._script_service = ScriptService()
        self._push_configs: Dict[str, PushNotificationConfig] = {}
        self._task_updates: Dict[str, asyncio.Queue] = {}
    
    def _format_content(self, content: str, output_mode: str) -> str:
        """
        Format content according to the specified output mode
        
        Args:
            content: Content to format
            output_mode: Desired output format
            
        Returns:
            Formatted content
        """
        if output_mode == "text":
            return content
        elif output_mode == "markdown":
            return content  # Already in markdown format
        elif output_mode == "html":
            return markdown.markdown(content)
        elif output_mode == "json":
            return json.dumps({"content": content})
        else:
            return content  # Default to text

    def _create_part(self, content: str, output_mode: str) -> TextPart:
        """
        Create a message part with proper formatting
        
        Args:
            content: Content for the part
            output_mode: Desired output format
            
        Returns:
            TextPart with formatted content
        """
        formatted_content = self._format_content(content, output_mode)
        return TextPart(
            type="text",
            text=formatted_content,
            metadata={
                "mimeType": self.SUPPORTED_MODES[output_mode]
            }
        )

    def _create_status_update(self, state: TaskState, message_text: Optional[str] = None, output_mode: str = "text") -> TaskStatus:
        """
        Create a status update following A2A format
        
        Args:
            state: The task state
            message_text: Optional message text
            output_mode: Desired output format
            
        Returns:
            TaskStatus: Status update in A2A format
        """
        status = TaskStatus(
            state=state,
            timestamp=datetime.utcnow().isoformat()
        )
        
        if message_text:
            status.message = Message(
                role="agent",
                parts=[self._create_part(message_text, output_mode)]
            )
            
        return status

    def _get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get or create session context
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session context
        """
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = {
                "tasks": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "context": {}  # Stores session-specific data like previous scripts, characters, etc.
            }
        else:
            self._active_sessions[session_id]["last_accessed"] = datetime.utcnow().isoformat()
            
        return self._active_sessions[session_id]

    async def create_task(self, task_params: Union[Dict[str, Any], Task]) -> Task:
        """
        Create a new task in SUBMITTED state
        
        Args:
            task_params: Dictionary containing task parameters or Task object
            
        Returns:
            Task: Created task in SUBMITTED state
        """
        # Create task object and validate output modes
        if isinstance(task_params, Task):
            task = task_params
            # Ensure default output modes if none specified
            if not hasattr(task, 'acceptedOutputModes') or not task.acceptedOutputModes:
                task.acceptedOutputModes = ["text"]
        else:
            params = TaskSendParams(**task_params)
            task = Task.from_params(params)
            
        # Validate that we support at least one of the accepted modes
        supported_modes = set(self.SUPPORTED_MODES.keys())
        accepted_modes = set(task.acceptedOutputModes)
        if not supported_modes.intersection(accepted_modes):
            raise ValueError(
                f"None of the accepted output modes {accepted_modes} are supported. "
                f"Supported modes are: {supported_modes}"
            )
        
        # Use the first supported output mode from the accepted list
        output_mode = next(mode for mode in task.acceptedOutputModes if mode in supported_modes)
        
        # Set initial state following A2A format
        task.status = self._create_status_update(
            TaskState.SUBMITTED,
            "Task received and queued for processing",
            output_mode
        )
        
        # Initialize history with user message if exists
        if task.status.message:
            task.history = [task.status.message]
        else:
            task.history = []
        
        # Store task
        self._tasks[task.id] = task
        
        # Create update queue
        self._task_updates[task.id] = asyncio.Queue()
        
        # Handle session
        if task.sessionId:
            session_context = self._get_session_context(task.sessionId)
            session_context["tasks"].append(task.id)
            
            # If there are previous tasks in the session, add their artifacts as context
            previous_tasks = [self._tasks[tid] for tid in session_context["tasks"][:-1]]
            if previous_tasks:
                context_message = Message(
                    role="system",
                    parts=[self._create_part(
                        "Previous session context available",
                        output_mode
                    )]
                )
                task.history.append(context_message)
                
                # Update session context with relevant information
                for prev_task in previous_tasks:
                    if prev_task.artifacts:
                        for artifact in prev_task.artifacts:
                            if artifact.name == "script":
                                session_context["context"]["previous_script"] = artifact.parts[0].text
                            elif artifact.name == "outline":
                                session_context["context"]["previous_outline"] = artifact.parts[0].text
        
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
        
        # Get the preferred output mode
        output_mode = task.acceptedOutputModes[0]
        
        try:
            # Update to working state
            task.status = self._create_status_update(
                TaskState.WORKING,
                "Processing your request...",
                output_mode
            )
            task.history.append(task.status.message)
            await self._notify_update(task)
            
            # Get session context if available
            session_context = {}
            if task.sessionId:
                session_context = self._get_session_context(task.sessionId)["context"]
            
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
            
            # Add session context to metadata
            metadata.update(session_context)
            
            # Determine task type
            task_type = metadata.get("skill_id", "script-generation")
            
            # Process based on task type
            if task_type == "script-generation":
                script, thoughts = await self._script_service.generate_script(text_content, metadata)
                
                # Create outline artifact
                outline_message = Message(
                    role="agent",
                    parts=[self._create_part(thoughts[0]["content"], output_mode)]
                )
                task.history.append(outline_message)
                outline_artifact = Artifact(
                    name="outline",
                    description="Script outline",
                    parts=[self._create_part(thoughts[0]["content"], output_mode)]
                )
                task.artifacts = [outline_artifact]
                
                # Update status to show outline progress
                task.status = self._create_status_update(
                    TaskState.WORKING,
                    "Generated script outline, proceeding with full script...",
                    output_mode
                )
                await self._notify_update(task)
                
                # Create script artifact
                script_message = Message(
                    role="agent",
                    parts=[self._create_part(script, output_mode)]
                )
                task.history.append(script_message)
                script_artifact = Artifact(
                    name="script",
                    description="Generated script",
                    parts=[self._create_part(script, output_mode)]
                )
                artifacts = [outline_artifact, script_artifact]
                
                # Update session context with new script information
                if task.sessionId:
                    session_context = self._get_session_context(task.sessionId)
                    session_context["context"].update({
                        "previous_script": script,
                        "previous_outline": thoughts[0]["content"]
                    })
            
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Add thoughts artifact
            thoughts_json = json.dumps(thoughts, indent=2)
            thoughts_message = Message(
                role="agent",
                parts=[self._create_part(thoughts_json, "json")]  # Always JSON for thoughts
            )
            task.history.append(thoughts_message)
            thoughts_artifact = Artifact(
                name="thoughts",
                description="Processing thoughts and insights",
                parts=[self._create_part(thoughts_json, "json")]
            )
            artifacts.append(thoughts_artifact)
            
            # Update task with completion
            task.status = self._create_status_update(
                TaskState.COMPLETED,
                "Script generation completed successfully",
                output_mode
            )
            task.history.append(task.status.message)
            task.artifacts = artifacts
            await self._notify_update(task)
            
        except Exception as e:
            # Handle errors
            task.status = self._create_status_update(
                TaskState.FAILED,
                f"Error during processing: {str(e)}",
                output_mode
            )
            task.history.append(task.status.message)
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
                        headers={"Authorization": f"Bearer {config.token}"} if config.token else None
                    )
            except Exception as e:
                print(f"Failed to send push notification: {e}")
    
    async def cancel_task(self, task_id: str) -> Task:
        """
        Cancel a task in progress
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = self._create_status_update(
            TaskState.CANCELED,
            "Task canceled by user request"
        )
        task.history.append(task.status.message)
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
    
    async def get_session_tasks(self, session_id: str) -> List[Task]:
        """
        Get all tasks for a session in chronological order
        
        Args:
            session_id: Session identifier
            
        Returns:
            List[Task]: List of tasks in the session
        """
        session_context = self._get_session_context(session_id)
        return [self._tasks[tid] for tid in session_context["tasks"] if tid in self._tasks]

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get session context including metadata and task history
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session context and metadata
        """
        return self._get_session_context(session_id) 