"""
Test suite for A2A Push Notifications functionality.
This module tests the implementation of push notifications in the A2A protocol,
including status updates and artifact updates.
"""
import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import logging
from dotenv import load_dotenv
import subprocess
import time
import os
import signal
import aiohttp
import uvicorn
import threading
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
import uuid

from src.client import AgentClient
from src.api.app import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_server_running():
    """
    * Check if the server is already running
    * @returns {boolean} True if server is running, False otherwise
    """
    try:
        response = requests.get("http://localhost:8000/health")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def run_server():
    """
    * Run the FastAPI server in a separate thread
    """
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",  # Changed from 0.0.0.0 to localhost
        port=8000,
        log_level="info",
        reload=False  # Ensure reload is disabled for testing
    )
    server = uvicorn.Server(config)
    server.run()

@pytest.fixture(scope="session")
def server_process():
    """
    * Fixture to manage the server process
    * Starts the server if not running and ensures cleanup
    """
    if not is_server_running():
        logger.info("Starting server in a new thread...")
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        retries = 5
        while retries > 0 and not is_server_running():
            time.sleep(1)
            retries -= 1
            logger.info(f"Waiting for server to start... {retries} retries left")
        
        if not is_server_running():
            pytest.fail("Server failed to start")
    
    yield
    # No need to cleanup as we're using daemon threads

@pytest.fixture
def test_client():
    """
    * Create a test client for the FastAPI application
    * @returns {TestClient} FastAPI test client
    """
    return TestClient(app)

def test_stream_notifications(server_process, test_client):
    """
    * Test streaming notifications functionality using SSE endpoint
    """
    # Create a task first
    task_data = {
        "title": "AI Paints a Dream",
        "tags": ["short story", "AI", "painting"],
        "idea": "An AI learns to paint and discovers creativity.",
        "duration": 5
    }
    envelope = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {
            "sessionId": None,
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": task_data["idea"]
                    }
                ]
            },
            "metadata": {
                "title": task_data["title"],
                "tags": task_data["tags"],
                "idea": task_data["idea"],
                "duration": task_data.get("duration"),
                "lyrics": task_data.get("lyrics")
            }
        }
    }
    response = test_client.post("/tasks/send", json=envelope)
    assert response.status_code == 200
    task_id = response.json()["id"]
    
    # Now subscribe to updates
    with test_client.get(f"/tasks/{task_id}", stream=True) as response:
        assert response.status_code == 200
        task_data = response.json()
        assert "state" in task_data
        assert task_data["state"] in {"submitted", "working", "completed", "failed"}

def test_cancel_notification(server_process, test_client):
    """
    * Test cancellation of notifications using HTTP endpoints
    """
    # Create a task first
    task_data = {
        "title": "War and Peace Analysis",
        "tags": ["analysis", "literature", "War and Peace"],
        "idea": "A detailed analysis of War and Peace.",
        "duration": 60
    }
    envelope = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {
            "sessionId": None,
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": task_data["idea"]
                    }
                ]
            },
            "metadata": {
                "title": task_data["title"],
                "tags": task_data["tags"],
                "idea": task_data["idea"],
                "duration": task_data.get("duration"),
                "lyrics": task_data.get("lyrics")
            }
        }
    }
    response = test_client.post("/tasks/send", json=envelope)
    assert response.status_code == 200
    task_id = response.json()["id"]
    
    # Cancel the task
    response = test_client.post(f"/tasks/{task_id}/cancel")
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["state"] == "cancelled"

class NotificationCollector:
    """
    Helper class to collect and verify push notifications
    
    @param max_notifications: Maximum number of notifications to collect before stopping
    @param timeout: Maximum time to wait for notifications in seconds
    """
    def __init__(self, max_notifications: int = 10, timeout: float = 60.0):
        self.status_updates: List[Dict[str, Any]] = []
        self.artifact_updates: List[Dict[str, Any]] = []
        self.max_notifications = max_notifications
        self.timeout = timeout
        self.done = asyncio.Event()
        
    def add_status_update(self, update: Dict[str, Any]):
        """
        Add a status update notification
        
        @param update: Status update data
        """
        self.status_updates.append(update)
        if update.get("state") in {"completed", "failed", "cancelled"}:
            self.done.set()
        
    def add_artifact_update(self, update: Dict[str, Any]):
        """
        Add an artifact update notification
        
        @param update: Artifact update data
        """
        self.artifact_updates.append(update)
        
    @property
    def total_notifications(self) -> int:
        """Get total number of notifications received"""
        return len(self.status_updates) + len(self.artifact_updates)
        
    def verify_status_sequence(self) -> bool:
        """
        Verify that status updates follow valid A2A protocol state transitions
        
        @returns: True if sequence is valid, False otherwise
        """
        if not self.status_updates:
            return False
            
        valid_states = {"submitted", "working", "input-required", "completed", "failed", "cancelled"}
        current_state = None
        
        for update in self.status_updates:
            state = update.get("state")
            
            # Verify state is valid
            if state not in valid_states:
                logger.error(f"Invalid state: {state}")
                return False
                
            # Verify state transitions
            if current_state:
                # Can't go back to submitted
                if current_state != "submitted" and state == "submitted":
                    logger.error("Invalid transition: Can't return to submitted state")
                    return False
                    
                # Can't continue after terminal state
                if current_state in {"completed", "failed", "cancelled"} and state != current_state:
                    logger.error(f"Invalid transition: Can't transition from {current_state} to {state}")
                    return False
                    
            current_state = state
            
        return True

@pytest.mark.asyncio
async def test_push_notifications_streaming(server_process=None):
    """
    * Test streaming push notifications during task execution using SSE
    * @param server_process: Optional fixture parameter, not used when running directly
    """
    collector = NotificationCollector(timeout=60.0)
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create streaming task
        task_data = {
            "title": "AI Paints a Dream",
            "tags": ["short story", "AI", "painting"],
            "idea": "An AI learns to paint and discovers creativity.",
            "duration": 5
        }
        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/sendSubscribe",
            "params": {
                "sessionId": None,
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": task_data["idea"]
                        }
                    ]
                },
                "metadata": {
                    "title": task_data["title"],
                    "tags": task_data["tags"],
                    "idea": task_data["idea"],
                    "duration": task_data.get("duration"),
                    "lyrics": task_data.get("lyrics")
                }
            }
        }
        
        # Subscribe to SSE updates
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{client.base_url}/tasks/sendSubscribe",
                json=envelope
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to subscribe to updates: {response.status}")
                
                try:
                    async for event in response.content:
                        if event:
                            event_data = event.decode()
                            # Skip heartbeats and empty lines
                            if not event_data.strip() or event_data == "data: ":
                                continue
                                
                            # Ensure it's a data event and extract the JSON
                            if event_data.startswith("data: "):
                                try:
                                    data = json.loads(event_data.replace("data: ", "", 1))
                                    logger.info(f"SSE update received: {data}")
                                    
                                    if "status" in data:
                                        collector.add_status_update(data["status"])
                                        
                                    if "artifacts" in data and data["artifacts"]:
                                        for artifact in data["artifacts"]:
                                            collector.add_artifact_update(artifact)
                                            
                                    # Check if we're done
                                    if collector.done.is_set():
                                        break
                                        
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error decoding JSON from SSE event: {e}")
                                    logger.debug(f"Raw event data: {event_data}")
                                    continue
                except asyncio.TimeoutError:
                    logger.warning("SSE connection timed out")
                    
        # Verify notifications
        assert collector.total_notifications > 0, "No notifications received"
        assert collector.verify_status_sequence(), "Invalid status transition sequence"
        
        # Verify final state
        final_status = collector.status_updates[-1]
        assert final_status["state"] in {"completed", "failed", "cancelled"}, \
            f"Task did not reach terminal state. Final state: {final_status['state']}"

@pytest.mark.asyncio
async def test_push_notifications_error_handling():
    """
    Test error handling in push notifications
    """
    collector = NotificationCollector()
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create task with invalid data to trigger error
        task_data = {
            "title": "",
            "tags": [],
            "idea": "",
            "duration": None
        }
        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "sessionId": None,
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": task_data["idea"]
                        }
                    ]
                },
                "metadata": {
                    "title": task_data["title"],
                    "tags": task_data["tags"],
                    "idea": task_data["idea"],
                    "duration": task_data.get("duration"),
                    "lyrics": task_data.get("lyrics")
                }
            }
        }
        
        # Expect task to fail
        with pytest.raises(Exception) as exc_info:
            task_response = await client.send_task(envelope)
            
        assert "Failed to send task" in str(exc_info.value)

@pytest.mark.asyncio
async def test_push_notifications_cancellation():
    """
    Test cancellation handling in push notifications
    """
    collector = NotificationCollector()
    task_id = None
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create long-running task
        task_data = {
            "title": "War and Peace Analysis",
            "tags": ["analysis", "literature", "War and Peace"],
            "idea": "A detailed analysis of War and Peace.",
            "duration": 60
        }
        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/sendSubscribe",
            "params": {
                "sessionId": None,
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": task_data["idea"]
                        }
                    ]
                },
                "metadata": {
                    "title": task_data["title"],
                    "tags": task_data["tags"],
                    "idea": task_data["idea"],
                    "duration": task_data.get("duration"),
                    "lyrics": task_data.get("lyrics")
                }
            }
        }
        
        # Subscribe to SSE updates
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{client.base_url}/tasks/sendSubscribe",
                json=envelope
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to subscribe to updates: {response.status}")
                
                # Process events until we get the task ID and working state
                async for event in response.content:
                    if event:
                        event_data = event.decode()
                        # Skip heartbeats and empty lines
                        if not event_data.strip() or event_data == "data: ":
                            continue
                            
                        # Ensure it's a data event and extract the JSON
                        if event_data.startswith("data: "):
                            try:
                                data = json.loads(event_data.replace("data: ", "", 1))
                                if "id" in data:
                                    task_id = data["id"]
                                if "status" in data:
                                    collector.add_status_update(data["status"])
                                    if data["status"]["state"] == "working":
                                        break
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding JSON from SSE event: {e}")
                                logger.debug(f"Raw event data: {event_data}")
                                continue
                
                if not task_id:
                    raise Exception("Failed to get task ID from initial response")
                
                # Let task run briefly
                await asyncio.sleep(2)
                
                # Cancel the task
                try:
                    cancel_response = await client.cancel_task(task_id)
                    collector.add_status_update(cancel_response["status"])
                    logger.info(f"Task cancelled successfully: {cancel_response['status']}")
                except Exception as e:
                    logger.error(f"Failed to cancel task: {str(e)}")
                    raise

                # No need to wait for more SSE updates after cancellation
                # The connection will be closed by the server
                logger.info("Task cancelled, SSE connection will be closed")

        # Verify status sequence
        assert collector.verify_status_sequence(), "Invalid status transition sequence"
        
        # Get final status directly
        final_status = await client.check_task_status(task_id)
        collector.add_status_update(final_status["status"])
        
        assert final_status["status"]["state"] == "cancelled", \
            f"Task was not properly cancelled. Final state: {final_status['status']['state']}"
            
        # Verify we can't cancel an already cancelled task
        with pytest.raises(Exception) as exc_info:
            await client.cancel_task(task_id)
        assert "Cannot cancel task in cancelled state" in str(exc_info.value)

if __name__ == "__main__":
    # Run async tests directly
    async def run_tests():
        """
        * Run all async tests in sequence
        * This allows for proper debugging with breakpoints
        """
        # Start server if needed
        server_thread = None
        if not is_server_running():
            logger.info("Server not running. Starting server...")
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            retries = 5
            while retries > 0 and not is_server_running():
                time.sleep(1)
                retries -= 1
                logger.info(f"Waiting for server to start... {retries} retries left")
            
            if not is_server_running():
                raise Exception("Server failed to start")

        try:
            # Run each test
            logger.info("Running streaming notifications test...")
            await test_push_notifications_streaming()
            
            logger.info("Running error handling test...")
            await test_push_notifications_error_handling()
            
            logger.info("Running cancellation test...")
            await test_push_notifications_cancellation()
            
            logger.info("All tests completed successfully!")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

    # Run the tests
    asyncio.run(run_tests())