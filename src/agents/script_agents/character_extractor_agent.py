from crewai import Agent, LLM
from dotenv import load_dotenv
import os
import uuid

# Load environment variables with override
load_dotenv(override=True)

class CharacterExtractorAgent:
    """Agent specialized in extracting and developing characters"""
    
    # Create a deterministic UUID based on the class name
    agent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "CharacterExtractorAgent"))
    
    @staticmethod
    def create(llm=None):
        """
        Creates an agent specialized in extracting and developing characters
        
        Args:
            llm (BaseChatModel, optional): Language model to use. Defaults to LLM with gpt-4.1-nano.
            
        Returns:
            Agent: A CrewAI agent for character extraction and development
        """
        if llm is None:
            llm = LLM(
                model="gpt-4.1-nano",
                temperature=0.7,
                request_timeout=60,
                max_retries=3,
                stream=True,
                base_url="https://oai.helicone.ai/v1",
                api_key=os.environ.get("OPENAI_API_KEY"),
                extra_headers={
                    "Helicone-Auth": f"Bearer {os.environ.get('HELICONE_API_KEY')}",
                    "helicone-stream-usage": "true",
                    "Helicone-Property-AgentId": CharacterExtractorAgent.agent_id,
                }
            )
            
        return Agent(
            role='Character Analyst',
            goal='Extract and develop detailed character profiles from scripts',
            backstory="""You are a character development specialist who excels at 
            analyzing and extracting character details from scripts. You understand 
            character motivations, arcs, and relationships.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        ) 