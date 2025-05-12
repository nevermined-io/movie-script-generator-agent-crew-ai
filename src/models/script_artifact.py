"""
Script artifact models for A2A protocol integration.
"""
from typing import List
from src.models.task import Artifact, TextPart, InlineDataPart
from src.core.domain_models import ExtractedScene, TransformedScene, ScriptMetadata
import json

def create_script_artifact(
    script_text: str,
    scenes: List[ExtractedScene],
    transformed_scenes: List[TransformedScene],
    metadata: ScriptMetadata
) -> Artifact:
    """
    Creates an A2A artifact from a generated script.
    
    Args:
        script_text (str): The complete script text
        scenes (List[ExtractedScene]): List of extracted scenes
        transformed_scenes (List[TransformedScene]): List of transformed scenes
        metadata (ScriptMetadata): Script metadata
        
    Returns:
        Artifact: The A2A protocol compliant artifact
    """
    # Create the main script text part
    script_part = TextPart(
        type="text",
        text=script_text,
        metadata={
            "name": "scriptText",
            "description": "The complete script text with scene descriptions, technical directions, and character actions",
            "mimeType": "text/plain"
        }
    )
    
    # Create the metadata part as inline data
    metadata_part = InlineDataPart(
        type="inline-data",
        mimeType="application/json",
        data=metadata.model_dump_json(),
        metadata={
            "name": "movieMetadata",
            "description": "Metadata about the movie, including title, genre tags, duration, scene count and characters"
        }
    )
    
    # Create the extracted scenes part as inline data - directly as array
    extracted_scenes_part = InlineDataPart(
        type="inline-data",
        mimeType="application/json",
        data=json.dumps([scene.model_dump() for scene in scenes]),
        metadata={
            "name": "extractedScenes",
            "description": "Scene-by-scene breakdown with timing, shot types, transitions, and character actions"
        }
    )
    
    # Create the transformed scenes part as inline data - directly as array
    transformed_scenes_part = InlineDataPart(
        type="inline-data",
        mimeType="application/json",
        data=json.dumps([scene.model_dump() for scene in transformed_scenes]),
        metadata={
            "name": "transformedScenes",
            "description": "Transformed scenes with prompts suitable for AI-based image/video generation"
        }
    )
    
    return Artifact(
        name=metadata.title,
        description=f"Movie script for {metadata.title}",
        parts=[script_part, metadata_part, extracted_scenes_part, transformed_scenes_part],
        metadata={
            "genre_tags": metadata.genre_tags,
            "total_scenes": metadata.total_scenes,
            "duration": metadata.duration
        }
    ) 