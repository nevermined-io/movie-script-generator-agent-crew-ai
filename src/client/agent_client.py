"""
A2A protocol client implementation
"""
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .agent_interpreter import AgentCardInterpreter
from .models import TaskStatus, TaskArtifact

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
            
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running task
        
        @param task_id: ID of the task to cancel
        @returns: Cancellation response
        @raises: Exception if request fails or task is in terminal state
        """
        if not self.session:
            raise Exception("Session not initialized. Use async with.")
            
        # Check current status first
        current_status = await self.check_task_status(task_id)
        state = current_status["status"]["state"]
        
        # Can't cancel tasks in terminal states
        if state in {"completed", "failed", "cancelled"}:
            raise Exception(f"Cannot cancel task in {state} state")
            
        # Send cancellation request
        async with self.session.post(
            f"{self.base_url}/tasks/{task_id}/cancel"
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to cancel task: {response.status}")
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
                return task_status
            elif state == "failed":
                error_msg = task_status["status"]["message"]["parts"][0]["text"]
                raise Exception(f"Task failed: {error_msg}")
            elif state == "cancelled":
                raise Exception("Task was canceled")
                
            await asyncio.sleep(self.retry_delay)
            
        raise Exception(f"Task did not complete after {self.max_retries} retries") 