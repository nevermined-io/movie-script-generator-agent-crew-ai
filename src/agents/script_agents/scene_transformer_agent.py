from crewai import Agent, LLM
from src.tools.scene_tools import AdjustSceneDurationsTool
from dotenv import load_dotenv
import os
import uuid

# Load environment variables with override
load_dotenv(override=True)

class SceneTransformerAgent:
    """Agent specialized in transforming scene descriptions into detailed formats"""
    
    # Create a deterministic UUID based on the class name
    agent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "SceneTransformerAgent"))
    
    @staticmethod
    def create(llm=None, sessionId=None):
        """
        Creates an agent specialized in transforming scene descriptions
        
        Args:
            llm (BaseChatModel, optional): Language model to use. Defaults to LLM with gpt-4.1-nano.
            sessionId (str, optional): Session identifier for tracking. Defaults to None.
            
        Returns:
            Agent: A CrewAI agent for scene transformation
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
                    "Helicone-Property-AgentId": SceneTransformerAgent.agent_id,
                    "Helicone-Property-SessionId": sessionId if sessionId else "",
                }
            )
            
        return Agent(
            role='Scene Transformer',
            goal='Transform scene descriptions into detailed technical formats with camera angles, lighting, and transitions',
            backstory="""You are a technical director with extensive experience in 
            translating creative scene descriptions into detailed technical specifications. 
            You understand camera work, lighting, and scene transitions.""",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            #tools=[AdjustSceneDurationsTool(result_as_answer=True)]
        ) 