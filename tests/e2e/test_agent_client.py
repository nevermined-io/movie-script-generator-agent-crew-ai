"""
End-to-end tests for the A2A protocol client implementation
"""
import asyncio
import json
from typing import Dict, Optional, Any, List
import logging
import os
from datetime import datetime
import pytest
from dotenv import load_dotenv

from src.client import AgentClient, AgentCardInterpreter

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_task_history_tracking():
    """
    Test that task history follows A2A protocol state transitions and structure
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
            assert task_id in client.task_history, "Task ID should be present in history"
            history = client.task_history[task_id]
            assert len(history) > 0, "History should contain entries"
            
            # Verify A2A protocol state transitions
            states = [entry["state"] for entry in history]
            valid_states = {"submitted", "working", "input-required", "completed", "failed", "cancelled"}
            assert all(state in valid_states for state in states), \
                f"All states should be valid A2A states: {valid_states}"
            
            # Verify history entry structure according to A2A
            for entry in history:
                # Required fields
                assert "timestamp" in entry, "Each entry should have a timestamp"
                assert "state" in entry, "Each entry should have a state"
                assert isinstance(entry["timestamp"], str), "Timestamp should be ISO format string"
                assert entry["state"] in valid_states, f"State should be one of: {valid_states}"
                
                # Optional message field - verify A2A format if present
                if "message" in entry:
                    message = entry["message"]
                    assert isinstance(message, dict), "Message should be a dictionary"
                    assert "parts" in message, "Message should have parts array"
                    assert isinstance(message["parts"], list), "Message parts should be a list"
                    for part in message["parts"]:
                        assert isinstance(part, dict), "Each part should be a dictionary"
                        if "text" in part:
                            assert isinstance(part["text"], str), "Text in part should be a string"
            
            # Verify final state is terminal
            final_state = history[-1]["state"]
            assert final_state in {"completed", "failed", "cancelled"}, \
                "Task should end in a terminal state"
            
            # Verify state transitions are logical
            for i in range(1, len(states)):
                prev_state = states[i-1]
                curr_state = states[i]
                
                # Can't go back to submitted after starting
                if prev_state != "submitted":
                    assert curr_state != "submitted", \
                        "Task can't return to submitted state"
                
                # Can't go back to working after completion
                if prev_state in {"completed", "failed", "cancelled"}:
                    assert curr_state in {"completed", "failed", "cancelled"}, \
                        "Task can't return to working after terminal state"
            
        except Exception as e:
            logger.error(f"Task failed: {str(e)}")
            raise

@pytest.mark.asyncio
async def test_history_error_handling():
    """
    Test error handling for history-related operations according to A2A protocol
    """
    # Test uninitialized session
    client = AgentClient(base_url="http://invalid-url")
    with pytest.raises(Exception) as exc_info:
        await client.get_task_history("invalid-task-id")
    assert "Session not initialized" in str(exc_info.value)
    
    # Test non-existent task ID
    async with AgentClient(base_url="http://localhost:8000") as client:
        task_id = "non-existent-task"
        with pytest.raises(Exception) as exc_info:
            await client.get_task_history(task_id)
        assert f"Task {task_id} not found" in str(exc_info.value)
        
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
        with pytest.raises(Exception) as exc_info:
            await client._update_task_history(task_id, {
                "state": "working",
                "message": {
                    "parts": [{"text": "Cannot work on completed task"}]
                }
            })
        assert "Invalid state transition" in str(exc_info.value) 