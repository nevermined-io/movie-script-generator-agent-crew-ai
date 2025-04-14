from crewai import Agent
from langchain_openai import ChatOpenAI
from src.tools.scene_tools import AdjustSceneDurationsTool

class SceneTransformerAgent:
    """Agent specialized in transforming scene descriptions into detailed formats"""
    
    @staticmethod
    def create(llm=None):
        """
        Creates an agent specialized in transforming scene descriptions
        
        @param llm - Language model to use. Defaults to ChatOpenAI with gpt-4o-mini
        @return Agent: A CrewAI agent for scene transformation
        """
        if llm is None:
            llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.9
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