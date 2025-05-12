from crewai import Agent
from langchain_openai import ChatOpenAI

class ScriptWriterAgent:
    """Agent specialized in generating initial movie scripts"""
    
    @staticmethod
    def create(llm=None):
        """
        Creates an agent specialized in generating initial movie scripts
        
        Args:
            llm (BaseChatModel, optional): Language model to use. Defaults to ChatOpenAI with gpt-4.1-nano.
            
        Returns:
            Agent: A CrewAI agent for script writing
        """
        if llm is None:
            llm = ChatOpenAI(
                model_name="gpt-4.1-nano",
                temperature=0.9
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