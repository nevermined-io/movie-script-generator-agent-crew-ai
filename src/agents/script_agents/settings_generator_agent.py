from crewai import Agent
from langchain_openai import ChatOpenAI

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
            llm=ChatOpenAI(
                model_name="gpt-4.1-nano",
                temperature=0.8
            )
        ) 