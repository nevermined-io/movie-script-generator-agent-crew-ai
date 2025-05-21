"""
Basic example of generating a movie script using MovieScriptGenerator directly.
"""
import os
from dotenv import load_dotenv
from src.core.generator import MovieScriptGenerator

# Load environment variables
load_dotenv(override=True)

def main():
    # Create generator instance
    generator = MovieScriptGenerator()
    
    # Generate a script
    result = generator.generate_script(
        title="The Last Adventure",
        tags=["action", "adventure", "fantasy"],
        idea="A group of explorers discover an ancient temple in the Amazon rainforest that contains a portal to another dimension.",
        lyrics="",  # Optional song lyrics
        duration=30  # 30 seconds for testing
    )
    
    # Print the results
    print("\n=== Generated Script ===")
    print(result["script"])
    
    print("\n=== Extracted Scenes ===")
    for scene in result["scenes"]:
        print(f"\nScene {scene.get('sceneNumber', 'N/A')}:")
        print(f"Description: {scene.get('description', 'N/A')}")
        print(f"Characters: {', '.join(scene.get('characters', []))}")
    
    print("\n=== Characters ===")
    for character in result["characters"]:
        print(f"\n{character.get('name', 'N/A')}:")
        print(f"Role: {character.get('role', 'N/A')}")
        print(f"Description: {character.get('description', 'N/A')}")

if __name__ == "__main__":
    main() 