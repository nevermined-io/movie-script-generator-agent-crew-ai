"""
Test script that behaves as an agent client using A2A protocol.
This script will:
1. Request the AgentCard
2. Interpret the AgentCard using OpenAI
3. Send an INVALID task request to test error handling
4. Verify the error response
"""
import asyncio
import aiohttp
import json
from typing import Dict, Optional, Any
import logging
import os
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentCardInterpreter:
    """
    Interprets the AgentCard using OpenAI to understand input/output requirements and adapt our goals
    
    @param api_key: OpenAI API key
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        
    async def create_invalid_task_data(self, agent_card: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """
        Analyze the agent card and create INVALID task data that will trigger a 422 error
        
        @param agent_card: The agent card to analyze
        @param goal: Our specific goal for the task
        @returns: Dictionary with intentionally invalid task data
        """
        # Create an invalid task structure that will trigger validation errors
        return {
            "id": "test-123",
            "message": {
                "role": "user",
                # Invalid: parts should be a list but we're sending a string
                "parts": "This should be a list but it's a string to trigger an error"
            },
            # Invalid: sessionId should be a string
            "sessionId": 12345
        }

class AgentClient:
    """
    A client that interacts with our script generator agent using A2A protocol
    
    @param base_url: Base URL of the agent service
    """
    def __init__(
        self, 
        base_url: str = "http://localhost:8000",
        openai_api_key: Optional[str] = None
    ):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.interpreter = AgentCardInterpreter(openai_api_key)
        
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
            
        async with self.session.get(f"{self.base_url}/agent-card") as response:
            if response.status != 200:
                raise Exception(f"Failed to get agent card: {response.status}")
            return await response.json()
            
    async def send_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an invalid task request to the agent
        
        @param task_data: Invalid task parameters
        @returns: Error response from server
        """
        if not self.session:
            raise Exception("Session not initialized. Use async with.")
            
        async with self.session.post(
            f"{self.base_url}/tasks/send",
            json=task_data
        ) as response:
            return {
                "status": response.status,
                "data": await response.json()
            }

async def main():
    """
    Main function demonstrating the error handling when sending invalid task data
    """
    # Define a simple goal (won't be used properly as we're testing error cases)
    goal = "Create a movie script"
    
    try:
        async with AgentClient() as client:
            # Get the agent card
            logger.info("Requesting agent card...")
            agent_card = await client.get_agent_card()
            logger.info("Agent card received")
            
            # Create invalid task data
            logger.info("Creating invalid task data...")
            task_data = await client.interpreter.create_invalid_task_data(agent_card, goal)
            logger.info(f"Invalid task data created: {json.dumps(task_data, indent=2)}")
            
            # Send the invalid task and expect an error
            logger.info("Sending invalid task...")
            response = await client.send_task(task_data)
            
            # Log the error response
            logger.info(f"Received error response (status {response['status']}):")
            logger.info(json.dumps(response['data'], indent=2))
            
            if response['status'] == 422:
                logger.info("Successfully received validation error as expected")
            else:
                logger.warning(f"Unexpected response status: {response['status']}")
                
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 