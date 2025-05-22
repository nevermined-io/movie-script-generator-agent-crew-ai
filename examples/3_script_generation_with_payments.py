"""
Example of generating a movie script and processing payments for the session.
"""
import os
from dotenv import load_dotenv
from src.core.generator import MovieScriptGenerator
from src.core.payments import process_payments
import time

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
    
    # Process payments for this session
    print("\n=== Processing Payments ===")
    session_id = result["session_id"]
    agent_ids = list(result["agent_ids"].values())  # Convert dict values to list

    # Wait for 15 seconds to ensure the results are logged by Helicone
    timeout = 15
    print(f"Waiting for {timeout} seconds...")
    time.sleep(timeout)
    
    process_payments(
        agent_ids=agent_ids,
        session_id=session_id,
        limit=50,  # Adjust as needed
        offset=0,
        margin=0.05,  # 5% margin
        usd_to_credit_rate=1000.0  # 1000 credits per USD
    )

if __name__ == "__main__":
    main() 