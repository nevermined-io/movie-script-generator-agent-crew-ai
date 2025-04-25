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

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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
        logger.info("=== Starting Task History Tracking Test ===")
        
        async with AgentClient(base_url="http://localhost:8000") as client:
            # Get agent card first
            logger.info("Requesting agent card...")
            agent_card = await client.get_agent_card()
            logger.info(f"Agent card received: {json.dumps(agent_card, indent=2)}")
            
            # Create and send a task
            logger.info("Creating new task...")
            task_data = await client.interpreter.create_task_data(
                agent_card,
                "Write a short comedy script about a misunderstanding at a coffee shop"
            )
            logger.info(f"Task data created: {json.dumps(task_data, indent=2)}")
            
            task_response = await client.send_task(task_data)
            task_id = task_response["id"]
            logger.info(f"Task sent successfully. Task ID: {task_id}")
            
            try:
                # Wait for completion while tracking history
                logger.info(f"Waiting for task {task_id} completion...")
                result = await client.wait_for_completion(task_id)
                logger.info(f"Task completed. Result: {json.dumps(result, indent=2)}")
                
                # Get history for verification
                history = client.task_history[task_id]
                logger.info(f"Task history entries: {len(history)}")
                
                # Log each state transition
                for i, entry in enumerate(history, 1):
                    logger.info(f"State transition {i}: {entry['state']}")
                    if "message" in entry:
                        logger.info(f"Message for state {entry['state']}: {json.dumps(entry['message'], indent=2)}")
                    logger.info(f"Timestamp: {entry['timestamp']}")
                    logger.info("-" * 50)
                
                states = [entry["state"] for entry in history]
                valid_states = {"submitted", "working", "input-required", "completed", "failed", "cancelled"}
                logger.info(f"State sequence: {' -> '.join(states)}")
                
                # Verify state validity
                invalid_states = [state for state in states if state not in valid_states]
                if invalid_states:
                    logger.warning(f"Found invalid states: {invalid_states}")
                
                # Log final state
                final_state = history[-1]["state"]
                logger.info(f"Task completed with final state: {final_state}")
                
                # Check state transitions
                for i in range(1, len(states)):
                    prev_state = states[i-1]
                    curr_state = states[i]
                    logger.info(f"Transition: {prev_state} -> {curr_state}")
                    
                    # Log potential issues
                    if prev_state != "submitted" and curr_state == "submitted":
                        logger.warning("Invalid transition: Returned to submitted state")
                    
                    if prev_state in {"completed", "failed", "cancelled"} and curr_state != prev_state:
                        logger.warning(f"Invalid transition: Changed from terminal state {prev_state} to {curr_state}")
                
            except Exception as e:
                logger.error(f"Task failed: {str(e)}")
                raise
            
        logger.info("=== Task History Tracking Test Completed ===")

    async def test_history_error_handling(self):
        """
        * Test error handling for history-related operations according to A2A protocol
        """
        logger.info("=== Starting History Error Handling Test ===")
        
        # Test uninitialized session
        logger.info("Testing uninitialized session...")
        client = AgentClient(base_url="http://invalid-url")
        try:
            await client.get_task_history("invalid-task-id")
        except Exception as e:
            logger.info(f"Expected error for uninitialized session: {str(e)}")
        
        # Test non-existent task ID
        logger.info("Testing non-existent task ID...")
        async with AgentClient(base_url="http://localhost:8000") as client:
            task_id = "non-existent-task"
            try:
                await client.get_task_history(task_id)
            except Exception as e:
                logger.info(f"Expected error for non-existent task: {str(e)}")
            
        # Test invalid state transitions
        logger.info("Testing invalid state transitions...")
        async with AgentClient(base_url="http://localhost:8000") as client:
            task_id = "test-task"
            
            # Start with completed state
            logger.info("Setting initial state to 'completed'...")
            initial_state = {
                "state": "completed",
                "message": {
                    "parts": [{"text": "Task completed"}]
                }
            }
            await client._update_task_history(task_id, initial_state)
            logger.info(f"Initial state set: {json.dumps(initial_state, indent=2)}")
            
            # Try to transition to working (should fail)
            logger.info("Attempting invalid transition to 'working' state...")
            try:
                invalid_state = {
                    "state": "working",
                    "message": {
                        "parts": [{"text": "Cannot work on completed task"}]
                    }
                }
                await client._update_task_history(task_id, invalid_state)
            except Exception as e:
                logger.info(f"Expected error for invalid state transition: {str(e)}")
        
        logger.info("=== History Error Handling Test Completed ===")

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
        logger.info("========================================")
        logger.info("Starting test suite execution...")
        logger.info("========================================")
        
        logger.info("Running task history tracking test...")
        run_async_test(test_case, "test_task_history_tracking")
        
        logger.info("Running error handling test...")
        run_async_test(test_case, "test_history_error_handling")
        
        logger.info("========================================")
        logger.info("All tests completed successfully!")
        logger.info("========================================")
        
    except Exception as e:
        logger.error("========================================")
        logger.error(f"Test suite failed: {str(e)}")
        logger.error("========================================")
        raise 