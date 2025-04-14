"""
Core functionality for generating movie scripts using AI agents
"""

from typing import Dict, Any
from crewai import Agent, Crew, Task
from langchain_openai import ChatOpenAI
from src.tasks.script_tasks import ScriptTasks
from src.agents.script_agents.script_writer_agent import ScriptWriterAgent
from src.agents.script_agents.scene_transformer_agent import SceneTransformerAgent
from crewai.process import Process
import json
import math
from tenacity import retry, stop_after_attempt, wait_exponential

class MovieScriptGenerator:
    """
    Main class for generating movie scripts with technical details
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the script generator
        
        @param model_name - Name of the LLM model to use
        """
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.9,
            request_timeout=60,
            max_retries=3,
            streaming=True
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_script(self, title: str, tags: str, lyrics: str, idea: str, duration: int = 180) -> Dict[str, Any]:
        """
        Generate a complete movie script with technical details
        
        @param title - Title of the movie/video
        @param tags - Style tags for the content
        @param lyrics - Song lyrics if applicable
        @param idea - Basic concept/idea for the video
        @param duration - Duration in seconds
        @return Dictionary containing the complete script details
        """
        try:
            # Create agents
            script_writer = ScriptWriterAgent.create(self.llm)
            scene_transformer = SceneTransformerAgent.create(self.llm)
            minScenes = math.floor(duration / 10)
            maxScenes = math.floor(duration / 5)
            meanScenes = math.floor((minScenes + maxScenes) / 2)

            # Create tasks with assigned agents
            tasks = [
                ScriptTasks.generate_script(title, tags, lyrics, idea, script_writer, duration, meanScenes),
                ScriptTasks.extract_scenes(scene_transformer),
                ScriptTasks.generate_settings(scene_transformer),
                ScriptTasks.extract_characters(script_writer),
                ScriptTasks.transform_scenes(scene_transformer)
            ]

            # Create crew and process
            crew = Crew(
                agents=[script_writer, scene_transformer],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )

            # Execute and get initial result
            result = crew.kickoff()
            
            # Access results through the CrewOutput object
            # Each task has a name based on the static method that created it
            script_result = result.tasks_output[0].raw
            scenes_result = result.tasks_output[1].json_dict['scenes']
            settings_result = result.tasks_output[2].json_dict['settings']
            characters_result = result.tasks_output[3].json_dict['characters']
            transformed_scenes_result = result.tasks_output[4].json_dict['transformedScenes']
            
            return {
                "script": script_result,
                "scenes": scenes_result,
                "settings": settings_result,
                "characters": characters_result,
                "transformedScenes": transformed_scenes_result
            }
        except Exception as e:
            print(f"Error during script generation: {str(e)}")
            raise 