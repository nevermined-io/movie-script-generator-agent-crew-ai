"""
Tests for the API routes.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from fastapi import status, APIRouter
from src.api.models import ScriptRequest
from src.models.task import TaskState, TaskStatus, Message, TextPart, Task
from src.core.task_processor import TaskProcessor
from src.server import app, get_task_processor
from src.controllers.a2a_controller import A2AController, TaskRequest
from src.models.a2a import TaskSendParams, PushNotificationConfig
from datetime import datetime
import json
import httpx
import asyncio
import sys
from fastapi.testclient import TestClient
import uuid
import logging
from typing import List, Optional, AsyncGenerator

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

MOCK_TASK_REQUEST = {
    "id": "test-123",
    "sessionId": "session-123",
    "message": {
        "role": "user",
        "parts": [
            {
                "type": "text",
                "text": "Generate a movie script",
                "metadata": {
                    "genre": "comedy",
                    "tone": "light",
                    "length": "short"
                }
            }
        ]
    },
    "metadata": {
        "title": "Test Script",
        "genre": "comedy",
        "tone": "light",
        "length": "short",
        "tags": ["test"]
    }
}

MOCK_TASK = {
    "id": "test-task-id",
    "sessionId": None,
    "status": {
        "state": TaskState.COMPLETED,
        "timestamp": datetime.utcnow().isoformat(),
        "message": {
            "role": "assistant",
            "parts": [
                {
                    "type": "text",
                    "text": "Script generated successfully",
                    "metadata": {}
                }
            ],
            "metadata": {}
        }
    },
    "metadata": {
        "title": "Test Script",
        "tags": ["test", "movie"],
        "idea": "A test movie script",
        "duration": 120
    }
}

MOCK_INVALID_REQUEST = {
    "id": "test-task-id",
    "invalid_field": "invalid"
}

MOCK_PUSH_CONFIG = {
    "events": ["task.completed", "task.failed"],
    "url": "http://test.com/webhook"
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
    """Mock implementation of TaskProcessor for testing"""
    
    def __init__(self):
        """Initialize mock task processor"""
        self._tasks = {}
        self._push_configs = {}
        self._task_updates = {}
        self._logger = logging.getLogger("mock_task_processor")

    async def process_task(self, task_params: TaskSendParams) -> Task:
        """Mock task processing"""
        task = Task(
            id=task_params.id or str(uuid.uuid4()),
            sessionId=task_params.sessionId or str(uuid.uuid4()),
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Task submitted")]
                )
            ),
            metadata=task_params.metadata
        )
        self._tasks[task.id] = task
        self._task_updates[task.id] = asyncio.Queue()
        await self._task_updates[task.id].put(task)
        return task

    async def get_task(self, task_id: str) -> Task:
        """Mock get task"""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        return self._tasks[task_id]

    async def cancel_task(self, task_id: str) -> Task:
        """Mock task cancellation"""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        task = self._tasks[task_id]
        task.status.state = TaskState.CANCELED
        task.status.timestamp = datetime.utcnow().isoformat()
        task.status.message = Message(
            role="assistant",
            parts=[TextPart(type="text", text="Task cancelled")]
        )
        return task

    async def list_tasks(self) -> List[Task]:
        """Mock list tasks"""
        return list(self._tasks.values())

    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> PushNotificationConfig:
        """Mock set push notification"""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        self._push_configs[task_id] = config
        return config

    async def get_push_notification(self, task_id: str) -> Optional[PushNotificationConfig]:
        """Mock get push notification"""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        return self._push_configs.get(task_id)

    async def get_task_updates(self, task_id: str) -> AsyncGenerator[Task, None]:
        """Mock task updates generator"""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        queue = self._task_updates[task_id]
        while True:
            try:
                task = await queue.get()
                yield task
                if task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
                    break
            except asyncio.CancelledError:
                break

    def _create_test_task(self, task_id: str, state: TaskState = TaskState.WORKING) -> Task:
        """Helper method to create a test task"""
        task = Task(
            id=task_id,
            sessionId=str(uuid.uuid4()),
            status=TaskStatus(
                state=state,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Test task")]
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
        self._tasks[task_id] = task
        return task

@pytest.fixture(autouse=True)
def mock_all_dependencies():
    """Mock all external dependencies"""
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
    
    for p in patches:
        p.start()
    
    yield
    
    for p in patches:
        p.stop()

@pytest.fixture
def task_processor():
    """Fixture for mock task processor"""
    return MockTaskProcessor()

@pytest.fixture
def controller(task_processor):
    """Create a controller instance for testing"""
    controller = A2AController()
    controller.task_processor = task_processor
    return controller

@pytest.fixture
def test_client(controller, task_processor):
    """Fixture for test client with mocked dependencies"""
    app.dependency_overrides[get_task_processor] = lambda: task_processor
    
    # Ensure the controller's router is included in the app
    app.include_router(controller.router)
    
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_generate_script_validation_error(test_client):
    """Test script generation with invalid request"""
    # Invalid request that should fail TaskSendParams validation
    invalid_request = {
        "id": "test-123",
        "message": "not a dictionary",  # message debe ser un Dict[str, Any]
        "sessionId": 123  # sessionId debe ser un string opcional
    }
    
    # Ensure we're hitting the correct endpoint
    response = test_client.post("/tasks/send", json=invalid_request)
    
    
    # Log the response for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    
    assert response.status_code == 422
    error_detail = response.json().get("detail", [])
    assert any("message" in str(error).lower() for error in error_detail)

@pytest.mark.asyncio
async def test_generate_script_success(test_client):
    """Test successful script generation"""
    request_data = {
        "id": "test-123",
        "message": {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Generate a movie script",
                    "metadata": {
                        "genre": "comedy",
                        "tone": "light",
                        "length": "short"
                    }
                }
            ]
        },
        "sessionId": "test-session",
        "metadata": {
            "title": "Test Script",
            "tags": ["test"],
            "idea": "A test script about testing",
            "duration": 120
        }
    }
    response = test_client.post("/tasks/send", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-123"
    assert data["sessionId"] == "test-session"
    assert data["status"]["state"] == TaskState.SUBMITTED.value

@pytest.mark.asyncio
async def test_get_task_success(test_client, task_processor):
    """Test getting a task"""
    task = task_processor._create_test_task("test-123")
    response = test_client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["status"]["state"] == TaskState.WORKING.value

@pytest.mark.asyncio
async def test_get_task_not_found(test_client):
    """Test getting a non-existent task"""
    response = test_client.get("/tasks/non-existent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_cancel_task_success(test_client, task_processor):
    """Test cancelling a task"""
    task = task_processor._create_test_task("test-123")
    response = test_client.post(f"/tasks/{task.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["status"]["state"] == TaskState.CANCELED.value

@pytest.mark.asyncio
async def test_cancel_task_not_found(test_client):
    """Test cancelling a non-existent task"""
    response = test_client.post("/tasks/non-existent/cancel")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_list_tasks_success(test_client, task_processor):
    """Test listing tasks"""
    task = task_processor._create_test_task("test-123")
    response = test_client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == task.id

@pytest.mark.asyncio
async def test_set_push_notification(test_client, task_processor):
    """Test setting push notification"""
    task = task_processor._create_test_task("test-123")
    response = test_client.post(f"/tasks/{task.id}/push", json=MOCK_PUSH_CONFIG)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == MOCK_PUSH_CONFIG["url"]
    assert data["events"] == MOCK_PUSH_CONFIG["events"]

@pytest.mark.asyncio
async def test_get_push_notification(test_client, task_processor):
    """Test getting push notification"""
    task = task_processor._create_test_task("test-123")
    await task_processor.set_push_notification(task.id, PushNotificationConfig(**MOCK_PUSH_CONFIG))
    response = test_client.get(f"/tasks/{task.id}/push")
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == MOCK_PUSH_CONFIG["url"]
    assert data["events"] == MOCK_PUSH_CONFIG["events"]

@pytest.mark.asyncio
async def test_send_task_streaming_success(test_client, task_processor):
    """Test successful streaming task updates"""
    task = task_processor._create_test_task("test-123")
    with test_client.websocket_connect(f"/tasks/{task.id}/stream") as websocket:
        # Simulate task updates
        await task_processor._task_updates[task.id].put(task)
        task.status.state = TaskState.COMPLETED
        await task_processor._task_updates[task.id].put(task)
        
        # Receive updates
        data = websocket.receive_json()
        assert data["id"] == task.id
        assert data["status"]["state"] == TaskState.WORKING.value
        
        data = websocket.receive_json()
        assert data["id"] == task.id
        assert data["status"]["state"] == TaskState.COMPLETED.value

@pytest.mark.asyncio
async def test_send_task_streaming_error(test_client):
    """Test streaming updates for non-existent task"""
    with pytest.raises(WebSocketDisconnect):
        with test_client.websocket_connect("/tasks/non-existent/stream"):
            pass