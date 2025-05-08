"""
Main entry point for the movie script generation API
"""

import os
from dotenv import load_dotenv
import uvicorn
from api.app import app

# Load environment variables from .env file
load_dotenv()

def main():
    """Start the FastAPI application with uvicorn"""
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    main() 