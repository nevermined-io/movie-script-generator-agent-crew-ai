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
    Create a technical script for a 60-second music video with these specific requirements:
    
    Song Details:
    - Duration: 60 seconds
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
    - Peak energy during the drop (30-45 second mark)
    - Elegant wind-down for the final 15 seconds
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

if __name__ == "__main__":
    asyncio.run(main()) 