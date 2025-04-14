"""
FastAPI routes for the movie script generation system
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
from src.core.generator import MovieScriptGenerator
from src.api.models import ScriptRequest, ScriptResponse

app = FastAPI(
    title="Movie Script Generator API",
    description="API for generating technical movie scripts using AI agents",
    version="1.0.0"
)

@app.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest) -> Dict[str, Any]:
    """
    Generate a movie script with technical details
    """
    try:
        generator = MovieScriptGenerator()  # Using default model
        result = generator.generate_script(
            title=request.title,
            tags=request.tags,
            lyrics=request.lyrics,
            idea=request.idea,
            duration=request.duration
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"} 