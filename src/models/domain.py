"""
Domain models for the movie script generation system
"""

from typing import List, Dict, Any
from pydantic import BaseModel

class Aesthetic(BaseModel):
    """
    Model for visual aesthetic details
    
    @param colorPalette - Color scheme description
    @param lighting - Lighting setup details
    @param effects - List of visual effects
    """
    colorPalette: str
    lighting: str
    effects: List[str]

class TechnicalDetails(BaseModel):
    """
    Model for technical details of a scene
    
    @param cameraGear - List of camera equipment
    @param visualReferences - List of visual references
    """
    cameraGear: List[str]
    visualReferences: List[str]

class SceneCharacter(BaseModel):
    """
    Model for character details in a scene
    
    @param name - Character name
    @param actions - Character actions in the scene
    @param interaction - Character interactions with others or camera
    """
    name: str
    actions: str
    interaction: str

class ExtractedScene(BaseModel):
    """
    Model for extracted scene details
    
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

class CharacterDetail(BaseModel):
    """
    Model for detailed character information
    
    @param name - Character name
    @param ageRange - Age range description
    @param perceivedGender - Gender presentation
    @param heightBuild - Physical build description
    @param distinctiveFeatures - Unique physical characteristics
    @param wardrobeDetails - Clothing and accessories
    @param movementStyle - Movement and gestures
    @param keyAccessories - Important props or accessories
    @param sceneSpecificChanges - Costume/appearance changes
    @param imagePrompt - Image generation prompt
    """
    name: str
    ageRange: str
    perceivedGender: str
    heightBuild: str
    distinctiveFeatures: str
    wardrobeDetails: str
    movementStyle: str
    keyAccessories: str
    sceneSpecificChanges: str
    imagePrompt: str

class TransformedScene(BaseModel):
    """
    Model for transformed scene details
    
    @param sceneNumber - Scene number in sequence
    @param prompt - Scene generation prompt
    @param charactersInScene - List of character names
    @param settingId - Reference to setting
    @param duration - Scene duration in seconds
    @param technicalDetails - Technical specifications
    """
    sceneNumber: int
    prompt: str
    charactersInScene: List[str]
    settingId: str
    duration: int
    technicalDetails: Dict[str, Any]

class ExtractedSceneList(BaseModel):
    """
    Model for extracted scene details
    """
    scenes: List[ExtractedScene]
    
class SettingList(BaseModel):
    """
    Model for setting details
    """
    settings: List[Setting]
    
class CharacterDetailList(BaseModel):
    """
    Model for detailed character information
    """
    characters: List[CharacterDetail]
    
class TransformedSceneList(BaseModel):
    """
    Model for transformed scene details
    """
    transformedScenes: List[TransformedScene] 