"""
Example of creating a custom crew with specific agents and tasks.
"""
import os
from dotenv import load_dotenv
from crewai import Crew, Task, Process
from src.agents.script_agents.script_writer_agent import ScriptWriterAgent
from src.agents.script_agents.scene_transformer_agent import SceneTransformerAgent
from src.tasks.script_tasks import ScriptTasks

# Load environment variables
load_dotenv(override=True)

def main():
    # Create agents
    script_writer = ScriptWriterAgent.create()
    scene_transformer = SceneTransformerAgent.create()
    
    # Create tasks using the ScriptTasks factory
    tasks = [
        ScriptTasks.generate_script(
            title="The Hidden Portal",
            tags=["sci-fi", "adventure"],
            lyrics="",
            idea="A scientist discovers a way to communicate with parallel universes through quantum computing.",
            agent=script_writer,
            duration=30,  # 30 seconds for testing
            mean_scenes=6  # Reduced number of scenes for shorter duration
        ),
        ScriptTasks.transform_scenes(scene_transformer)
    ]
    
    # Create a custom crew
    crew = Crew(
        agents=[script_writer, scene_transformer],
        tasks=tasks,
        process=Process.sequential,  # Tasks will be executed in sequence
        verbose=True  # Show detailed execution information
    )
    
    # Execute the crew's tasks
    result = crew.kickoff()
    
    # Process and display results
    print("\n=== Generated Script ===")
    print(result.tasks_output[0].raw)  # First task output (script)
    
    print("\n=== Transformed Scenes ===")
    print(result.tasks_output[1].json_dict)  # Second task output (transformed scenes)

if __name__ == "__main__":
    main() 