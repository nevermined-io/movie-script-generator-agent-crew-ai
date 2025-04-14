"""
Tasks module for the movie script generation system
"""

from .script_tasks import ScriptTasks

# Export task factory methods
generate_script = ScriptTasks.generate_script
extract_scenes = ScriptTasks.extract_scenes
generate_settings = ScriptTasks.generate_settings
extract_characters = ScriptTasks.extract_characters
transform_scenes = ScriptTasks.transform_scenes 