"""
Main entry point for the movie script generation API
"""

import uvicorn
from api.app import app

def main():
    """Start the FastAPI application with uvicorn"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main() 