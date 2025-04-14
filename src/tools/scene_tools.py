"""
Tools for scene manipulation and transformation
"""
from typing import Type, List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from src.models import ExtractedScene
from src.utils.scene_utils import adjust_scene_durations as adjust_scenes

class AdjustSceneDurationsInput(BaseModel):
    """Input schema for AdjustSceneDurationsTool."""
    scenes: List[ExtractedScene] = Field(..., description="List of scenes to adjust")
    #target_duration: float = Field(..., description="Target total duration in seconds")

class AdjustSceneDurationsTool(BaseTool):
    """Tool for adjusting scene durations to match a target duration."""
    name: str = "adjust_scene_durations"
    description: str = """
    Adjusts scene durations to match a target duration while maintaining 5 or 10 second lengths.
    This tool modifies scenes in place to match a target duration by converting
    5-second scenes to 10 seconds or vice versa as needed.
    """
    args_schema: Type[BaseModel] = AdjustSceneDurationsInput

    def _run(self, scenes: List[ExtractedScene]) -> str:
        """
        Run the scene duration adjustment tool.

        @param scenes - List of scenes to adjust
        @param target_duration - Target total duration in seconds
        @return Modified list of scenes with adjusted durations
        """
        target_duration: float = 180
        print(f"Adjusting scene durations for {target_duration} seconds")
        print(f"Scenes: {scenes}")
        print("--------------------------------")
        return adjust_scenes(scenes, target_duration) 