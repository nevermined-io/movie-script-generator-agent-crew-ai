"""
Example of using individual agents separately.
"""
import os
from dotenv import load_dotenv
from crewai import Task
from src.agents.script_agents.script_writer_agent import ScriptWriterAgent
from src.agents.script_agents.scene_transformer_agent import SceneTransformerAgent
from src.agents.script_agents.settings_generator_agent import SettingsGeneratorAgent
from src.agents.script_agents.character_extractor_agent import CharacterExtractorAgent

# Load environment variables
load_dotenv(override=True)

def main():
    # Create individual agents
    script_writer = ScriptWriterAgent.create()
    scene_transformer = SceneTransformerAgent.create()
    settings_generator = SettingsGeneratorAgent.create()
    character_extractor = CharacterExtractorAgent.create()
    
    # Example script to work with
    sample_script = """
    INT. ANCIENT TEMPLE - DAY
    
    A group of EXPLORERS cautiously enters the dimly lit chamber.
    DR. SARAH CHEN (40s, archaeologist) leads the way, her flashlight
    illuminating ancient hieroglyphs on the walls.
    
    DR. CHEN
    (whispering)
    These symbols... they're unlike anything I've seen before.
    
    JAMES WILSON (30s, photographer) raises his camera, capturing
    the mysterious inscriptions.
    """
    
    # Create tasks for each agent
    script_task = Task(
        description="Generate a complete movie script about an archaeological discovery",
        agent=script_writer
    )
    
    scene_task = Task(
        description="Transform this scene into detailed technical specifications",
        agent=scene_transformer
    )
    
    settings_task = Task(
        description="Generate detailed setting descriptions for an ancient temple",
        agent=settings_generator
    )
    
    character_task = Task(
        description="Extract and develop character profiles from the script",
        agent=character_extractor
    )
    
    # Execute tasks (in a real scenario, you would use CrewAI's execution)
    print("\n=== Script Writer Task ===")
    print("Task Description:", script_task.description)
    print("Agent Role:", script_writer.role)
    
    print("\n=== Scene Transformer Task ===")
    print("Task Description:", scene_task.description)
    print("Agent Role:", scene_transformer.role)
    
    print("\n=== Settings Generator Task ===")
    print("Task Description:", settings_task.description)
    print("Agent Role:", settings_generator.role)
    
    print("\n=== Character Extractor Task ===")
    print("Task Description:", character_task.description)
    print("Agent Role:", character_extractor.role)

if __name__ == "__main__":
    main() 