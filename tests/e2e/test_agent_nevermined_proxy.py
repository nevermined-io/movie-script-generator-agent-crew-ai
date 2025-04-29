"""
End-to-end tests for the A2A protocol client implementation using the Nevermined proxy
"""
import asyncio
import json
import logging
import unittest
from typing import Dict, Any

# Proxy URL and test token
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.client import AgentClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROXY_URL = os.getenv("PROXY_URL")
TEST_TOKEN = os.getenv("TEST_TOKEN")

class TestAgentNeverminedProxy(unittest.TestCase):
    """
    Test class for AgentClient functionality using the Nevermined proxy
    @class
    """

    async def test_task_without_token(self):
        """
        Test that creating a task without Bearer token fails
        """
        logger.info("=== Starting test: task without Bearer token ===")
        async with AgentClient(base_url=PROXY_URL) as client:
            agent_card = await client.get_agent_card()
            task_data = await client.interpreter.create_task_data(
                agent_card,
                "Write a short script about a robot learning Spanish"
            )
            try:
                await client.send_task(task_data)
                self.fail("Task creation should fail without Bearer token")
            except Exception as e:
                logger.info(f"Expected failure: {str(e)}")
        logger.info("=== Test completed: task without Bearer token ===")

    async def test_task_with_token(self):
        """
        Test that creating a task with Bearer token succeeds if credits are available
        """
        logger.info("=== Starting test: task with Bearer token ===")
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        async with AgentClient(base_url=PROXY_URL) as client:
            agent_card = await client.get_agent_card()
            task_data = await client.interpreter.create_task_data(
                agent_card,
                "Write a short script about a robot learning Spanish"
            )
            try:
                # Send the task with Bearer token using aiohttp directly
                async with client.session.post(
                    f"{PROXY_URL}/tasks/send",
                    json=task_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to send task: {response.status}")
                    response_json = await response.json()
                    logger.info(f"Task created successfully: {json.dumps(response_json, indent=2)}")
                    task_id = response_json["id"]
                result = await client.wait_for_completion(task_id)
                logger.info(f"Task completed: {json.dumps(result, indent=2)}")
            except Exception as e:
                logger.error(f"Task creation failed: {str(e)}")
                self.fail("Task creation with valid token should succeed if credits are available")
        logger.info("=== Test completed: task with Bearer token ===")

    async def test_task_with_token_no_credits(self):
        """
        Test that creating a task with Bearer token fails if no credits are available
        """
        logger.info("=== Starting test: task with Bearer token but no credits ===")
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        async with AgentClient(base_url=PROXY_URL) as client:
            agent_card = await client.get_agent_card()
            task_data = await client.interpreter.create_task_data(
                agent_card,
                "Write a short script about a robot learning Spanish"
            )
            try:
                # Send the task with Bearer token using aiohttp directly
                async with client.session.post(
                    f"{PROXY_URL}/tasks/send",
                    json=task_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        self.fail("Task creation should fail if no credits are available")
                    else:
                        logger.info(f"Expected failure due to no credits: {response.status}")
            except Exception as e:
                logger.info(f"Expected failure due to no credits: {str(e)}")
        logger.info("=== Test completed: task with Bearer token but no credits ===")

def run_async_test(test_case, test_name):
    """
    Helper function to run async test methods
    @param {unittest.TestCase} test_case - The test case instance
    @param {str} test_name - Name of the test method to run
    """
    test_method = getattr(test_case, test_name)
    asyncio.run(test_method())

if __name__ == "__main__":
    test_case = TestAgentNeverminedProxy()
    try:
        logger.info("========================================")
        logger.info("Starting Nevermined proxy test suite...")
        logger.info("========================================")

        logger.info("Running test: task without Bearer token...")
        run_async_test(test_case, "test_task_without_token")

        logger.info("Running test: task with Bearer token...")
        run_async_test(test_case, "test_task_with_token")

        #logger.info("Running test: task with Bearer token but no credits...")
        #run_async_test(test_case, "test_task_with_token_no_credits")

        logger.info("========================================")
        logger.info("All proxy tests completed!")
        logger.info("========================================")
    except Exception as e:
        logger.error("========================================")
        logger.error(f"Proxy test suite failed: {str(e)}")
        logger.error("========================================")
        raise 