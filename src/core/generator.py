"""
Core functionality for generating movie scripts using AI agents
"""

from typing import Dict, Any
from crewai import Agent, Crew, Task, LLM
from langchain_openai import ChatOpenAI
from src.tasks.script_tasks import ScriptTasks
from src.agents.script_agents.script_writer_agent import ScriptWriterAgent
from src.agents.script_agents.scene_transformer_agent import SceneTransformerAgent
from src.utils.logger import logger
from crewai.process import Process
import json
import math
import traceback
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from dotenv import load_dotenv

# Load environment variables with override
load_dotenv(override=True)

class MovieScriptGenerator:
    """
    Main class for generating movie scripts with technical details
    """
    
    def __init__(self, model_name: str = "gpt-4.1-nano"):
        """
        Initialize the script generator
        
        @param model_name - Name of the LLM model to use
        """
        # self.llm = ChatOpenAI(
        #     model_name=model_name,
        #     temperature=0.9,
        #     request_timeout=60,
        #     max_retries=3,
        #     streaming=False,
        #     openai_api_key=os.getenv("OPENAI_API_KEY"),
        #     model_kwargs={
        #         "extra_headers": {
        #             "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}"
        #         }
        #     },
        #     openai_api_base="https://oai.helicone.ai/v1"
        # )

        self.llm = LLM(
            model=model_name,
            temperature=0.9,
            request_timeout=60,
            max_retries=3,
            stream=True,
            base_url="https://oai.helicone.ai/v1",
            api_key=os.environ.get("OPENAI_API_KEY"),
            extra_headers={
                "Helicone-Auth": f"Bearer {os.environ.get('HELICONE_API_KEY')}",
                "helicone-stream-usage": "true",
            }
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
            # Log start of script generation
            logger.log_script_generation(
                task_id="internal",
                status="generating",
                metadata={
                    "title": title,
                    "tags": tags,
                    "lyrics": lyrics,
                    "idea": idea,
                    "duration": duration
                }
            )

            # Create agents
            script_writer = ScriptWriterAgent.create(self.llm)
            scene_transformer = SceneTransformerAgent.create(self.llm)
            minScenes = math.floor(duration / 10)
            maxScenes = math.floor(duration / 5)
            meanScenes = math.floor((minScenes + maxScenes) / 2)

            # Log agent creation
            logger.log_script_generation(
                task_id="internal",
                status="agents_created",
                metadata={
                    "min_scenes": minScenes,
                    "max_scenes": maxScenes,
                    "mean_scenes": meanScenes
                }
            )

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

            # Log crew kickoff
            logger.log_script_generation(
                task_id="internal",
                status="crew_started",
                metadata={
                    "total_tasks": len(tasks)
                }
            )

            # Execute crew tasks
            result = crew.kickoff()

            # Process results from CrewOutput
            script_result = {
                "script": result.tasks_output[0].raw,  # Script from first task
                "scenes": result.tasks_output[1].json_dict["scenes"],  # Extracted scenes from second task
                "settings": result.tasks_output[2].json_dict["settings"],  # Settings from third task
                "characters": result.tasks_output[3].json_dict["characters"],  # Characters from fourth task
                "transformedScenes": result.tasks_output[4].json_dict["scenes"]  # Transformed scenes from fifth task
            }

            # Log successful generation
            logger.log_script_generation(
                task_id="internal",
                status="generation_complete",
                metadata={
                    "total_scenes": len(script_result["scenes"]),
                    "total_characters": len(script_result["characters"])
                }
            )

            return script_result

        except Exception as e:
            print(traceback.format_exc())
            # Log error
            logger.log_script_generation(
                task_id="internal",
                status="generation_failed",
                metadata={
                    "title": title,
                    "duration": duration
                },
                error=str(e)
            )
            raise 