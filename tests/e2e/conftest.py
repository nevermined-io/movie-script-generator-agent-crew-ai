"""
Pytest configuration for end-to-end tests
"""
import pytest
import asyncio
import uvicorn
import multiprocessing
import time
from src.api.app import app

def run_server():
    """Run the FastAPI server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

@pytest.fixture(scope="session", autouse=True)
def server_fixture():
    """
    Fixture to start and stop the FastAPI server
    """
    # Start server in a separate process
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    # Wait for server to start
    time.sleep(2)
    
    yield
    
    # Stop server
    server_process.terminate()
    server_process.join() 