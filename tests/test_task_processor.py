"""
Unit tests for the TaskProcessor class
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import json
import asyncio
import logging
from src.core.task_processor import TaskProcessor
from src.models.task import Task, TaskStatus, Message, Artifact, TextPart, TaskState
from src.models.a2a import PushNotificationConfig
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def task_processor():
    """
    Create a TaskProcessor instance with mocked ScriptService
    
    @returns {TaskProcessor} A TaskProcessor instance with mocked ScriptService
    """
    with patch('src.core.task_processor.ScriptService') as mock_script_service:
        processor = TaskProcessor()
        # Mock the script service methods
        processor._script_service.generate_script = AsyncMock()
        yield processor

def create_test_task():
    """
    Creates a test task with proper metadata configuration
    
    @returns {Task} A configured test task instance
    """
    task_metadata = {
        "title": "Test Script",
        "genre": "test",
        "tone": "neutral",
        "length": "short",
        "tags": ["test"]
    }
    
    message_metadata = {
        "data": {
            "genre": "test",
            "tone": "neutral",
            "length": "short"
        }
    }
    
    return Task(
        id=str(uuid.uuid4()),
        sessionId=str(uuid.uuid4()),
        status=TaskStatus(
            state=TaskState.SUBMITTED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Generate a test script",
                        metadata=message_metadata
                    )
                ]
            )
        ),
        metadata=task_metadata,
        artifacts=[]
    )

@pytest.mark.asyncio
async def test_create_task(task_processor):
    """
    Test creating a new task
    
    @param {TaskProcessor} task_processor - The mocked task processor instance
    """
    task_params = {
        "id": "test-task",
        "sessionId": "test-session",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Test prompt"}]
        },
        "metadata": {
            "title": "Test Movie",
            "tags": ["test"],
            "idea": "A test movie",
            "lyrics": None,
            "duration": 60
        }
    }
    
    task = await task_processor.create_task(task_params)
    
    assert task.id == task_params["id"]
    assert task.sessionId == task_params["sessionId"]
    assert task.metadata["title"] == task_params["metadata"]["title"]
    assert task.metadata["tags"] == task_params["metadata"]["tags"]
    assert task.metadata["idea"] == task_params["metadata"]["idea"]
    assert task.metadata["lyrics"] == task_params["metadata"]["lyrics"]
    assert task.metadata["duration"] == task_params["metadata"]["duration"]
    assert task.status.state == TaskState.SUBMITTED
    assert task.id in task_processor._tasks
    assert task.id in task_processor._task_updates
    assert isinstance(task_processor._task_updates[task.id], asyncio.Queue)

@pytest.mark.asyncio
async def test_process_task_script_generation(task_processor):
    """
    Tests the processing of a script generation task
    
    @param {TaskProcessor} task_processor - The task processor fixture
    """
    try:
        # Mock script service response
        script_content = "Test script content"
        thoughts = [
            {"type": "outline", "content": "Test outline"},
            {"type": "completion", "content": "Script generated successfully"}
        ]
        
        task_processor._script_service.generate_script.return_value = (script_content, thoughts)
        
        # Create and store test task
        task = create_test_task()
        task_processor._tasks[task.id] = task
        task_processor._task_updates[task.id] = asyncio.Queue()
        
        # Start task processing
        process_task = asyncio.create_task(
            task_processor.process_task_async(task.id)
        )
        
        # Collect updates until task is done
        updates = []
        try:
            while True:
                update = await asyncio.wait_for(
                    task_processor._task_updates[task.id].get(),
                    timeout=1
                )
                updates.append(update)
                if update.status.state in [TaskState.COMPLETED, TaskState.FAILED]:
                    break
        except asyncio.TimeoutError:
            logging.error("Timeout waiting for task updates")
            if process_task.done():
                exc = process_task.exception()
                if exc:
                    logging.error(f"Task failed with error: {exc}")
            raise
            
        # Verify updates were received
        assert len(updates) > 0, "No updates received"
        
        # Get final task state
        final_update = updates[-1]
        assert final_update.status.state == TaskState.COMPLETED
        
        # Verify script artifacts
        task = task_processor._tasks[task.id]
        assert len(task.artifacts) == 3, "Expected outline, script and thoughts artifacts"
        
        # Verify outline artifact
        outline_artifact = next((a for a in task.artifacts if a.name == "outline"), None)
        assert outline_artifact is not None
        assert outline_artifact.description == "Script outline"
        assert outline_artifact.parts[0].text == "Test outline"
        
        # Verify script artifact
        script_artifact = next((a for a in task.artifacts if a.name == "script"), None)
        assert script_artifact is not None
        assert script_artifact.description == "Generated script"
        assert script_artifact.parts[0].text == "Test script content"
        
        # Verify thoughts artifact
        thoughts_artifact = next((a for a in task.artifacts if a.name == "thoughts"), None)
        assert thoughts_artifact is not None
        assert thoughts_artifact.description == "Processing thoughts and insights"
        
        # Verify script service was called with correct metadata
        script_service_call = task_processor._script_service.generate_script.call_args
        assert script_service_call is not None
        prompt_arg, metadata_arg = script_service_call[0]
        assert prompt_arg == task.status.message.parts[0].text
        assert metadata_arg == task.status.message.parts[0].metadata["data"]
        
    finally:
        if 'process_task' in locals():
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass

@pytest.mark.asyncio
async def test_process_task_error(task_processor):
    """
    Test processing a task that results in error
    
    @param {TaskProcessor} task_processor - The mocked task processor instance
    """
    logger.info("Starting error test")
    process_task = None
    
    try:
        # Mock script service error
        error_message = "Service error"
        task_processor._script_service.generate_script.side_effect = Exception(error_message)
        logger.debug("Mocked service error")
        
        # Create and store test task
        task = create_test_task()
        original_message = task.status.message
        task_processor._tasks[task.id] = task
        task_processor._task_updates[task.id] = asyncio.Queue()
        logger.debug("Created test task")
        
        # Start task processing
        logger.info("Starting task processing")
        process_task = asyncio.create_task(task_processor.process_task_async(task.id))
        logger.debug("Task processing started")
        
        # Get all updates until we see FAILED
        updates = []
        try:
            while True:
                update = await asyncio.wait_for(task_processor._task_updates[task.id].get(), timeout=2.0)
                logger.info(f"Received update with state: {update.status.state}")
                updates.append(update)
                if update.status.state == TaskState.FAILED:
                    break
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for updates")
            if process_task.done():
                exc = process_task.exception()
                if exc:
                    logging.error(f"Task failed with error: {exc}")
            raise
        
        # Verify we got at least one update and it's FAILED
        assert len(updates) > 0, "No updates received"
        final_update = updates[-1]
        assert final_update.status.state == TaskState.FAILED
        
        # Verify error message
        assert final_update.status.message is not None
        assert final_update.status.message.role == "agent"
        assert len(final_update.status.message.parts) == 1
        error_part = final_update.status.message.parts[0]
        assert isinstance(error_part, TextPart)
        assert error_part.type == "text"
        assert error_message in error_part.text
        logger.info("Verified FAILED state")
        
        # Verify script service was called with correct metadata from original message
        script_service_call = task_processor._script_service.generate_script.call_args
        assert script_service_call is not None
        prompt_arg, metadata_arg = script_service_call[0]
        assert prompt_arg == original_message.parts[0].text
        assert metadata_arg == original_message.parts[0].metadata["data"]
        
    finally:
        if process_task and not process_task.done():
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass

@pytest.mark.asyncio
async def test_get_task_updates(task_processor):
    """
    Test getting task updates via streaming
    """
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    task_processor._task_updates[task.id] = asyncio.Queue()
    
    # Add a single COMPLETED update to queue
    update = task.copy()
    update.status.state = TaskState.COMPLETED
    await task_processor._task_updates[task.id].put(update)
    
    # Close the queue to signal no more updates
    task_processor._task_updates[task.id].task_done()
    
    # Get updates
    updates = []
    async for update in task_processor.get_task_updates(task.id):
        updates.append(update)
        if update.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
            break
    
    # Verify we got exactly one COMPLETED update
    assert len(updates) == 1, f"Expected 1 update but got {len(updates)}"
    assert updates[0].status.state == TaskState.COMPLETED

@pytest.mark.asyncio
async def test_cancel_task(task_processor):
    """
    Test canceling a task
    """
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    task_processor._task_updates[task.id] = asyncio.Queue()
    
    # Cancel task
    cancelled_task = await task_processor.cancel_task(task.id)
    
    # Verify task state
    assert cancelled_task.status.state == TaskState.CANCELLED
    assert cancelled_task.id == task.id
    
    # Verify update was sent
    update = await task_processor._task_updates[task.id].get()
    assert update.status.state == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_nonexistent_task(task_processor):
    """
    Test canceling a task that doesn't exist
    """
    with pytest.raises(ValueError) as exc_info:
        await task_processor.cancel_task("nonexistent-task")
    assert "Task nonexistent-task not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_task(task_processor):
    """
    Test retrieving a task
    """
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    
    # Get task
    retrieved_task = await task_processor.get_task(task.id)
    
    # Verify
    assert retrieved_task.id == task.id
    assert retrieved_task.sessionId == task.sessionId

@pytest.mark.asyncio
async def test_get_nonexistent_task(task_processor):
    """
    Test retrieving a task that doesn't exist
    """
    with pytest.raises(ValueError) as exc_info:
        await task_processor.get_task("nonexistent-task")
    assert "Task nonexistent-task not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_set_push_notification(task_processor):
    """
    Test setting push notification configuration
    """
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    
    # Set push notification config
    config = PushNotificationConfig(
        url="https://test.com/webhook",
        events=["status", "artifact"]
    )
    result = await task_processor.set_push_notification(task.id, config)
    
    # Verify
    assert result == config
    assert task_processor._push_configs[task.id] == config

@pytest.mark.asyncio
async def test_set_push_notification_nonexistent_task(task_processor):
    """
    Test setting push notification for non-existent task
    """
    config = PushNotificationConfig(
        url="https://test.com/webhook",
        events=["status", "artifact"]
    )
    with pytest.raises(ValueError) as exc_info:
        await task_processor.set_push_notification("nonexistent-task", config)
    assert "Task nonexistent-task not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_push_notification(task_processor):
    """
    Test getting push notification configuration
    """
    # Create and store test task and config
    task = create_test_task()
    task_processor._tasks[task.id] = task
    config = PushNotificationConfig(
        url="https://test.com/webhook",
        events=["status", "artifact"]
    )
    task_processor._push_configs[task.id] = config
    
    # Get config
    result = await task_processor.get_push_notification(task.id)
    
    # Verify
    assert result == config

@pytest.mark.asyncio
async def test_get_push_notification_nonexistent(task_processor):
    """
    Test getting push notification for non-existent task
    """
    result = await task_processor.get_push_notification("nonexistent-task")
    assert result is None

def test_get_session_tasks(task_processor):
    """
    Test retrieving tasks for a session
    
    @param {TaskProcessor} task_processor - The task processor instance
    """
    # Create session ID
    session_id = str(uuid.uuid4())
    
    # Create multiple tasks with same session ID
    tasks = []
    for _ in range(2):
        task = create_test_task()
        task.sessionId = session_id
        tasks.append(task)
    
    # Create a task with different session ID
    other_task = create_test_task()
    tasks.append(other_task)
    
    # Store tasks and session info
    task_processor._active_sessions[session_id] = [t.id for t in tasks[:2]]
    for task in tasks:
        task_processor._tasks[task.id] = task
    
    # Get session tasks
    session_tasks = task_processor.get_session_tasks(session_id)
    
    # Verify
    assert len(session_tasks) == 2
    assert all(task.sessionId == session_id for task in session_tasks)
    assert other_task.id not in [task.id for task in session_tasks] 