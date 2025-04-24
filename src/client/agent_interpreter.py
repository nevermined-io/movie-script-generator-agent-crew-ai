"""
Interpreter for A2A protocol agent cards using OpenAI
"""
import json
import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

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
        @param goal: Our specific goal for the task
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
                content = '\n'.join(content.split('\n')[1:-1])
            if content.startswith('json'):
                content = '\n'.join(content.split('\n')[1:])
                
            # Parse the cleaned response into a dictionary
            task_data = json.loads(content)
            return task_data
            
        except Exception as e:
            raise Exception(f"Failed to create task data: {str(e)}") 