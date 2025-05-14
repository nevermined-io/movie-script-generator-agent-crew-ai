from crewai import Agent, LLM
from dotenv import load_dotenv
import os

# Load environment variables with override
load_dotenv(override=True)

class SettingsGeneratorAgent:
    """Agent specialized in generating detailed settings for scenes"""
    
    @staticmethod
    def create():
        """
        Creates an agent specialized in generating detailed settings for scenes
        
        Returns:
            Agent: A CrewAI agent for settings generation
        """
        return Agent(
            role='Settings Generator',
            goal='Create detailed and immersive settings for movie scenes',
            backstory="""You are a production designer with extensive experience in 
            creating vivid and detailed settings for movies. You understand how to 
            create environments that enhance the story.""",
            verbose=True,
            allow_delegation=False,
            llm=LLM(
                model="gpt-4.1-nano",
                temperature=0.8,
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
        ) 