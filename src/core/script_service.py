"""
Service for movie script generation and analysis using OpenAI
"""
from typing import Dict, Any, Optional, List, Tuple
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class ScriptService:
    """
    Service for handling movie script generation and analysis tasks
    """
    
    def __init__(self):
        """
        Initialize the script service with OpenAI client
        """
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def generate_script(self, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate a movie script based on the given prompt
        
        Args:
            prompt: User's script requirements
            metadata: Additional parameters for generation
            
        Returns:
            Tuple containing the generated script and thoughts/analysis
        """
        # System message to set the context
        system_msg = """You are an experienced screenwriter. Your task is to generate movie scripts 
        following standard screenplay format. Focus on creating engaging dialogue, clear action 
        descriptions, and proper scene formatting. Include scene headings (sluglines), action 
        descriptions, character names, dialogue, and parentheticals where appropriate."""
        
        try:
            # First get the outline
            outline_response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Create a brief outline for a script based on this prompt: {prompt}"}
                ],
                temperature=0.7
            )
            
            outline = outline_response.choices[0].message.content
            
            # Then generate the full script
            script_response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "assistant", "content": f"Here's the outline I'll use:\n{outline}"},
                    {"role": "user", "content": f"Generate a properly formatted script based on this outline and the original prompt: {prompt}"}
                ],
                temperature=0.7
            )
            
            script = script_response.choices[0].message.content
            
            # Generate analysis and thoughts
            thoughts = [
                {"type": "outline", "content": outline},
                {"type": "completion", "content": "Script generated successfully"}
            ]
            
            return script, thoughts
            
        except Exception as e:
            raise Exception(f"Error generating script: {str(e)}")