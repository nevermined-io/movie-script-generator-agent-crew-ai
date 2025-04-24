"""
Unit tests for the ScriptService class
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.script_service import ScriptService
import json

@pytest.fixture
def script_service():
    """
    Create a ScriptService instance with mocked OpenAI client
    
    @returns {ScriptService} A ScriptService instance with mocked OpenAI client
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
    
    @param {ScriptService} script_service - The mocked script service instance
    """
    # Mock responses
    outline_data = {
        "outline": "Test outline",
        "scenes": ["Scene 1", "Scene 2"],
        "metadata": {"genre": "test"}
    }
    script_data = {
        "script": "Test script",
        "scenes": ["Scene 1", "Scene 2"],
        "metadata": {"genre": "test"}
    }
    
    outline_response = MagicMock()
    outline_response.choices = [MagicMock(message=MagicMock(content=json.dumps(outline_data)))]
    
    script_response = MagicMock()
    script_response.choices = [MagicMock(message=MagicMock(content=json.dumps(script_data)))]
    
    script_service.client.chat.completions.create.side_effect = [
        outline_response,
        script_response
    ]
    
    # Test data
    prompt = {
        "title": "Test Movie",
        "tags": ["test"],
        "idea": "A test movie",
        "lyrics": None,
        "duration": 60
    }
    
    # Execute
    result = await script_service.generate_script(prompt)
    
    # Verify
    assert isinstance(result, tuple)
    script_result, thoughts = result
    
    # Verify script data - should be a JSON string
    assert isinstance(script_result, str)
    parsed_script = json.loads(script_result)
    assert parsed_script == script_data
    
    # Verify thoughts
    assert isinstance(thoughts, list)
    assert len(thoughts) == 2
    
    # Verify outline thought
    assert thoughts[0]["type"] == "outline"
    assert thoughts[0]["content"] == json.dumps(outline_data)
    
    # Verify completion thought - should be plain text
    assert thoughts[1]["type"] == "completion"
    assert thoughts[1]["content"] == "Script generated successfully"
    
    # Verify API calls
    assert script_service.client.chat.completions.create.call_count == 2
    
@pytest.mark.asyncio
async def test_generate_script_error(script_service):
    """
    Test script generation with API error
    
    @param {ScriptService} script_service - The mocked script service instance
    """
    # Mock error response
    script_service.client.chat.completions.create.side_effect = Exception("API Error")
    
    # Test data
    prompt = {
        "title": "Test Movie",
        "tags": ["test"],
        "idea": "A test movie",
        "lyrics": None,
        "duration": 60
    }
    
    # Execute and verify
    with pytest.raises(Exception) as exc_info:
        await script_service.generate_script(prompt)
    assert "Error generating script: API Error" in str(exc_info.value)