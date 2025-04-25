"""
End-to-end tests for the A2A protocol client implementation using unittest
"""
import asyncio
import json
import logging
import os
import threading
import time
import unittest
from datetime import datetime
from typing import Dict, Optional, Any, List

import requests
import uvicorn
from dotenv import load_dotenv

from src.client import AgentClient, AgentCardInterpreter
from src.api.app import app

# Load environment variables from .env file
load_dotenv()

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
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)
    server.run()

class TestAgentClient(unittest.TestCase):
    """
    * Test class for AgentClient functionality
    * @class
    """
    
    @classmethod
    def setUpClass(cls):
        """
        * Set up test environment before running tests
        * Starts the server if not running
        """
        if not is_server_running():
            logger.info("Starting server in a new thread...")
            cls.server_thread = threading.Thread(target=run_server, daemon=True)
            cls.server_thread.start()
            
            # Wait for server to start
            retries = 5
            while retries > 0 and not is_server_running():
                time.sleep(1)
                retries -= 1
                logger.info(f"Waiting for server to start... {retries} retries left")
            
            if not is_server_running():
                raise Exception("Server failed to start")

    async def test_task_history_tracking(self):
        """
        * Test that task history follows A2A protocol state transitions and structure
        """
        async with AgentClient(base_url="http://localhost:8000") as client:
            # Get agent card first
            agent_card = await client.get_agent_card()
            
            # Create and send a task
            task_data = await client.interpreter.create_task_data(
                agent_card,
                "Write a short comedy script about a misunderstanding at a coffee shop"
            )
            task_response = await client.send_task(task_data)
            task_id = task_response["id"]
            
            try:
                # Wait for completion while tracking history
                result = await client.wait_for_completion(task_id)
                
                # Verify internal history tracking
                self.assertIn(task_id, client.task_history, "Task ID should be present in history")
                history = client.task_history[task_id]
                self.assertGreater(len(history), 0, "History should contain entries")
                
                # Verify A2A protocol state transitions
                states = [entry["state"] for entry in history]
                valid_states = {"submitted", "working", "input-required", "completed", "failed", "cancelled"}
                self.assertTrue(
                    all(state in valid_states for state in states),
                    f"All states should be valid A2A states: {valid_states}"
                )
                
                # Verify history entry structure according to A2A
                for entry in history:
                    # Required fields
                    self.assertIn("timestamp", entry, "Each entry should have a timestamp")
                    self.assertIn("state", entry, "Each entry should have a state")
                    self.assertIsInstance(entry["timestamp"], str, "Timestamp should be ISO format string")
                    self.assertIn(entry["state"], valid_states, f"State should be one of: {valid_states}")
                    
                    # Optional message field - verify A2A format if present
                    if "message" in entry:
                        message = entry["message"]
                        self.assertIsInstance(message, dict, "Message should be a dictionary")
                        self.assertIn("parts", message, "Message should have parts array")
                        self.assertIsInstance(message["parts"], list, "Message parts should be a list")
                        for part in message["parts"]:
                            self.assertIsInstance(part, dict, "Each part should be a dictionary")
                            if "text" in part:
                                self.assertIsInstance(part["text"], str, "Text in part should be a string")
                
                # Verify final state is terminal
                final_state = history[-1]["state"]
                self.assertIn(
                    final_state,
                    {"completed", "failed", "cancelled"},
                    "Task should end in a terminal state"
                )
                
                # Verify state transitions are logical
                for i in range(1, len(states)):
                    prev_state = states[i-1]
                    curr_state = states[i]
                    
                    # Can't go back to submitted after starting
                    if prev_state != "submitted":
                        self.assertNotEqual(
                            curr_state,
                            "submitted",
                            "Task can't return to submitted state"
                        )
                    
                    # Can't go back to working after completion
                    if prev_state in {"completed", "failed", "cancelled"}:
                        self.assertIn(
                            curr_state,
                            {"completed", "failed", "cancelled"},
                            "Task can't return to working after terminal state"
                        )
                
            except Exception as e:
                logger.error(f"Task failed: {str(e)}")
                raise

    async def test_history_error_handling(self):
        """
        * Test error handling for history-related operations according to A2A protocol
        """
        # Test uninitialized session
        client = AgentClient(base_url="http://invalid-url")
        with self.assertRaises(Exception) as context:
            await client.get_task_history("invalid-task-id")
        self.assertIn("Session not initialized", str(context.exception))
        
        # Test non-existent task ID
        async with AgentClient(base_url="http://localhost:8000") as client:
            task_id = "non-existent-task"
            with self.assertRaises(Exception) as context:
                await client.get_task_history(task_id)
            self.assertIn(f"Task {task_id} not found", str(context.exception))
            
        # Test invalid state transitions
        async with AgentClient(base_url="http://localhost:8000") as client:
            task_id = "test-task"
            # Start with completed state
            await client._update_task_history(task_id, {
                "state": "completed",
                "message": {
                    "parts": [{"text": "Task completed"}]
                }
            })
            
            # Try to transition to working (should fail)
            with self.assertRaises(Exception) as context:
                await client._update_task_history(task_id, {
                    "state": "working",
                    "message": {
                        "parts": [{"text": "Cannot work on completed task"}]
                    }
                })
            self.assertIn("Invalid state transition", str(context.exception))

def run_async_test(test_case, test_name):
    """
    * Helper function to run async test methods
    * @param {unittest.TestCase} test_case - The test case instance
    * @param {str} test_name - Name of the test method to run
    """
    test_method = getattr(test_case, test_name)
    asyncio.run(test_method())

if __name__ == "__main__":
    """
    * Run all tests in sequence
    * This allows for proper debugging with breakpoints
    """
    test_case = TestAgentClient()
    
    try:
        logger.info("Running task history tracking test...")
        run_async_test(test_case, "test_task_history_tracking")
        
        logger.info("Running error handling test...")
        run_async_test(test_case, "test_history_error_handling")
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise 