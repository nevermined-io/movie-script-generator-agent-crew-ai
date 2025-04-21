"""
Tests for the API routes.
"""
import pytest
from fastapi import status
from src.api.models import ScriptRequest
from src.models.task import TaskState, TaskStatus, Message, TextPart
from src.controllers.a2a_controller import controller, TaskRequest
from src.models.a2a import Task, TaskSendParams, PushNotificationConfig
from datetime import datetime
import json
import httpx
import asyncio
from src.server import app, get_task_processor

def test_generate_script_success(test_client, mock_task_processor, monkeypatch):
    """
    Test successful script generation with A2A implementation.
    Verifies that the endpoint returns immediately with SUBMITTED state.
    """

    print("test_generate_script_success")
    # Mock the task processor
    monkeypatch.setattr("src.server.get_task_processor", lambda: mock_task_processor)

    # Test data
    request_data = {
        "title": "Test Title",
        "tags": ["tag1", "tag2"],
        "idea": "Test idea",
        "lyrics": "Test lyrics",
        "duration": 180,
        "sessionId": "test-session",
        "metadata": {
            "source": "test",
            "priority": "high"
        }
    }

    print(f"Request data: {request_data}")

    # Make request
    response = test_client.post("/tasks/send", json=request_data)

    # Assertions for immediate response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    print(f"Result: {result}")
    assert result["id"] is not None
    assert result["status"]["state"] == TaskState.SUBMITTED.value
    assert result["status"]["message"]["parts"][0]["text"] == "Starting script generation..."
    assert result["metadata"]["source"] == "test"
    assert result["metadata"]["priority"] == "high"

    # Get task after a short delay to verify background processing started
    task_id = result["id"]
    response = test_client.get(f"/tasks/{task_id}")
    assert response.status_code == status.HTTP_200_OK
    task_status = response.json()
    assert task_status["status"]["state"] in [TaskState.SUBMITTED.value, TaskState.WORKING.value, TaskState.COMPLETED.value]

def test_generate_script_validation_error(test_client):
    """
    Test script generation with invalid request data
    """
    # Make request with invalid data
    response = test_client.post("/tasks/send", json={})

    # Assertions
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_task_success(test_client, monkeypatch):
    """
    Test successful task retrieval with A2A implementation
    """
    # Setup test task
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        status=TaskStatus(
            state=TaskState.COMPLETED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Test message")]
            )
        ),
        metadata={
            "source": "test",
            "sessionId": "test-session"
        }
    )
    controller.tasks[task_id] = test_task

    # Make request
    response = test_client.get(f"/tasks/{task_id}")

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] == task_id
    assert result["status"]["state"] == TaskState.COMPLETED.value
    assert result["metadata"]["source"] == "test"
    assert result["metadata"]["sessionId"] == "test-session"

def test_get_task_not_found(test_client):
    """
    Test task retrieval for non-existent task
    """
    response = test_client.get("/tasks/non-existent")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_cancel_task_success(test_client):
    """
    Test successful task cancellation with A2A implementation
    """
    # Setup test task
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        status=TaskStatus(
            state=TaskState.WORKING,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Working...")]
            )
        ),
        metadata={"sessionId": "test-session"}
    )
    controller.tasks[task_id] = test_task

    # Make request
    response = test_client.post(f"/tasks/{task_id}/cancel")

    # Assertions
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

def test_list_tasks_success(test_client):
    """
    Test successful task listing with A2A implementation
    """
    # Clear existing tasks
    controller.tasks.clear()
    
    # Setup test tasks
    task_id = "test-123"
    test_task = Task(
        id=task_id,
        status=TaskStatus(
            state=TaskState.COMPLETED,
            timestamp=datetime.utcnow().isoformat(),
            message=Message(
                role="assistant",
                parts=[TextPart(type="text", text="Test message")]
            )
        ),
        metadata={"sessionId": "test-session"}
    )
    controller.tasks[task_id] = test_task

    # Make request
    response = test_client.get("/tasks")

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == task_id
    assert result[0]["status"]["state"] == TaskState.COMPLETED.value
    assert result[0]["metadata"]["sessionId"] == "test-session"

def test_set_push_notification(test_client):
    """
    Test setting push notification configuration
    """
    task_id = "test-123"
    config = {
        "url": "https://test.com/webhook",
        "headers": {"Authorization": "Bearer test"}
    }
    
    response = test_client.post(f"/tasks/{task_id}/notifications", json=config)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["url"] == config["url"]
    assert result["headers"] == config["headers"]

def test_get_push_notification(test_client):
    """
    Test getting push notification configuration
    """
    task_id = "test-123"
    config = PushNotificationConfig(
        url="https://test.com/webhook",
        headers={"Authorization": "Bearer test"}
    )
    controller.push_notifications[task_id] = config
    
    response = test_client.get(f"/tasks/{task_id}/notifications")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["url"] == config.url
    assert result["headers"] == config.headers

@pytest.mark.asyncio
async def test_send_task_streaming_success(test_client, mock_task_processor, monkeypatch):
    """
    Test successful task streaming with A2A implementation
    """
    monkeypatch.setattr("src.server.get_task_processor", lambda: mock_task_processor)
    
    params = {
        "title": "Test Title",
        "tags": ["tag1", "tag2"],
        "idea": "Test idea",
        "lyrics": "Test lyrics",
        "duration": 180,
        "sessionId": "test-session",
        "metadata": {
            "source": "test",
            "priority": "high"
        }
    }
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/tasks/send/subscribe", params=params)
        assert response.status_code == 200
        
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                if event_data["status"]["state"] == TaskState.COMPLETED.value:
                    break
        
        assert len(events) >= 2
        
        # Verify first event (working state)
        assert events[0]["status"]["state"] == TaskState.WORKING.value
        assert events[0]["status"]["message"]["parts"][0]["text"] == "Generating movie script..."
        assert events[0]["metadata"]["source"] == "test"
        assert events[0]["metadata"]["priority"] == "high"

        # Verify last event (completed state)
        last_event = events[-1]
        assert last_event["status"]["state"] == TaskState.COMPLETED.value
        assert last_event["status"]["message"]["parts"][0]["text"] == "Movie script generated successfully"
        assert "artifacts" in last_event
        assert len(last_event["artifacts"]) > 0

@pytest.mark.asyncio
async def test_send_task_streaming_error(test_client, mock_task_processor, monkeypatch):
    """
    Test streaming error handling with A2A implementation
    """
    monkeypatch.setattr("src.server.get_task_processor", lambda: mock_task_processor)
    mock_task_processor.process_task_stream = mock_task_processor.mock_process_task_stream_error
    
    params = {
        "title": "Test Title",
        "tags": ["tag1", "tag2"],
        "idea": "Test idea",
        "lyrics": "Test lyrics",
        "duration": 180,
        "sessionId": "test-session",
        "metadata": {"source": "test"}
    }
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/tasks/send/subscribe", params=params)
        assert response.status_code == 200
        
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                if event_data["status"]["state"] == TaskState.ERROR.value:
                    break

        assert len(events) == 1
        assert events[0]["status"]["state"] == TaskState.ERROR.value
        assert events[0]["status"]["message"]["parts"][0]["text"] == "Failed to generate movie script: Invalid parameters provided"
        assert events[0]["metadata"]["source"] == "test"