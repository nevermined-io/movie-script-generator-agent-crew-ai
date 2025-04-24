"""
Domain models for the movie script generation system
"""

from src.core.domain_models import (
    ExtractedScene,
    TransformedScene,
    Setting,
    ScriptCharacter as CharacterDetail,  # Alias for backward compatibility
    ScriptMetadata,
    ExtractedSceneList,
    SettingList,
    CharacterList as CharacterDetailList,  # Alias for backward compatibility
    TransformedSceneList
) 