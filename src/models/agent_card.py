"""
Agent Card definition for the Movie Script Generator Agent.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class AgentProvider(BaseModel):
    """Provider information for the agent."""
    organization: str = "Nevermined"
    url: Optional[str] = "https://nevermined.io"

class AgentCapabilities(BaseModel):
    """Capabilities of the agent."""
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = True

class InputParameter(BaseModel):
    """Input parameter definition."""
    name: str
    description: str
    required: bool
    type: str

class OutputSchema(BaseModel):
    """Schema for output artifacts that will be returned by the agent."""
    name: str
    description: str
    mimeType: str
    schema: Dict[str, Any]

class AgentSkill(BaseModel):
    """Skill definition for the agent."""
    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None
    parameters: Optional[List[InputParameter]] = None
    outputSchemas: Optional[List[OutputSchema]] = None

class AgentCard(BaseModel):
    """Agent Card following A2A protocol."""
    name: str = "Movie Script Generator Agent"
    description: str = "AI agent that generates detailed movie scripts based on input parameters, using a crew of specialized AI agents for different aspects of script creation"
    url: str = "http://localhost:8000"
    provider: AgentProvider = AgentProvider()
    version: str = "1.0.0"
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities = AgentCapabilities()
    authentication: Dict[str, Any] = {"schemes": ["public"]}
    defaultInputModes: List[str] = ["text/plain", "application/json"]
    defaultOutputModes: List[str] = ["application/json", "text/plain", "text/markdown"]
    skills: List[AgentSkill] = [
        AgentSkill(
            id="generate-script",
            name="Generate Movie Script",
            description="Generates a detailed movie script with scenes, characters, and technical directions based on provided parameters",
            tags=["movie", "script", "generation", "creative", "screenplay"],
            inputModes=["application/json"],
            outputModes=["application/json", "text/markdown"],
            parameters=[
                InputParameter(
                    name="title",
                    description="The title of the movie",
                    required=True,
                    type="string"
                ),
                InputParameter(
                    name="tags",
                    description="List of genre tags or themes for the movie",
                    required=True,
                    type="array[string]"
                ),
                InputParameter(
                    name="lyrics",
                    description="Song lyrics or poetic text to inspire the script",
                    required=False,
                    type="string"
                ),
                InputParameter(
                    name="idea",
                    description="Brief description or concept for the movie",
                    required=True,
                    type="string"
                ),
                InputParameter(
                    name="duration",
                    description="Approximate duration of the movie in minutes",
                    required=False,
                    type="integer"
                )
            ],
            outputSchemas=[
                OutputSchema(
                    name="scriptText",
                    description="The complete script text with scene descriptions, technical directions, and character actions",
                    mimeType="text/plain",
                    schema={"type": "string"}
                ),
                OutputSchema(
                    name="movieMetadata",
                    description="Metadata about the movie, including title, genre tags, duration, scene count and characters",
                    mimeType="application/json",
                    schema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "genre_tags": {"type": "array", "items": {"type": "string"}},
                            "duration": {"type": "number"},
                            "total_scenes": {"type": "integer"},
                            "characters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "ageRange": {"type": "string"},
                                        "perceivedGender": {"type": "string"},
                                        "heightBuild": {"type": "string"},
                                        "distinctiveFeatures": {"type": "string"},
                                        "wardrobeDetails": {"type": "string"},
                                        "movementStyle": {"type": "string"},
                                        "keyAccessories": {"type": "string"},
                                        "sceneSpecificChanges": {"type": "string"},
                                        "imagePrompt": {"type": "string"},
                                        "role": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                ),
                OutputSchema(
                    name="extractedScenes",
                    description="Scene-by-scene breakdown with timing, shot types, transitions, and character actions",
                    mimeType="application/json",
                    schema={
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sceneNumber": {"type": "integer"},
                                "startTime": {"type": "string"},
                                "endTime": {"type": "string"},
                                "shotType": {"type": "string"},
                                "cameraMovement": {"type": "string"},
                                "cameraEquipment": {"type": "string"},
                                "location": {"type": "string"},
                                "lightingSetup": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"},
                                        "description": {"type": "string"}
                                    }
                                },
                                "colorPalette": {"type": "array", "items": {"type": "string"}},
                                "visualReferences": {"type": "array", "items": {"type": "string"}},
                                "characterActions": {"type": "object", "additionalProperties": {"type": "string"}},
                                "transitionType": {"type": "string"},
                                "specialNotes": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                ),
                OutputSchema(
                    name="transformedScenes",
                    description="Transformed scenes with prompts suitable for AI-based image/video generation",
                    mimeType="application/json",
                    schema={
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sceneNumber": {"type": "integer"},
                                "prompt": {"type": "string"},
                                "charactersInScene": {"type": "array", "items": {"type": "string"}},
                                "settingId": {"type": "string"},
                                "duration": {"type": "integer"},
                                "technicalDetails": {
                                    "type": "object",
                                    "properties": {
                                        "shotType": {"type": "string"},
                                        "cameraMovement": {"type": "string"},
                                        "lens": {"type": "string"},
                                        "cameraGear": {"type": "string"},
                                        "lighting": {"type": "string"},
                                        "colorPalette": {"type": "array", "items": {"type": "string"}},
                                        "timeOfDay": {"type": "string"}
                                    },
                                    "required": ["colorPalette"]
                                }
                            }
                        }
                    }
                )
            ],
            examples=[
                "Generate a script for a 90-minute sci-fi thriller about artificial intelligence",
                "Create a romantic comedy script based on song lyrics about missed connections"
            ]
        )
    ]

# Create a singleton instance of the agent card
AGENT_CARD = AgentCard() 