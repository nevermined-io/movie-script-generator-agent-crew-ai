"""
Unit tests for the ScriptService class
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.script_service import ScriptService

@pytest.fixture
def script_service():
    """
    Create a ScriptService instance with mocked OpenAI client
    """
    with patch('src.core.script_service.AsyncOpenAI') as mock_openai:
        service = ScriptService()
        # Mock the chat completions create method
        service.client.chat.completions.create = AsyncMock()
        yield service

@pytest.mark.asyncio
async def test_generate_script_success(script_service):
    """
    Test successful script generation
    """
    # Mock responses
    outline_response = MagicMock()
    outline_response.choices = [MagicMock(message=MagicMock(content="Test outline"))]
    
    script_response = MagicMock()
    script_response.choices = [MagicMock(message=MagicMock(content="Test script"))]
    
    script_service.client.chat.completions.create.side_effect = [
        outline_response,
        script_response
    ]
    
    # Test data
    prompt = "Write a romantic comedy"
    metadata = {"genre": "romance"}
    
    # Execute
    script, thoughts = await script_service.generate_script(prompt, metadata)
    
    # Verify
    assert script == "Test script"
    assert len(thoughts) == 2
    assert thoughts[0]["type"] == "outline"
    assert thoughts[0]["content"] == "Test outline"
    assert thoughts[1]["type"] == "completion"
    
    # Verify API calls
    assert script_service.client.chat.completions.create.call_count == 2
    
@pytest.mark.asyncio
async def test_generate_script_error(script_service):
    """
    Test script generation with API error
    """
    # Mock error response
    script_service.client.chat.completions.create.side_effect = Exception("API Error")
    
    # Test data
    prompt = "Write a romantic comedy"
    
    # Execute and verify
    with pytest.raises(Exception) as exc_info:
        await script_service.generate_script(prompt)
    assert "Error generating script: API Error" in str(exc_info.value)