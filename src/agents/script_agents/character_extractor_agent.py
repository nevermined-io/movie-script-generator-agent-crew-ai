from crewai import Agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

# Load environment variables with override
load_dotenv(override=True)

class CharacterExtractorAgent:
    """Agent specialized in extracting and developing characters"""
    
    @staticmethod
    def create():
        """
        Creates an agent specialized in extracting and developing characters
        
        Returns:
            Agent: A CrewAI agent for character extraction and development
        """
        return Agent(
            role='Character Analyst',
            goal='Extract and develop detailed character profiles from scripts',
            backstory="""You are a character development specialist who excels at 
            analyzing and extracting character details from scripts. You understand 
            character motivations, arcs, and relationships.""",
            verbose=True,
            allow_delegation=False,
            llm=ChatOpenAI(
                model_name="gpt-4.1-nano",
                temperature=0.7,
                base_url="https://oai.helicone.ai/v1",
                default_headers={
                    "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}"
                }
            )
        ) 