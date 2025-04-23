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
    @param max_attempts: Maximum number of status check attempts
    """
    def __init__(self, max_notifications: int = 10, timeout: float = 60.0, max_attempts: int = 30):
        self.status_updates: List[Dict[str, Any]] = []
        self.artifact_updates: List[Dict[str, Any]] = []
        self.max_notifications = max_notifications
        self.timeout = timeout
        self.max_attempts = max_attempts
        
    def add_status_update(self, update: Dict[str, Any]):
        """
        Add a status update notification
        
        @param update: Status update data
        """
        self.status_updates.append(update)
        
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
    Test streaming push notifications during task execution
    """
    collector = NotificationCollector(timeout=60.0, max_attempts=30)
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create streaming task
        task_data = await client.interpreter.create_task_data(
            agent_card,
            "Generate a short story about an AI learning to paint"
        )
        
        # Send task and collect notifications
        task_response = await client.send_task(task_data)
        task_id = task_response["id"]
        
        attempts = 0
        try:
            while collector.total_notifications < collector.max_notifications and attempts < collector.max_attempts:
                attempts += 1
                status = await client.check_task_status(task_id)
                
                # Process status update
                if "status" in status:
                    collector.add_status_update(status["status"])
                    logger.info(f"Status update received: {status['status']}")
                    if status["status"]["state"] in {"completed", "failed", "cancelled"}:
                        # For completed tasks, we expect artifacts
                        if status["status"]["state"] == "completed" and "artifacts" in status:
                            logger.info(f"Processing artifacts for completed task: {len(status['artifacts'])}")
                            for artifact in status["artifacts"]:
                                collector.add_artifact_update(artifact)
                        break
                        
                # Process artifact updates during task execution
                if "artifacts" in status and status["artifacts"]:
                    logger.info(f"Processing artifacts during execution: {len(status['artifacts'])}")
                    for artifact in status["artifacts"]:
                        collector.add_artifact_update(artifact)
                        
                await asyncio.sleep(2)  # Increased polling delay
                
        except asyncio.TimeoutError:
            logger.warning("Notification collection timed out")
            
        # Verify notifications
        assert collector.total_notifications > 0, "No notifications received"
        assert collector.verify_status_sequence(), "Invalid status transition sequence"
        
        # Verify final state
        final_status = collector.status_updates[-1]
        assert final_status["state"] in {"completed", "failed", "cancelled"}, \
            f"Task did not reach terminal state after {attempts} attempts. Final state: {final_status['state']}"

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
    
    async with AgentClient() as client:
        # Get agent card
        agent_card = await client.get_agent_card()
        
        # Create long-running task
        task_data = await client.interpreter.create_task_data(
            agent_card,
            "Write a detailed analysis of War and Peace"
        )
        
        # Send task
        task_response = await client.send_task(task_data)
        task_id = task_response["id"]
        
        # Let it run briefly to ensure it's in working state
        await asyncio.sleep(2)
        
        # Get initial status
        initial_status = await client.check_task_status(task_id)
        collector.add_status_update(initial_status["status"])
        
        # Cancel the task
        try:
            cancel_response = await client.cancel_task(task_id)
            collector.add_status_update(cancel_response["status"])
        except Exception as e:
            logger.error(f"Failed to cancel task: {str(e)}")
            raise
            
        # Verify cancellation status
        final_status = await client.check_task_status(task_id)
        collector.add_status_update(final_status["status"])
        
        # Verify status sequence
        assert collector.verify_status_sequence(), "Invalid status transition sequence"
        assert final_status["status"]["state"] == "cancelled", \
            f"Task was not properly cancelled. Final state: {final_status['status']['state']}"
            
        # Verify we can't cancel an already cancelled task
        with pytest.raises(Exception) as exc_info:
            await client.cancel_task(task_id)
        assert "Cannot cancel task in cancelled state" in str(exc_info.value)

if __name__ == "__main__":
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    asyncio.run(test_push_notifications_streaming())
    #asyncio.run(test_push_notifications_error_handling())
    #asyncio.run(test_push_notifications_cancellation()) 