from crewai import Agent
from langchain_openai import ChatOpenAI
from src.tools.scene_tools import AdjustSceneDurationsTool
from dotenv import load_dotenv
import os

# Load environment variables with override
load_dotenv(override=True)

class SceneTransformerAgent:
    """Agent specialized in transforming scene descriptions into detailed formats"""
    
    @staticmethod
    def create(llm=None):
        """
        Creates an agent specialized in transforming scene descriptions
        
        @param llm - Language model to use. Defaults to ChatOpenAI with gpt-4.1-nano
        @return Agent: A CrewAI agent for scene transformation
        """
        if llm is None:
            llm = ChatOpenAI(
                model_name="gpt-4.1-nano",
                temperature=0.9,
                base_url="https://oai.helicone.ai/v1",
                default_headers={
                    "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}"
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