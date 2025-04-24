"""
Test fixtures for API tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
import asyncio
from src.api.app import app
from src.core.generator import MovieScriptGenerator
from src.models.task import TaskState, TaskStatus, Message, TextPart, Artifact
from src.models.a2a import Task, TaskSendParams
import os
from dotenv import load_dotenv

# Load environment variables from .env file at the start of testing
load_dotenv()

@pytest.fixture
def test_client():
    """
    Create a test client for the FastAPI application.
    
    Returns:
        TestClient: A FastAPI test client instance
    """
    return TestClient(app)

@pytest.fixture
def mock_movie_script_generator():
    """
    Create a mock movie script generator with predefined return values.
    
    Returns:
        MagicMock: A mock instance of MovieScriptGenerator with configured responses
    """
    generator = MagicMock(spec=MovieScriptGenerator)
    async def mock_generate():
        return {
            "transformedScenes": [],
            "settings": [],
            "characters": [],
            "script": "Test script"
        }
    generator.generate_script = AsyncMock(side_effect=mock_generate)
    return generator

@pytest.fixture
def mock_task_processor():
    """
    Create a mock task processor that simulates task operations.
    
    Returns:
        MagicMock: A mock task processor with configured methods
    """
    processor = MagicMock()
    
    # Store tasks in memory
    processor.tasks = {}
    
    # Configure get_task
    def mock_get_task(task_id: str):
        if task_id in processor.tasks:
            return processor.tasks[task_id]
        task = Task(
            id=task_id,
            status=TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Task completed")]
                )
            )
        )
        return task
    processor.get_task = mock_get_task
    
    # Configure process_task (non-streaming)
    async def mock_process_task(task_params):
        if isinstance(task_params, dict):
            params = TaskSendParams(**task_params)
            task = Task.from_params(params)
        else:
            task = task_params
            
        # Store initial task
        processor.tasks[task.id] = task
        
        # Simulate background processing
        async def update_task_status():
            await asyncio.sleep(0.1)  # Small delay to simulate processing
            task.status = TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Generating movie script...")]
                )
            )
            await asyncio.sleep(0.1)  # Small delay to simulate completion
            task.status = TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Movie script generated successfully")]
                )
            )
        
        # Start background processing
        asyncio.create_task(update_task_status())
        
        return task
        
    processor.process_task = AsyncMock(side_effect=mock_process_task)
    
    # Configure process_task_stream for streaming success case
    async def mock_process_task_stream_success(task_params):
        if isinstance(task_params, dict):
            params = TaskSendParams(**task_params)
            task = Task.from_params(params)
        else:
            task = task_params
            
        # Store initial task
        processor.tasks[task.id] = task
        yield task.to_dict()
            
        # Yield working status after a small delay
        await asyncio.sleep(0.1)
        working_task = Task(
            id=task.id,
            sessionId=task.sessionId,
            status=TaskStatus(
                state=TaskState.WORKING,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Generating movie script...")]
                )
            )
        )
        processor.tasks[task.id] = working_task
        yield working_task.to_dict()
        
        # Yield completed status with artifacts after another delay
        await asyncio.sleep(0.1)
        completed_task = Task(
            id=task.id,
            sessionId=task.sessionId,
            status=TaskStatus(
                state=TaskState.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Movie script generated successfully")]
                )
            ),
            artifacts=[
                Artifact(
                    name="script",
                    description="Generated script",
                    parts=[TextPart(type="text", text="Generated test script")]
                ),
                Artifact(
                    name="characters",
                    description="Character list",
                    parts=[TextPart(type="text", text='["Character 1", "Character 2"]')]
                ),
                Artifact(
                    name="settings",
                    description="Settings list",
                    parts=[TextPart(type="text", text='["Setting 1", "Setting 2"]')]
                )
            ]
        )
        processor.tasks[task.id] = completed_task
        yield completed_task.to_dict()
    
    # Configure process_task_stream for streaming error case
    async def mock_process_task_stream_error(task_params):
        if isinstance(task_params, dict):
            params = TaskSendParams(**task_params)
            task = Task.from_params(params)
        else:
            task = task_params
            
        # Store initial task
        processor.tasks[task.id] = task
        yield task.to_dict()
        
        # Yield error status after a delay
        await asyncio.sleep(0.1)
        error_task = Task(
            id=task.id,
            sessionId=task.sessionId,
            status=TaskStatus(
                state=TaskState.FAILED,
                timestamp=datetime.utcnow().isoformat(),
                message=Message(
                    role="assistant",
                    parts=[TextPart(type="text", text="Failed to generate movie script: Invalid parameters provided")]
                )
            )
        )
        processor.tasks[task.id] = error_task
        yield error_task.to_dict()
    
    # Default to success case
    processor.process_task_stream = mock_process_task_stream_success
    
    # Store error case for tests that need it
    processor.mock_process_task_stream_error = mock_process_task_stream_error
    
    return processor 