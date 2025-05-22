"""
Core functionality for generating movie scripts using AI agents
"""

from typing import Dict, Any, List, Type
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
import uuid
from datetime import datetime
import inspect

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

    def _get_agent_classes(self) -> List[Type]:
        """
        Get all agent classes from the script_agents module
        
        Returns:
            List[Type]: List of agent classes
        """
        # Import the modules directly
        from src.agents.script_agents.script_writer_agent import ScriptWriterAgent
        from src.agents.script_agents.scene_transformer_agent import SceneTransformerAgent
        
        # Return the known agent classes
        return [ScriptWriterAgent, SceneTransformerAgent]

    def _get_agent_ids(self) -> Dict[str, str]:
        """
        Get agent IDs from all agent classes
        
        Returns:
            Dict[str, str]: Dictionary mapping agent class names to their IDs
        """
        agent_ids = {}
        for agent_class in self._get_agent_classes():
            if hasattr(agent_class, 'agent_id'):
                agent_ids[agent_class.__name__] = agent_class.agent_id
        return agent_ids

    def _log_session_info(self, session_id: str, agent_ids: Dict[str, str]):
        """
        Log session and agent IDs to a timestamped file
        
        Args:
            session_id (str): The session ID
            agent_ids (Dict[str, str]): Dictionary of agent names and their IDs
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join("src", "logs", f"session_{timestamp}.txt")
        
        log_content = f"Session ID: {session_id}\n"
        log_content += "Agent IDs:\n"
        for agent_name, agent_id in agent_ids.items():
            log_content += f"{agent_name}: {agent_id}\n"
            
        with open(log_file, "w") as f:
            f.write(log_content)

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
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create agents with session ID
            script_writer = ScriptWriterAgent.create(sessionId=session_id)
            scene_transformer = SceneTransformerAgent.create(sessionId=session_id)
            
            # Log session and agent IDs
            agent_ids = self._get_agent_ids()
            self._log_session_info(session_id, agent_ids)
            
            minScenes = math.floor(duration / 10)
            maxScenes = math.floor(duration / 5)
            meanScenes = math.floor((minScenes + maxScenes) / 2)

            # Log start of script generation
            logger.log_script_generation(
                task_id="internal",
                status="generating",
                metadata={
                    "title": title,
                    "tags": tags,
                    "lyrics": lyrics,
                    "idea": idea,
                    "duration": duration,
                    "session_id": session_id
                }
            )

            # Log agent creation
            logger.log_script_generation(
                task_id="internal",
                status="agents_created",
                metadata={
                    "min_scenes": minScenes,
                    "max_scenes": maxScenes,
                    "mean_scenes": meanScenes,
                    "session_id": session_id
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
                    "total_tasks": len(tasks),
                    "session_id": session_id
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
                "transformedScenes": result.tasks_output[4].json_dict["scenes"],  # Transformed scenes from fifth task
                "session_id": session_id,  # Add session ID
                "agent_ids": agent_ids  # Add agent IDs
            }

            # Log successful generation
            logger.log_script_generation(
                task_id="internal",
                status="generation_complete",
                metadata={
                    "total_scenes": len(script_result["scenes"]),
                    "total_characters": len(script_result["characters"]),
                    "session_id": session_id
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
                    "duration": duration,
                    "session_id": session_id if 'session_id' in locals() else None
                },
                error=str(e)
            )
            raise 