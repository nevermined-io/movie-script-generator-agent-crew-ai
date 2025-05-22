from crewai import Agent, LLM
from dotenv import load_dotenv
import os
import uuid

# Load environment variables with override
load_dotenv(override=True)

class SceneExtractorAgent:
    """Agent specialized in extracting and organizing scenes from scripts"""
    
    # Create a deterministic UUID based on the class name
    agent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "SceneExtractorAgent"))
    
    @staticmethod
    def create(llm=None, sessionId=None):
        """
        Creates an agent specialized in extracting and organizing scenes from scripts
        
        Args:
            llm (BaseChatModel, optional): Language model to use. Defaults to LLM with gpt-4.1-nano.
            sessionId (str, optional): Session identifier for tracking. Defaults to None.
            
        Returns:
            Agent: A CrewAI agent for scene extraction
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
                    "Helicone-Property-AgentId": SceneExtractorAgent.agent_id,
                    "Helicone-Property-SessionId": sessionId if sessionId else "",
                }
            )
            
        return Agent(
            role='Scene Extractor',
            goal='Extract and organize scenes from movie scripts into a structured format',
            backstory="""You are a script analyst specialized in breaking down scripts 
            into their component scenes. You have a keen eye for scene structure and 
            can identify key elements in each scene.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        ) 