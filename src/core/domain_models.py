"""
Core domain models for the movie script generation system
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ScriptCharacter(BaseModel):
    """
    Model for character details in the script
    
    @param name - Character name
    @param description - Character description
    @param ageRange - Age range description
    @param perceivedGender - Gender presentation
    @param heightBuild - Physical build description
    @param distinctiveFeatures - Unique physical characteristics
    @param wardrobeDetails - Clothing and accessories
    @param movementStyle - Movement and gestures
    @param keyAccessories - Important props or accessories
    @param sceneSpecificChanges - Costume/appearance changes
    @param imagePrompt - Image generation prompt
    @param role - Optional character role in the story
    """
    name: str
    description: str
    ageRange: str
    perceivedGender: str
    heightBuild: str
    distinctiveFeatures: str
    wardrobeDetails: str
    movementStyle: str
    keyAccessories: str
    sceneSpecificChanges: str
    imagePrompt: str
    role: Optional[str] = None

class Setting(BaseModel):
    """
    Model for setting details
    
    @param id - Unique setting identifier
    @param name - Setting name
    @param description - Detailed description
    @param imagePrompt - Image generation prompt
    @param keyFeatures - List of key visual elements
    @param technicalRequirements - Technical specifications
    """
    id: str
    name: str
    description: str
    imagePrompt: str
    keyFeatures: List[str]
    technicalRequirements: Dict[str, Any]

class ExtractedScene(BaseModel):
    """
    Model for extracted scene details from source material
    
    @param sceneNumber - Scene number in sequence
    @param startTime - Scene start time (MM:SS)
    @param endTime - Scene end time (MM:SS)
    @param shotType - Type of camera shot
    @param cameraMovement - Camera movement description
    @param cameraEquipment - Camera gear used
    @param location - Scene location
    @param lightingSetup - Lighting configuration
    @param colorPalette - List of colors used
    @param visualReferences - List of visual references
    @param characterActions - Map of character names to actions
    @param transitionType - Scene transition type
    @param specialNotes - Additional technical notes
    """
    sceneNumber: int
    startTime: str
    endTime: str
    shotType: str
    cameraMovement: str
    cameraEquipment: str
    location: str
    lightingSetup: Dict[str, Any]
    colorPalette: List[str]
    visualReferences: List[str]
    characterActions: Dict[str, str]
    transitionType: str
    specialNotes: List[str]

class TransformedScene(BaseModel):
    """
    Model for transformed scene details ready for production
    
    @param sceneNumber - Scene number in sequence
    @param description - Scene description
    @param prompt - Scene generation prompt
    @param charactersInScene - List of character names
    @param settingId - Reference to setting
    @param duration - Scene duration in seconds
    @param technicalDetails - Technical specifications
    """
    sceneNumber: int
    description: str
    prompt: str
    charactersInScene: List[str]
    settingId: str
    duration: int
    technicalDetails: Dict[str, Any]

class ScriptMetadata(BaseModel):
    """
    Model for script metadata
    
    @param title - Title of the script
    @param genre_tags - List of genre tags
    @param duration - Total duration in seconds
    @param total_scenes - Total number of scenes
    @param characters - List of characters in the script
    """
    title: str
    genre_tags: List[str]
    duration: Optional[float] = None
    total_scenes: int
    characters: List[ScriptCharacter]

class ExtractedSceneList(BaseModel):
    """
    Model for list of extracted scenes
    
    @param scenes - List of extracted scenes
    """
    scenes: List[ExtractedScene]

class TransformedSceneList(BaseModel):
    """
    Model for list of transformed scenes
    
    @param scenes - List of transformed scenes
    """
    scenes: List[TransformedScene]

class SettingList(BaseModel):
    """
    Model for list of settings
    
    @param settings - List of settings
    """
    settings: List[Setting]

class CharacterList(BaseModel):
    """
    Model for list of characters
    
    @param characters - List of characters
    """
    characters: List[ScriptCharacter] 