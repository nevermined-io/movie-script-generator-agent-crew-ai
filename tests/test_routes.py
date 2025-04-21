"""
Tests for the API routes.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from fastapi import status
from src.api.models import ScriptRequest
from src.models.task import TaskState, TaskStatus, Message, TextPart, Task
from src.core.task_processor import TaskProcessor
from src.server import app, get_task_processor
from src.models.a2a import TaskSendParams, PushNotificationConfig
from datetime import datetime
import json
import httpx
import asyncio
import sys
from fastapi.testclient import TestClient

# Mock test data
MOCK_SCRIPT_RESULT = {
    "script": "Test script content",
    "scenes": [{
        "technical_details": {
            "shot_type": "wide",
            "camera_movement": "static",
            "camera_equipment": "test camera",
            "location": "test location",
            "lighting_setup": {},
            "color_palette": [],
            "visual_references": [],
            "character_actions": {},
            "transition_type": "cut",
            "special_notes": []
        }
    }],
    "transformedScenes": [{
        "description": "Test scene",
        "prompt": "Test prompt",
        "characters_in_scene": [],
        "setting_id": "test_setting",
        "duration": 60,
        "technical_details": {}
    }],
    "characters": []
}

class MockScriptService:
    """Mock class for ScriptService"""
    async def generate_script(self, prompt: str, metadata: dict = None) -> tuple:
        return "Test script content", [
            {"type": "outline", "content": "Test outline"},
            {"type": "completion", "content": "Script generated successfully"}
        ]

class MockLogger:
    """Mock class for logger"""
    def log_script_generation(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

class MockTaskProcessor(TaskProcessor):
    """Mock class for TaskProcessor with overridden async methods"""
    async def create_task(self, task_params: dict) -> Task:
        # Validate required fields using TaskSendParams
        params = TaskSendParams(**task_params)
        
        task = Task(
            id="test-123",
            sessionId=params.sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Starting script generation...")]
                )
            ),
            metadata=params.metadata
        )
        self._tasks[task.id] = task
        return task

    async def process_task_async(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.status.state = TaskState.COMPLETED
            task.status.message.parts[0].text = "Script generated successfully"
            if task_id in self._task_updates:
                await self._task_updates[task_id].put(task)

    async def get_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task

    async def cancel_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.status.state = TaskState.CANCELED
        return task

    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> PushNotificationConfig:
        self._push_configs[task_id] = config
        return config

    async def get_push_notification(self, task_id: str) -> PushNotificationConfig:
        config = self._push_configs.get(task_id)
        if not config:
            raise ValueError(f"No push notification config found for task {task_id}")
        return config

@pytest.fixture(autouse=True)
def mock_all_dependencies():
    """
    Mock all external dependencies to completely avoid real calls
    """
    # Create patches for all dependencies
    patches = [
        patch('src.core.script_service.ScriptService', MockScriptService),
        patch('src.utils.logger.logger', MockLogger()),
        patch('src.core.generator.logger', MockLogger()),
        patch('openai.AsyncOpenAI', MagicMock()),
        patch.dict(sys.modules, {
            'openai': MagicMock(),
            'crewai': MagicMock(),
            'crewai.Agent': MagicMock(),
            'crewai.Crew': MagicMock(),
            'crewai.tasks': MagicMock(),
            'langchain': MagicMock(),
            'langchain.chat_models': MagicMock(),
            'langchain.tools': MagicMock()
        })
    ]
    
    # Apply all patches
    for p in patches:
        p.start()
    
    yield
    
    # Stop all patches
    for p in patches:
        p.stop()

@pytest.fixture
def task_processor():
    """
    Get a TaskProcessor instance with mocked dependencies
    """
    return MockTaskProcessor()

@pytest.fixture
def test_client(mock_all_dependencies, task_processor):
    """
    Create a test client with all dependencies properly mocked
    """
    app.dependency_overrides[get_task_processor] = lambda: task_processor
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

def test_generate_script_success(test_client, task_processor):
    """
    Test successful script generation
    """
    request_data = {
        "message": {
            "role": "user",
            "parts": [{
                "type": "text",
                "text": "Generate a test script"
            }]
        },
        "sessionId": "test-session",
        "metadata": {
            "title": "Test Script",
            "tags": ["test"],
            "idea": "A test script about testing",
            "lyrics": None,
            "duration": 120
        }
    }

    response = test_client.post("/tasks/send", json=request_data)
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] is not None
    assert result["sessionId"] == "test-session"
    assert result["status"]["state"] == TaskState.SUBMITTED.value
    assert result["status"]["message"]["role"] == "assistant"
    assert len(result["status"]["message"]["parts"]) == 1
    assert result["status"]["message"]["parts"][0]["type"] == "text"
    assert result["status"]["message"]["parts"][0]["text"] == "Starting script generation..."
    assert result["metadata"]["title"] == "Test Script"
    assert result["metadata"]["tags"] == ["test"]
    assert result["metadata"]["idea"] == "A test script about testing"
    assert result["metadata"]["duration"] == 120

def test_generate_script_validation_error(test_client):
    """
    Test script generation with invalid request data
    """
    # Enviar datos que no coinciden con el formato esperado
    response = test_client.post("/tasks/send", json={
        "message": "not_a_message_object",  # debe ser un objeto con role y parts
        "metadata": "not_a_metadata_object"  # debe ser un objeto con los campos requeridos
    })
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    error_detail = response.json()["detail"]
    assert "validation errors for TaskSendParams" in error_detail
    assert "Input should be a valid dictionary" in error_detail
    assert "message" in error_detail
    assert "metadata" in error_detail

def test_get_task_success(test_client, task_processor):
    """
    Test successful task retrieval
    """
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        sessionId="test-session",
        status=TaskStatus(
            state=TaskState.COMPLETED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Test message")]
            )
        ),
        metadata={
            "title": "Test Script",
            "tags": ["test"],
            "idea": "Test idea",
            "lyrics": None,
            "duration": 120
        }
    )
    task_processor._tasks[task_id] = test_task

    response = test_client.get(f"/tasks/{task_id}")

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] == task_id
    assert result["sessionId"] == "test-session"
    assert result["status"]["state"] == TaskState.COMPLETED.value
    assert result["metadata"]["title"] == "Test Script"

def test_get_task_not_found(test_client):
    """
    Test task retrieval for non-existent task
    """
    response = test_client.get("/tasks/non-existent")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_cancel_task_success(test_client, task_processor):
    """
    Test successful task cancellation
    """
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        sessionId="test-session",
        status=TaskStatus(
            state=TaskState.WORKING,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Working...")]
            )
        ),
        metadata={
            "title": "Test Script",
            "genre": "test",
            "tone": "neutral",
            "length": "short",
            "tags": ["test"]
        }
    )
    task_processor._tasks[task_id] = test_task

    response = test_client.post(f"/tasks/{task_id}/cancel")

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] == task_id
    assert result["status"]["state"] == TaskState.CANCELED.value

def test_cancel_task_not_found(test_client):
    """
    Test task cancellation for non-existent task
    """
    response = test_client.post("/tasks/non-existent/cancel")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_set_push_notification(test_client, task_processor):
    """
    Test setting push notification configuration
    """
    task_id = "test-123"
    config = {
        "url": "https://test.com/webhook",
        "events": ["task.completed", "task.failed"],
        "headers": {"Authorization": "Bearer test"}
    }
    
    response = test_client.post(f"/tasks/{task_id}/pushNotification", json=config)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["url"] == config["url"]
    assert result["events"] == config["events"]
    assert result["headers"] == config["headers"]

def test_get_push_notification(test_client, task_processor):
    """
    Test getting push notification configuration
    """
    task_id = "test-123"
    config = PushNotificationConfig(
        url="https://test.com/webhook",
        events=["task.completed", "task.failed"],
        headers={"Authorization": "Bearer test"}
    )
    task_processor._push_configs[task_id] = config
    
    response = test_client.get(f"/tasks/{task_id}/pushNotification")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["url"] == config.url
    assert result["events"] == config.events
    assert result["headers"] == config.headers

@pytest.mark.asyncio
async def test_send_task_streaming_success(test_client, task_processor):
    """
    Test successful task streaming
    """
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        sessionId="test-session",
        status=TaskStatus(
            state=TaskState.WORKING,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Working...")]
            )
        ),
        metadata={
            "title": "Test Script",
            "tags": ["test"],
            "idea": "Test idea",
            "lyrics": None,
            "duration": 120
        }
    )
    task_processor._tasks[task_id] = test_task
    task_processor._task_updates[task_id] = asyncio.Queue()
    await task_processor._task_updates[task_id].put(test_task)
    
    request_data = {
        "title": "Test Script",
        "tags": ["test"],
        "idea": "A test script about testing",
        "lyrics": None,
        "duration": 120,
        "sessionId": "test-session"
    }
    
    async with httpx.AsyncClient(app=test_client.app, base_url="http://test") as ac:
        async with ac.stream("POST", "/tasks/sendSubscribe", json=request_data) as response:
            assert response.status_code == status.HTTP_200_OK
            
            received_updates = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    received_updates.append(data)
                    if data["status"]["state"] == TaskState.COMPLETED.value:
                        break

            assert len(received_updates) > 0

@pytest.mark.asyncio
async def test_send_task_streaming_error(test_client, task_processor):
    """
    Test streaming error handling
    """
    task_id = "test-123"
    error_task = Task(
        id=task_id,
        sessionId="test-session",
        status=TaskStatus(
            state=TaskState.FAILED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Failed to generate script: Invalid parameters provided")]
            )
        ),
        metadata={
            "title": "Test Script",
            "tags": ["test"],
            "idea": "Test idea",
            "error": "Invalid parameters provided"
        }
    )
    task_processor._tasks[task_id] = error_task
    task_processor._task_updates[task_id] = asyncio.Queue()
    await task_processor._task_updates[task_id].put(error_task)
    
    request_data = {
        "title": "Test Script",
        "tags": ["test"],
        "idea": "A test script about testing",
        "lyrics": None,
        "duration": 120,
        "sessionId": "test-session"
    }
    
    async with httpx.AsyncClient(app=test_client.app, base_url="http://test") as ac:
        async with ac.stream("POST", "/tasks/sendSubscribe", json=request_data) as response:
            assert response.status_code == status.HTTP_200_OK
            
            received_updates = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    received_updates.append(data)
                    if data["status"]["state"] == TaskState.FAILED.value:
                        break

            assert len(received_updates) == 1
            assert received_updates[0]["status"]["state"] == TaskState.FAILED.value
            assert "Failed to generate script" in received_updates[0]["status"]["message"]["parts"][0]["text"]