"""
Integration tests for the API using a real server instance.
"""
import pytest
from fastapi.testclient import TestClient
import asyncio
import time
from datetime import datetime
from src.api.app import app
from src.models.task import TaskState

@pytest.fixture
def test_client():
    """
    Create a test client for the FastAPI application.
    
    @returns {TestClient} A FastAPI test client instance
    """
    return TestClient(app)

@pytest.mark.asyncio
async def test_real_script_generation(test_client):
    """
    Test real script generation without mocks.
    Verifies that the endpoint returns immediately with SUBMITTED state
    and eventually transitions to COMPLETED.
    
    @param {TestClient} test_client - FastAPI test client
    """
    # Test data
    request_data = {
        "title": "Test Integration",
        "tags": ["test", "integration"],
        "idea": "A simple test of the movie script generator",
        "lyrics": None,
        "duration": 60,
        "sessionId": "test-integration"
    }

    # Make initial request
    response = test_client.post("/tasks/send", json=request_data)
    assert response.status_code == 200
    
    # Verify initial response
    result = response.json()
    assert result["id"] is not None
    assert result["status"]["state"] == TaskState.SUBMITTED.value
    assert "Starting script generation..." in result["status"]["message"]["parts"][0]["text"]
    
    # Store task ID
    task_id = result["id"]
    
    # Poll task status until completion or timeout
    max_retries = 30  # 30 seconds timeout
    current_try = 0
    final_state = None
    
    while current_try < max_retries:
        # Get task status
        response = test_client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        
        task_status = response.json()
        current_state = task_status["status"]["state"]
        
        # Break if terminal state reached
        if current_state in [TaskState.COMPLETED.value, TaskState.FAILED.value]:
            final_state = current_state
            break
            
        # Wait before next poll
        current_try += 1
        await asyncio.sleep(1)  # Reduced sleep time for tests
    
    # Verify final state
    assert final_state is not None, "Task did not reach terminal state within timeout"
    assert final_state == TaskState.COMPLETED.value, "Task failed or did not complete"
    
    # Verify task artifacts
    response = test_client.get(f"/tasks/{task_id}")
    task_result = response.json()
    
    assert "artifacts" in task_result
    assert len(task_result["artifacts"]) > 0
    
    # Find and verify script artifact
    script_artifact = next((a for a in task_result["artifacts"] if "script" in a), None)
    assert script_artifact is not None
    assert isinstance(script_artifact["script"], str)
    assert isinstance(script_artifact["scenes"], list)
    assert isinstance(script_artifact["metadata"], dict)
    
    # Find and verify outline artifact
    outline_artifact = next((a for a in task_result["artifacts"] if "outline" in a), None)
    assert outline_artifact is not None
    assert isinstance(outline_artifact["outline"], str)
    assert isinstance(outline_artifact["scenes"], list)
    assert isinstance(outline_artifact["metadata"], dict)

def test_real_task_cancellation(test_client):
    """
    Test real task cancellation without mocks.
    
    @param {TestClient} test_client - FastAPI test client
    """
    # Create a task
    request_data = {
        "title": "Test Cancellation",
        "tags": ["test", "cancel"],
        "idea": "A task that will be cancelled",
        "lyrics": None,
        "duration": 120,
        "sessionId": "test-cancel"
    }
    
    # Start task
    response = test_client.post("/tasks/send", json=request_data)
    assert response.status_code == 200
    task_id = response.json()["id"]
    
    # Wait briefly to ensure task processing has started
    time.sleep(0.5)
    
    # Cancel task
    response = test_client.post(f"/tasks/{task_id}/cancel")
    assert response.status_code == 200
    
    # Verify cancellation
    result = response.json()
    assert result["status"]["state"] == TaskState.CANCELED.value
    assert "Task canceled" in result["status"]["message"]["parts"][0]["text"]

def test_real_task_listing(test_client):
    """
    Test real task listing functionality without mocks.
    
    @param {TestClient} test_client - FastAPI test client
    """
    # Create multiple tasks
    session_id = "test-listing"
    tasks = []
    
    for i in range(3):
        request_data = {
            "title": f"Test List {i}",
            "tags": ["test", "list"],
            "idea": f"Task number {i} for listing test",
            "lyrics": None,
            "duration": 60,
            "sessionId": session_id
        }
        
        response = test_client.post("/tasks/send", json=request_data)
        assert response.status_code == 200
        tasks.append(response.json()["id"])
    
    # List all tasks
    response = test_client.get("/tasks")
    assert response.status_code == 200
    all_tasks = response.json()
    
    # Verify all created tasks are present
    task_ids = [task["id"] for task in all_tasks]
    for task_id in tasks:
        assert task_id in task_ids
    
    # Filter by session
    response = test_client.get(f"/tasks?session_id={session_id}")
    assert response.status_code == 200
    session_tasks = response.json()
    
    # Verify all tasks in session are present
    assert len(session_tasks) == len(tasks)
    for task in session_tasks:
        assert task["sessionId"] == session_id 