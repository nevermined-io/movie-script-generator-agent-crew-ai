"""
Agent Card definition for the Movie Script Generator Agent.
"""
from typing import List, Optional, Dict
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

class AgentCard(BaseModel):
    """Agent Card following A2A protocol."""
    name: str = "Movie Script Generator Agent"
    description: str = "AI agent that generates detailed movie scripts based on input parameters, using a crew of specialized AI agents for different aspects of script creation"
    url: str = "http://localhost:8000"
    provider: AgentProvider = AgentProvider()
    version: str = "1.0.0"
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities = AgentCapabilities()
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
            examples=[
                "Generate a script for a 90-minute sci-fi thriller about artificial intelligence",
                "Create a romantic comedy script based on song lyrics about missed connections"
            ]
        )
    ]

# Create a singleton instance of the agent card
AGENT_CARD = AgentCard() 