[![banner](https://raw.githubusercontent.com/nevermined-io/assets/main/images/logo/banner_logo.png)](https://nevermined.io)

Music Video Script Generator Agent (Python)
=========================================================

> A **Python-based agent** that generates **detailed technical scripts** for music videos using **CrewAI** + **OpenAI**, providing a powerful tool for automated music video script creation and scene analysis.

* * *

**Description**
---------------

The **Music Video Script Generator Agent** automates the process of creating complex, production-ready music video scripts. Leveraging AI-powered text generation, the agent:

1. **Generates** a music video script outline (scene breakdowns, camera movements, lighting, etc.) synchronized with the song's rhythm and structure.
2. **Extracts** scene data (start/end times aligned with music beats, shot type, transitions).
3. **Identifies** the **settings** or environments in each scene with rich descriptors that match the song's mood and theme.
4. **Extracts** all **characters** mentioned (including artists, dancers, supporting roles, extras).
5. **Transforms** the final scene data into a set of prompts suitable for subsequent AI-based music video generation.

All steps are **event-driven**, with tasks managed through a robust workflow system. The agent processes each step sequentially, ensuring quality and consistency throughout the generation process, while maintaining perfect synchronization with the music track.

* * *
**Related Projects**
--------------------

This **Music Video Script Generator Agent** is part of a larger ecosystem of AI-driven media creation. For a complete view of how multiple agents work together, see:

1. [Music Orchestrator Agent](https://github.com/nevermined-io/music-video-orchestrator)
   * Coordinates end-to-end workflows: collects user prompts, splits them into tasks, merges final output.

2. [Song Generator Agent](https://github.com/nevermined-io/song-generation-agent)
   * Produces lyrics, titles, and final audio tracks using LangChain + OpenAI and a chosen music generation API.

3. [Image / Video Generator Agent](https://github.com/nevermined-io/video-generator-agent)
   * Produces Images / Video using 3rd party wrapper APIs (Fal.ai and TTapi, wrapping Flux and Kling.ai)

**Workflow Example**:

```
[ User Prompt ] --> [Music Orchestrator] --> [Song Generation] --> [Music Video Script Generation] --> [Image/Video Generation] --> [Final Compilation]
```

* * *

**Table of Contents**
---------------------

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Environment Variables](#environment-variables)
5. [Project Structure](#project-structure)
6. [Architecture & Workflow](#architecture--workflow)
7. [A2A Protocol Integration](#a2a-protocol-integration)
8. [Usage](#usage)
9. [Detailed Guide: Creating & Managing Tasks](#detailed-guide-creating--managing-tasks)
10. [Development & Testing](#development--testing)
11. [License](#license)

* * *

**Features**
------------

* **CrewAI + OpenAI**: Uses advanced prompt templates to produce detailed music video descriptions.
* **Scene Extraction & Settings**: Splits an existing script into discrete scenes with recommended camera gear, lighting setups, and transitions, all synchronized with the music.
* **Character Extraction**: Provides names, descriptions, wardrobe details, and AI-friendly prompts for each character in the music video.
* **Transform Scenes**: Creates final prompts summarizing each scene in a JSON array (duration, setting, character references) with precise musical timing.
* **Modular Design**: Extend or replace steps with minimal disruption.
* **Logging & Error Handling**: Comprehensive logs at every step, with robust fallback in case of failures.
* **A2A Protocol Support**: Full implementation of the Agent-to-Agent communication protocol.

* * *

**Prerequisites**
-----------------

* **Python** (>= 3.9.0 recommended)
* **CrewAI** (project developed on ^0.1.x)
* **OpenAI API Key** for text generation

* * *

**Installation**
----------------

1. **Clone** this repository:

   ```bash
   git clone https://github.com/nevermined-io/movie-script-generator-agent-crew-ai.git
   cd movie-script-generator-agent-crew-ai
   ```

2. **Install** dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up** environment:

   ```bash
   cp .env.example .env
   ```

* * *

**Environment Variables**
-------------------------

Rename `.env.example` to `.env` and set the required keys:

```env
OPENAI_API_KEY=your_openai_api_key
IS_DUMMY=false
```

* `OPENAI_API_KEY` grants access to OpenAI's text generation models.

* * *

**Project Structure**
---------------------

```plaintext
movie-script-generator-agent-crew-ai/
├── src/
│   ├── main.py                      # Main entry (initializes Payments, subscribes to steps)
│   ├── agents/
│   │   └── script_agents/          # Agents for script generation and review
│   ├── config/
│   │   └── env.py                  # Environment configuration
│   ├── models/
│   │   └── script.py               # Script data models
│   ├── server.py                   # Optional REST API
│   └── utils/
│       └── logger.py               # Logging system
├── .env.example                    # Environment template
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

### Key Components:

1. **`main.py`**: Handles task lifecycle, from receiving steps to sending back results.
2. **`script_agents/`**: Implements multi-step logic for generating initial script, extracting scenes, identifying settings, and extracting characters.
3. **`server.py`**: Optional REST API for service integration.
4. **`logger.py`**: Logging system that logs both locally and through the **Nevermined Payments** API.

* * *

**Architecture & Workflow**
---------------------------

1. **Initialization** (`init` step)
   * When a new task is created for this agent, it starts with `init`.
   * We create subsequent steps (e.g., `generateScript`, `extractScenes`, `generateSettings`, `extractCharacters`).

2. **Script Generation** (`generateScript`)
   * Takes the user's "idea" and song (plus optional tags/duration) and generates a full technical music video script.
   * The script typically includes scene descriptions, durations matched to music beats, camera gear, transitions, and other cinematic details.

3. **Scene Extraction** (`extractScenes`)
   * Parses the newly generated script to produce structured data: start/end times synchronized with music, shot types, transitions, etc.

4. **Settings Generation** (`generateSettings`)
   * Identifies each unique environment (e.g., concert venue, urban landscape, dreamscape) and creates a JSON array describing them.
   * Ensures settings match the song's mood and theme.

5. **Characters Extraction** (`extractCharacters`)
   * Finds all references to characters in the script (artists, dancers, extras).
   * Produces a list with each character's physical descriptors, wardrobe details, movement style, etc.

Throughout these steps, the agent **updates** each step's status (from `Pending` to `Completed` or `Failed`) in the **Nevermined** system. If a step fails, it logs the error and halts.

* * *

**A2A Protocol Integration**
---------------------------

The Movie Script Generator Agent implements the **Agent-to-Agent (A2A) Protocol**, a standardized communication protocol for AI agents. This section details how A2A is integrated into our system.

### Protocol Overview

The A2A Protocol defines:
1. **Task States**: A finite state machine for task progression
2. **Message Format**: Standardized format for agent communication
3. **Push Notifications**: Real-time updates on task progress
4. **Error Handling**: Standardized error reporting and recovery

### Task States

Tasks in our system follow the A2A state machine:

```
[SUBMITTED] --> [WORKING] --> [COMPLETED]
     |             |             
     |             +--> [INPUT-REQUIRED]
     |             |
     +-------------+--> [FAILED]
                   |
                   +--> [CANCELLED]
```

* **SUBMITTED**: Initial state when task is created
* **WORKING**: Active processing by CrewAI agents
* **INPUT-REQUIRED**: (Optional) Waiting for user input
* **COMPLETED**: Successful task completion
* **FAILED**: Error occurred during processing
* **CANCELLED**: Task cancelled by user request

### Implementation Details

1. **Task Controller** (`src/controllers/a2a_controller.py`)
   * Manages task lifecycle
   * Handles state transitions
   * Validates state changes
   * Implements cancellation logic

2. **Task Processor** (`src/core/task_processor.py`)
   * Processes tasks asynchronously
   * Manages CrewAI integration
   * Handles task artifacts
   * Implements push notifications

3. **Push Notifications** (`src/models/push_notifications.py`)
   * Server-Sent Events (SSE) for real-time updates
   * Configurable endpoints
   * Retry logic with backoff

### Task Structure

Each task follows the A2A format:

```json
{
    "id": "unique-task-id",
    "sessionId": "optional-session-id",
    "status": {
        "state": "working",
        "timestamp": "2024-03-14T12:00:00Z",
        "message": {
            "role": "assistant",
            "parts": [
                {
                    "type": "text",
                    "text": "Generating music video script..."
                }
            ]
        }
    },
    "artifacts": [
        {
            "name": "script",
            "description": "Generated music video script",
            "content": "..."
        }
    ],
    "metadata": {
        "title": "Music Video Title",
        "songDuration": 180,
        "musicGenre": "pop",
        "tags": ["performance", "urban", "choreography"]
    }
}
```

### Error Handling

The A2A implementation includes:
* Graceful error recovery
* Detailed error messages
* State validation
* Automatic cleanup
* Error logging and monitoring

### Testing

Comprehensive test suite in `tests/e2e/`:
* `test_push_notifications.py`: Tests SSE functionality
* `test_agent_client.py`: Tests client implementation
* State transition validation
* Error handling scenarios
* Cancellation testing

### Usage Example

```python
from src.client import AgentClient

async with AgentClient() as client:
    # Create and send task
    task_data = await client.interpreter.create_task_data(
        agent_card,
        "Generate a vibrant pop music video script"
    )
    task = await client.send_task(task_data)
    
    # Monitor progress with SSE
    async for update in client.subscribe_to_updates(task["id"]):
        print(f"Task state: {update['status']['state']}")
    
    # Cancel task if needed
    await client.cancel_task(task["id"])
```

### Benefits of A2A Integration

1. **Standardization**: Common interface for agent communication
2. **Real-time Updates**: Push notifications for task progress
3. **Error Recovery**: Robust error handling and recovery
4. **State Management**: Clear task lifecycle management
5. **Cancellation Support**: Ability to stop long-running tasks
6. **Monitoring**: Comprehensive logging and tracking

* * *

**Usage**
---------

After installing and configuring `.env`:

```bash
python src/main.py
```

1. The crew is ready to receive tasks.
2. The crew yields a JSON with scene prompts, character data, and settings.

* * *

**License**
-----------

```
Apache License 2.0

(C) 2025 Nevermined AG

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions
and limitations under the License. 