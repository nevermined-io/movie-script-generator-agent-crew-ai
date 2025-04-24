"""
Unit tests for the FastAPI server
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
import uuid
from datetime import datetime

from src.server import app, get_task_processor
from src.models.task import Task, TaskStatus, Message, TaskState, TextPart
from src.models.a2a import PushNotificationConfig

# Create test client
client = TestClient(app)

@pytest.fixture
def mock_task_processor():
    """
    Create a mock task processor for testing
    """
    processor = MagicMock()
    
    async def mock_create_task(task_params):
        """
        Mock implementation of create_task
        """
        return Task(
            id=task_params["id"],
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(
                        text="Task submitted",
                        type="text"
                    )]
                )
            )
        )
    
    async def mock_process_task_async(task_id):
        """
        Mock implementation of process_task_async
        """
        pass
    
    async def mock_get_task_updates(task_id):
        """
        Mock implementation of get_task_updates
        """
        # Initial working state
        yield Task(
            id=task_id,
            status=TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(
                        text="Processing task...",
                        type="text"
                    )]
                )
            )
        )
        
        # Final completed state
        yield Task(
            id=task_id,
            status=TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(
                        text="Task completed",
                        type="text"
                    )]
                )
            )
        )
    
    async def mock_get_task(task_id: str):
        if task_id == "nonexistent":
            raise ValueError("Task not found")
        return Task(
            id=task_id,
            sessionId=str(uuid.uuid4()),
            status=TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(
                        text="Task completed",
                        type="text"
                    )]
                )
            )
        )
    
    async def mock_cancel_task(task_id: str):
        return Task(
            id=task_id,
            sessionId=str(uuid.uuid4()),
            status=TaskStatus(
                state=TaskState.CANCELLED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Task cancelled")]
                )
            )
        )
    
    async def mock_set_push_notification(task_id: str, config: PushNotificationConfig):
        return config
    
    async def mock_get_push_notification(task_id: str):
        if task_id == "nonexistent":
            return None
        return PushNotificationConfig(
            url="https://test.com/webhook",
            events=["status", "artifact"]
        )
    
    processor.create_task = mock_create_task
    processor.process_task_async = mock_process_task_async
    processor.get_task_updates = mock_get_task_updates
    processor.get_task = mock_get_task
    processor.cancel_task = mock_cancel_task
    processor.set_push_notification = mock_set_push_notification
    processor.get_push_notification = mock_get_push_notification
    return processor

@pytest.fixture
def test_client(mock_task_processor):
    """
    Create a test client with mocked dependencies
    """
    app.dependency_overrides[get_task_processor] = lambda: mock_task_processor
    return TestClient(app)

def create_test_message():
    """
    Helper function to create a test message
    """
    return {
        "role": "user",
        "parts": [{
            "type": "text",
            "text": "Test message"
        }]
    }

def create_test_task_params():
    """
    Helper function to create test task parameters
    """
    return {
        "id": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "message": create_test_message(),
        "metadata": {}
    }

def test_get_agent_card():
    """
    Test retrieving the agent card
    """
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "name": "Movie Script Generator Agent",
            "version": "1.0.0"
        })
        
        response = client.get("/.well-known/agent.json")
        assert response.status_code == 200
        assert response.json()["name"] == "Movie Script Generator Agent"

def test_get_agent_card_not_found():
    """
    Test retrieving non-existent agent card
    """
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 404

def test_send_task_success(test_client):
    """
    Test successful task submission
    """
    params = create_test_task_params()
    response = test_client.post("/tasks/send", json=params)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == params["id"]
    assert data["status"]["state"] == TaskState.SUBMITTED
    assert "message" in data["status"]

def test_send_task_error(test_client, mock_task_processor):
    """
    Test task submission with error
    """
    async def mock_error_task(_):
        raise ValueError("Test error")
    
    mock_task_processor.create_task = mock_error_task
    params = create_test_task_params()
    response = test_client.post("/tasks/send", json=params)
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Test error"

def test_get_task_success(test_client):
    """
    Test successful task retrieval
    """
    response = test_client.get("/tasks/test-123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-123"
    assert data["status"]["state"] == TaskState.COMPLETED

def test_get_task_not_found(test_client):
    """
    Test task retrieval for non-existent task
    """
    response = test_client.get("/tasks/nonexistent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_cancel_task_success(test_client):
    """
    Test successful task cancellation
    """
    response = test_client.post("/tasks/test-123/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-123"
    assert data["status"]["state"] == TaskState.CANCELLED

def test_send_task_subscribe(test_client):
    """
    Test task submission with streaming response
    """
    params = create_test_task_params()
    with test_client.websocket_connect(f"/tasks/sendSubscribe") as websocket:
        websocket.send_json(params)
        
        # Check initial state
        data = websocket.receive_json()
        assert data["event"] == "update"
        task_data = json.loads(data["data"])
        assert task_data["status"]["state"] == TaskState.WORKING
        
        # Check final state
        data = websocket.receive_json()
        assert data["event"] == "update"
        task_data = json.loads(data["data"])
        assert task_data["status"]["state"] == TaskState.COMPLETED

def test_set_push_notification(test_client):
    """
    Test setting push notification configuration
    """
    config = {
        "url": "https://test.com/webhook",
        "events": ["status", "artifact"]
    }
    response = test_client.post("/tasks/test-123/pushNotification", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == config["url"]
    assert data["events"] == config["events"]

def test_get_push_notification_success(test_client):
    """
    Test getting push notification configuration
    """
    response = test_client.get("/tasks/test-123/pushNotification")
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://test.com/webhook"
    assert "status" in data["events"]

def test_get_push_notification_not_found(test_client):
    """
    Test getting non-existent push notification configuration
    """
    response = test_client.get("/tasks/nonexistent/pushNotification")
    assert response.status_code == 404 