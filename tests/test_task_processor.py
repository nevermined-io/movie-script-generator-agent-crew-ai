"""
Unit tests for the TaskProcessor class
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import json
import asyncio
from src.core.task_processor import TaskProcessor
from src.models.task import Task, TaskStatus, Message, Artifact, TextPart, TaskState
from src.models.a2a import PushNotificationConfig

@pytest.fixture
def task_processor():
    """
    Create a TaskProcessor instance with mocked ScriptService
    """
    with patch('src.core.task_processor.ScriptService') as mock_script_service:
        processor = TaskProcessor()
        # Mock the script service methods
        processor._script_service.generate_script = AsyncMock()
        yield processor

def create_test_task(task_id: str = "test-task", session_id: str = "test-session"):
    """
    Helper function to create a test task
    """
    return Task(
        id=task_id,
        sessionId=session_id,
        status=TaskStatus(
            state=TaskState.SUBMITTED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="user",
                parts=[TextPart(type="text", text="Test prompt")]
            )
        )
    )

@pytest.mark.asyncio
async def test_create_task(task_processor):
    """
    Test creating a new task
    """
    task_params = {
        "id": "test-task",
        "sessionId": "test-session",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Test prompt"}]
        }
    }
    
    task = await task_processor.create_task(task_params)
    
    assert task.id == task_params["id"]
    assert task.sessionId == task_params["sessionId"]
    assert task.status.state == TaskState.SUBMITTED
    assert task.id in task_processor._tasks
    assert task.id in task_processor._task_updates
    assert isinstance(task_processor._task_updates[task.id], asyncio.Queue)

@pytest.mark.asyncio
async def test_process_task_script_generation(task_processor):
    """
    Test processing a script generation task
    """
    # Mock script service response
    task_processor._script_service.generate_script.return_value = (
        "Generated script",
        [
            {"type": "outline", "content": "Test outline"},
            {"type": "completion", "content": "Script generated successfully"}
        ]
    )
    
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    task_processor._task_updates[task.id] = asyncio.Queue()
    
    # Process task
    await task_processor.process_task_async(task.id)
    
    # Get all updates from queue
    updates = []
    while not task_processor._task_updates[task.id].empty():
        updates.append(await task_processor._task_updates[task.id].get())
    
    # Verify updates
    assert len(updates) == 3  # Working + Outline + Completed
    assert updates[0].status.state == TaskState.WORKING
    assert updates[1].artifacts[0].name == "outline"
    assert updates[2].status.state == TaskState.COMPLETED
    assert len(updates[2].artifacts) == 3  # outline + script + thoughts
    
    # Verify script service call
    task_processor._script_service.generate_script.assert_called_once_with(
        "Test prompt",
        {}
    )

@pytest.mark.asyncio
async def test_process_task_error(task_processor):
    """
    Test processing a task that results in error
    """
    # Mock script service error
    task_processor._script_service.generate_script.side_effect = Exception("Service error")
    
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    task_processor._task_updates[task.id] = asyncio.Queue()
    
    # Process task
    await task_processor.process_task_async(task.id)
    
    # Get all updates from queue
    updates = []
    while not task_processor._task_updates[task.id].empty():
        updates.append(await task_processor._task_updates[task.id].get())
    
    # Verify updates
    assert len(updates) == 2  # Working + Error
    assert updates[0].status.state == TaskState.WORKING
    assert updates[1].status.state == TaskState.FAILED
    assert "Service error" in updates[1].status.message.parts[0].text

@pytest.mark.asyncio
async def test_get_task_updates(task_processor):
    """
    Test getting task updates via streaming
    """
    # Create and store test task
    task = create_test_task()
    task_processor._tasks[task.id] = task
    task_processor._task_updates[task.id] = asyncio.Queue()
    
    # Add some updates to queue
    update1 = task.copy()
    update1.status.state = TaskState.WORKING
    await task_processor._task_updates[task.id].put(update1)
    
    update2 = task.copy()
    update2.status.state = TaskState.COMPLETED
    await task_processor._task_updates[task.id].put(update2)
    
    # Get updates
    updates = []
    async for update in task_processor.get_task_updates(task.id):
        updates.append(update)
    
    # Verify updates
    assert len(updates) == 2
    assert updates[0].status.state == TaskState.WORKING
    assert updates[1].status.state == TaskState.COMPLETED

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
    assert cancelled_task.status.state == TaskState.CANCELED
    assert cancelled_task.id == task.id
    
    # Verify update was sent
    update = await task_processor._task_updates[task.id].get()
    assert update.status.state == TaskState.CANCELED

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
    """
    # Create and store multiple tasks
    session_id = "test-session"
    tasks = [
        create_test_task("task-1", session_id),
        create_test_task("task-2", session_id),
        create_test_task("task-3", "other-session")
    ]
    
    # Store tasks and session info
    task_processor._active_sessions[session_id] = ["task-1", "task-2"]
    for task in tasks:
        task_processor._tasks[task.id] = task
    
    # Get session tasks
    session_tasks = task_processor.get_session_tasks(session_id)
    
    # Verify
    assert len(session_tasks) == 2
    assert all(task.sessionId == session_id for task in session_tasks)
    assert "task-3" not in [task.id for task in session_tasks] 