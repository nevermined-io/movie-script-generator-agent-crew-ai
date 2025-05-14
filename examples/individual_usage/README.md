# Individual Usage Examples

This directory contains examples of how to use the movie script generation system independently of the A2A protocol. Each example demonstrates a different way to interact with the system.

## Prerequisites

1. Make sure you have all required environment variables set in your `.env` file:
   - `OPENAI_API_KEY`
   - `HELICONE_API_KEY`

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Examples

### 1. Basic Script Generation (`1_basic_script_generation.py`)
This example shows how to use the `MovieScriptGenerator` class directly to generate a complete movie script with scenes and characters.

Run it with:
```bash
python examples/individual_usage/1_basic_script_generation.py
```

### 2. Individual Agents (`2_individual_agents.py`)
This example demonstrates how to create and use individual agents separately. It shows how to:
- Create different types of agents
- Set up tasks for each agent
- Understand their roles and capabilities

Run it with:
```bash
python examples/individual_usage/2_individual_agents.py
```

### 3. Custom Crew (`3_custom_crew.py`)
This example shows how to create a custom crew with specific agents and tasks. It demonstrates:
- Creating a custom crew configuration
- Using the ScriptTasks factory
- Executing tasks sequentially
- Processing and displaying results

Run it with:
```bash
python examples/individual_usage/3_custom_crew.py
```

## Notes

- Each example is self-contained and can be run independently
- The examples use different approaches to show the flexibility of the system
- You can modify the examples to suit your specific needs
- Make sure to handle the API responses appropriately in a production environment

## Customization

You can customize these examples by:
1. Modifying the input parameters (title, tags, idea, etc.)
2. Adding or removing agents from the crew
3. Creating custom tasks
4. Changing the process type (sequential, parallel, etc.)
5. Adding error handling and logging 