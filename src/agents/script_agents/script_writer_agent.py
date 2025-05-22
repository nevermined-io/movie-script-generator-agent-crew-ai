from crewai import Agent, LLM
from dotenv import load_dotenv
import os
import uuid

# Load environment variables with override
load_dotenv(override=True)

class ScriptWriterAgent:
    """Agent specialized in generating initial movie scripts"""
    
    # Create a deterministic UUID based on the class name
    agent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ScriptWriterAgent"))
    
    @staticmethod
    def create(llm=None, sessionId=None):
        """
        Creates an agent specialized in generating initial movie scripts
        
        Args:
            llm (BaseChatModel, optional): Language model to use. Defaults to LLM with gpt-4.1-nano.
            sessionId (str, optional): Session identifier for tracking. Defaults to None.
            
        Returns:
            Agent: A CrewAI agent for script writing
        """
        if llm is None:
            llm = LLM(
                model="gpt-4.1-nano",
                temperature=0.9,
                request_timeout=60,
                max_retries=3,
                stream=True,
                base_url="https://oai.helicone.ai/v1",
                api_key=os.environ.get("OPENAI_API_KEY"),
                extra_headers={
                    "Helicone-Auth": f"Bearer {os.environ.get('HELICONE_API_KEY')}",
                    "helicone-stream-usage": "true",
                    "Helicone-Property-AgentId": ScriptWriterAgent.agent_id,
                    "Helicone-Property-SessionId": sessionId if sessionId else "",
                }
            )
            
        return Agent(
            role='Script Writer',
            goal='Generate compelling and creative movie scripts based on given prompts',
            backstory="""You are an experienced screenwriter with a talent for creating 
            engaging and original movie scripts. You understand story structure, character 
            development, and how to create compelling narratives.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        ) 