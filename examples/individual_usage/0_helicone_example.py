#!/usr/bin/env python3
"""
Example script demonstrating how to use Helicone with both OpenAI and Langchain clients.
Helicone provides observability and cost tracking for OpenAI API calls.
"""

import os
import sys
from typing import Dict, Any
from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_openai_client() -> OpenAI:
    """Configure base OpenAI client with Helicone headers."""
    # Get API keys from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    helicone_api_key = os.getenv("HELICONE_API_KEY")

    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    if not helicone_api_key:
        raise ValueError("HELICONE_API_KEY environment variable is not set")

    # Configure OpenAI client with Helicone
    client = OpenAI(
        api_key=openai_api_key,
        base_url="https://oai.helicone.ai/v1",
        default_headers={
            "Helicone-Auth": f"Bearer {helicone_api_key}"
        }
    )
    return client

def setup_langchain_client(model_name: str = "gpt-4.1-nano") -> ChatOpenAI:
    """Configure Langchain OpenAI client with Helicone headers."""
    # Get API keys from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    helicone_api_key = os.getenv("HELICONE_API_KEY")

    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    if not helicone_api_key:
        raise ValueError("HELICONE_API_KEY environment variable is not set")

    # Configure Langchain OpenAI client with Helicone
    client = ChatOpenAI(
        openai_api_key=openai_api_key,
        model_name=model_name,
        temperature=0.7,
        request_timeout=60,
        max_retries=3,
        streaming=False,
        model_kwargs={
            "extra_headers": {
                "Helicone-Auth": f"Bearer {helicone_api_key}"
            }
        },
        openai_api_base="https://oai.helicone.ai/v1"
    )
    return client

def make_openai_completion(client: OpenAI, prompt: str, model: str = "gpt-4.1-nano") -> Dict[str, Any]:
    """
    Make a completion request using base OpenAI client through Helicone.
    
    Args:
        client: The OpenAI client instance
        prompt: The prompt to send to the model
        model: The model to use for completion
        
    Returns:
        The completion response from the model
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response
    except Exception as e:
        print(f"Error making completion request: {str(e)}")
        sys.exit(1)

def make_langchain_completion(client: ChatOpenAI, prompt: str) -> Dict[str, Any]:
    """
    Make a completion request using Langchain client through Helicone.
    
    Args:
        client: The Langchain OpenAI client instance
        prompt: The prompt to send to the model
        
    Returns:
        The completion response from the model
    """
    try:
        response = client.invoke([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ])
        return response
    except Exception as e:
        print(f"Error making completion request: {str(e)}")
        sys.exit(1)

def main():
    """Main function to demonstrate both OpenAI and Langchain usage with Helicone."""
    try:
        # Test prompt
        prompt = "What is the capital of France?"
        
        # Test with base OpenAI client
        print("\n=== Testing with base OpenAI client ===")
        openai_client = setup_openai_client()
        print(f"\nSending prompt: {prompt}")
        
        openai_response = make_openai_completion(openai_client, prompt)
        print("\nResponse:")
        print(openai_response.choices[0].message.content)
        print("\nOpenAI Metadata:")
        print(f"Request ID: {openai_response.usage.request_id if hasattr(openai_response.usage, 'request_id') else 'N/A'}")
        print(f"Total Tokens: {openai_response.usage.total_tokens}")
        
        # Test with Langchain client
        print("\n=== Testing with Langchain client ===")
        langchain_client = setup_langchain_client()
        print(f"\nSending prompt: {prompt}")
        
        langchain_response = make_langchain_completion(langchain_client, prompt)
        print("\nResponse:")
        print(langchain_response.content)
        print("\nLangchain Metadata:")
        print(f"Additional Kwargs: {langchain_response.additional_kwargs}")
        print(f"Type: {type(langchain_response).__name__}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 