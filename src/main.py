"""
Main entry point for the movie script generation API
"""

import uvicorn
from src.api.routes import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 