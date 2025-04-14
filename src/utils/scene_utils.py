"""
Utility functions for scene duration adjustments and manipulations.
"""
from typing import List, Optional
import random
from src.models import ExtractedScene

def calculate_total_duration(scenes: List[ExtractedScene]) -> float:
    """
    Calculate the total duration of all scenes.

    @param scenes - List of scenes to calculate duration for
    @return Total duration in seconds
    """
    return sum(float(scene.endTime.split(':')[0]) * 60 + float(scene.endTime.split(':')[1]) - 
              (float(scene.startTime.split(':')[0]) * 60 + float(scene.startTime.split(':')[1])) 
              for scene in scenes)

def get_adjustable_scenes(scenes: List[ExtractedScene], target_duration: float, current_duration: float) -> List[ExtractedScene]:
    """
    Get list of scenes that can be adjusted based on target duration.

    @param scenes - List of all scenes
    @param target_duration - Target total duration in seconds
    @param current_duration - Current total duration in seconds
    @return List of scenes that can be adjusted
    """
    if current_duration < target_duration:
        # Get scenes with 5 second duration that can be extended
        return [scene for scene in scenes if abs(
            (float(scene.endTime.split(':')[0]) * 60 + float(scene.endTime.split(':')[1])) -
            (float(scene.startTime.split(':')[0]) * 60 + float(scene.startTime.split(':')[1])) - 5) < 0.1]
    else:
        # Get scenes with 10 second duration that can be shortened
        return [scene for scene in scenes if abs(
            (float(scene.endTime.split(':')[0]) * 60 + float(scene.endTime.split(':')[1])) -
            (float(scene.startTime.split(':')[0]) * 60 + float(scene.startTime.split(':')[1])) - 10) < 0.1]

def adjust_scene_duration(scene: ExtractedScene, new_duration: float) -> None:
    """
    Adjust the duration of a single scene by modifying its end time.

    @param scene - Scene to adjust
    @param new_duration - New duration in seconds
    """
    start_minutes = float(scene.startTime.split(':')[0])
    start_seconds = float(scene.startTime.split(':')[1])
    total_start_seconds = start_minutes * 60 + start_seconds
    total_end_seconds = total_start_seconds + new_duration
    
    end_minutes = int(total_end_seconds // 60)
    end_seconds = total_end_seconds % 60
    scene.endTime = f"{end_minutes:02d}:{end_seconds:05.2f}"

def adjust_scene_durations(scenes: List[ExtractedScene], target_duration: float) -> List[ExtractedScene]:
    """
    Adjust scene durations to match target duration while maintaining 5 or 10 second lengths.
    
    This function modifies scenes in place to match a target duration by converting
    5-second scenes to 10 seconds or vice versa as needed.

    @param scenes - List of scenes to adjust
    @param target_duration - Target total duration in seconds
    @return Modified list of scenes with adjusted durations
    """
    if not scenes:
        return scenes

    # Make a copy to avoid modifying the original list
    adjusted_scenes = scenes.copy()
    
    while True:
        current_duration = calculate_total_duration(adjusted_scenes)
        
        # If we're within 0.1 seconds of target, we're done
        if abs(current_duration - target_duration) < 0.1:
            break
            
        # Get scenes that can be adjusted
        adjustable_scenes = get_adjustable_scenes(adjusted_scenes, target_duration, current_duration)
        
        if not adjustable_scenes:
            break  # No more adjustments possible
            
        # Select a random scene to adjust
        scene_to_adjust = random.choice(adjustable_scenes)
        current_scene_duration = (float(scene_to_adjust.endTime.split(':')[0]) * 60 + float(scene_to_adjust.endTime.split(':')[1])) - \
                               (float(scene_to_adjust.startTime.split(':')[0]) * 60 + float(scene_to_adjust.startTime.split(':')[1]))
        
        # Adjust duration based on current total
        if current_duration < target_duration:
            # Convert 5s to 10s
            adjust_scene_duration(scene_to_adjust, 10.0)
        else:
            # Convert 10s to 5s
            adjust_scene_duration(scene_to_adjust, 5.0)
    
    return adjusted_scenes 