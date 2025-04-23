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

from src.client import AgentClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def server_process():
    """
    Start the server process before running tests
    """
    # Start server
    logger.info("Starting server...")
    server = subprocess.Popen(
        ["python", "src/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    yield server
    
    # Cleanup after tests
    logger.info("Stopping server...")
    server.send_signal(signal.SIGINT)
    server.wait()

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
async def test_push_notifications_streaming(server_process):
    """
    Test streaming push notifications during task execution using SSE
    """
    collector = NotificationCollector(timeout=60.0)
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create streaming task
        task_data = await client.interpreter.create_task_data(
            agent_card,
            "Generate a short story about an AI learning to paint"
        )
        
        # Subscribe to SSE updates
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{client.base_url}/tasks/sendSubscribe",
                json=task_data
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
            "invalid": "data"
        }
        
        # Expect task to fail
        with pytest.raises(Exception) as exc_info:
            task_response = await client.send_task(task_data)
            
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
        task_data = await client.interpreter.create_task_data(
            agent_card,
            "Write a detailed analysis of War and Peace"
        )
        
        # Subscribe to SSE updates
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{client.base_url}/tasks/sendSubscribe",
                json=task_data
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to subscribe to updates: {response.status}")
                
                # Let it run briefly to ensure it's in working state
                await asyncio.sleep(2)
                
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
                
                # Cancel the task
                try:
                    cancel_response = await client.cancel_task(task_id)
                    collector.add_status_update(cancel_response["status"])
                except Exception as e:
                    logger.error(f"Failed to cancel task: {str(e)}")
                    raise
                
                # Wait for final update
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
                                    if "status" in data:
                                        collector.add_status_update(data["status"])
                                        if data["status"]["state"] == "cancelled":
                                            break
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error decoding JSON from SSE event: {e}")
                                    logger.debug(f"Raw event data: {event_data}")
                                    continue
                except asyncio.TimeoutError:
                    logger.warning("SSE connection timed out")
                
        # Verify status sequence
        assert collector.verify_status_sequence(), "Invalid status transition sequence"
        assert collector.status_updates[-1]["state"] == "cancelled", \
            f"Task was not properly cancelled. Final state: {collector.status_updates[-1]['state']}"
            
        # Verify we can't cancel an already cancelled task
        with pytest.raises(Exception) as exc_info:
            await client.cancel_task(task_id)
        assert "Cannot cancel task in cancelled state" in str(exc_info.value)

if __name__ == "__main__":
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Start server manually when running directly
    logger.info("Starting server...")
    server = subprocess.Popen(
        ["python", "src/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Run test
        asyncio.run(test_push_notifications_streaming(server))
    finally:
        # Cleanup
        logger.info("Stopping server...")
        server.send_signal(signal.SIGINT)
        server.wait()
    
    # Run tests
    #asyncio.run(test_push_notifications_error_handling())
    #asyncio.run(test_push_notifications_cancellation()) 