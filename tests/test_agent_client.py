"""
Test script that behaves as an agent client using A2A protocol.
This script will:
1. Request the AgentCard
2. Interpret the AgentCard using OpenAI
3. Adapt our specific goal to the agent's required structure
4. Send a task request
5. Poll for task status
6. Handle success/failure states
"""
import asyncio
import aiohttp
import json
from typing import Dict, Optional, Any, List
import logging
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import pytest
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentCardInterpreter:
    """
    Interprets the AgentCard using OpenAI to understand input/output requirements and adapt our goals
    
    @param api_key: OpenAI API key
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        
    async def create_task_data(self, agent_card: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """
        Analyze the agent card and create task data that matches both the required structure
        and our specific goal
        
        @param agent_card: The agent card to analyze
        @param goal: Our specific goal for the task (e.g. "Create a technical script for a music video based on Bohemian Rhapsody")
        @returns: Dictionary with properly structured task data
        @raises: Exception if interpretation fails
        """
        try:
            # Create a prompt for OpenAI to analyze the agent card and create appropriate task data
            prompt = f"""
            You are an AI tasked with creating valid input data for an agent.

            The agent's card specification is:
            {json.dumps(agent_card, indent=2)}

            The goal we want to achieve is:
            {goal}

            Create a task input that:
            1. Follows exactly the structure required by the agent (based on the agent card)
            2. Contains appropriate values that will help achieve our goal
            3. Includes all required fields with valid data types

            Important: Respond ONLY with the raw JSON data, no markdown formatting or explanation.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates valid API inputs to achieve specific goals. Only respond with raw JSON data, no markdown or explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Clean the response content
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code block indicators if present
            if content.startswith('```'):
                content = '\\n'.join(content.split('\\n')[1:-1])
            if content.startswith('json'):
                content = '\\n'.join(content.split('\\n')[1:])
                
            # Parse the cleaned response into a dictionary
            task_data = json.loads(content)
            return task_data
            
        except Exception as e:
            raise Exception(f"Failed to create task data: {str(e)}")

class AgentClient:
    """
    A client that interacts with our script generator agent using A2A protocol
    
    @param base_url: Base URL of the agent service
    @param max_retries: Maximum number of status check retries
    @param retry_delay: Delay between retries in seconds
    @param openai_api_key: OpenAI API key for intelligent interpretation
    """
    def __init__(
        self, 
        base_url: str = "http://localhost:8000",
        max_retries: int = 40,
        retry_delay: int = 15,
        openai_api_key: Optional[str] = None
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = None
        self.interpreter = AgentCardInterpreter(openai_api_key)
        self.task_history = {}
        
    async def __aenter__(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            
    async def get_agent_card(self) -> Dict[str, Any]:
        """
        Request the agent's card using A2A protocol
        
        @returns: Agent card information
        @raises: Exception if request fails
        """
        if not self.session:
            raise Exception("Session not initialized. Use async with.")
            
        async with self.session.get(f"{self.base_url}/.well-known/agent.json") as response:
            if response.status != 200:
                raise Exception(f"Failed to get agent card: {response.status}")
            return await response.json()
            
    async def send_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a task request to the agent
        
        @param task_data: Task parameters
        @returns: Initial task response
        @raises: Exception if request fails
        """
        if not self.session:
            raise Exception("Session not initialized. Use async with.")
            
        async with self.session.post(
            f"{self.base_url}/tasks/send",
            json=task_data
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to send task: {response.status}")
            return await response.json()
            
    async def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a task
        
        @param task_id: ID of the task to check
        @returns: Task status response
        @raises: Exception if request fails
        """
        if not self.session:
            raise Exception("Session not initialized. Use async with.")
            
        async with self.session.get(
            f"{self.base_url}/tasks/{task_id}"
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to check task status: {response.status}")
            return await response.json()
            
    async def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete history of a task including all state transitions and messages
        
        @param task_id: ID of the task to get history for
        @returns: List of historical states and messages
        @raises: Exception if request fails
        """
        if not self.session:
            raise Exception("Session not initialized.")
            
        async with self.session.get(
            f"{self.base_url}/tasks/{task_id}/history"
        ) as response:
            if response.status != 200:
                raise Exception(f"Task {task_id} not found")
            return await response.json()
            
    async def _update_task_history(self, task_id: str, status_update: Dict[str, Any]):
        """
        Update internal task history with new status
        
        @param task_id: ID of the task
        @param status_update: New status update to add to history
        """
        if task_id not in self.task_history:
            self.task_history[task_id] = []
            
        # Validate state transition if present
        if "state" in status_update:
            new_state = status_update["state"]
            current_state = self.task_history[task_id][-1]["state"] if self.task_history[task_id] else None
            
            if current_state == "completed":
                raise Exception("Invalid state transition: Cannot update completed task")
                
        # Add timestamp if not present
        if "timestamp" not in status_update:
            status_update["timestamp"] = datetime.utcnow().isoformat()
            
        self.task_history[task_id].append(status_update)
    
    async def wait_for_completion(self, task_id: str) -> Dict[str, Any]:
        """
        Wait for task completion with retries
        
        @param task_id: ID of the task to monitor
        @returns: Final task result
        @raises: Exception if task fails or timeout
        """
        for attempt in range(self.max_retries):
            task_status = await self.check_task_status(task_id)
            state = task_status["status"]["state"]
            
            # Update task history
            await self._update_task_history(task_id, task_status["status"])
            
            if state == "completed":
                logger.info("Task completed successfully")
                return task_status
            elif state == "failed":
                error_msg = task_status["status"]["message"]["parts"][0]["text"]
                raise Exception(f"Task failed: {error_msg}")
            elif state == "cancelled":
                raise Exception("Task was canceled")
                
            logger.info(f"Task in progress. State: {state}. Attempt {attempt + 1}/{self.max_retries}")
            await asyncio.sleep(self.retry_delay)
            
        raise Exception(f"Task did not complete after {self.max_retries} retries")

async def main():
    """
    Main function demonstrating the agent client usage with specific goal
    """
    # Define our specific goal with detailed requirements
    goal = """
    Create a technical script for a 20-second music video with these specific requirements:
    
    Song Details:
    - Duration: 20 seconds
    - Number of scenes: 3
    - Electronic dance music (EDM) style
    - Focus on the build-up and drop sequence
    - Instrumental focus with minimal vocals
    
    Visual Style:
    - Modern, minimalist aesthetic
    - Color palette: Neon blues and purples with white accents
    - Urban nighttime settings
    - Mix of real footage and digital effects
    
    Technical Requirements:
    - Drone shots of city landscapes
    - Quick cuts synchronized with the beat
    - Particle effects during the drop sequence
    - Light trails and long exposure effects
    - Smooth transitions between real and digital elements
    
    Mood and Narrative:
    - Start with calm, establishing city shots
    - Gradual build-up of visual intensity
    """
    
    try:
        async with AgentClient() as client:
            # Get agent card
            logger.info("Requesting agent card...")
            agent_card = await client.get_agent_card()
            logger.info(f"Agent name: {agent_card.get('name')}")
            
            # Create task data based on our goal
            logger.info("Creating task data for our goal...")
            task_data = await client.interpreter.create_task_data(agent_card, goal)
            logger.info(f"Generated task data: {json.dumps(task_data, indent=2)}")
            
            # Send task
            logger.info("Sending task...")
            task_response = await client.send_task(task_data)
            task_id = task_response["id"]
            logger.info(f"Task created with ID: {task_id}")
            
            # Wait for completion
            logger.info("Waiting for task completion...")
            final_result = await client.wait_for_completion(task_id)
            
            # Print results
            logger.info("Task completed!")
            print(json.dumps(final_result, indent=2))
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

async def test_task_history_tracking():
    """
    Test that task history follows A2A protocol state transitions and structure
    """
    async with AgentClient() as client:
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
    async with AgentClient() as client:
        task_id = "non-existent-task"
        with pytest.raises(Exception) as exc_info:
            await client.get_task_history(task_id)
        assert f"Task {task_id} not found" in str(exc_info.value)
        
    # Test invalid state transitions
    async with AgentClient() as client:
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

if __name__ == "__main__":
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    asyncio.run(test_task_history_tracking())
    asyncio.run(test_history_error_handling()) 