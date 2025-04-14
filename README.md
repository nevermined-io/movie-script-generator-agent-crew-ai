[![banner](https://raw.githubusercontent.com/nevermined-io/assets/main/images/logo/banner_logo.png)](https://nevermined.io)

Movie Script Generator Agent (Python)
=========================================================

> A **Python-based agent** that generates **detailed technical scripts** for movies using **CrewAI** + **OpenAI**, providing a powerful tool for automated script creation and scene analysis.

* * *

**Description**
---------------

The **Movie Script Generator Agent** automates the process of creating complex, production-ready scripts. Leveraging AI-powered text generation, the agent:

1. **Generates** a script outline (scene breakdowns, camera movements, lighting, etc.).
2. **Extracts** scene data (start/end times, shot type, transitions).
3. **Identifies** the **settings** or environments in each scene with rich descriptors.
4. **Extracts** all **characters** mentioned (including main actors, supporting roles, extras).
5. **Transforms** the final scene data into a set of prompts suitable for subsequent AI-based image/video generation.

All steps are **event-driven**, with tasks managed through a robust workflow system. The agent processes each step sequentially, ensuring quality and consistency throughout the generation process.

* * *
**Related Projects**
--------------------

This **Movie Script Generator Agent** is part of a larger ecosystem of AI-driven media creation. For a complete view of how multiple agents work together, see:

1. [Music Orchestrator Agent](https://github.com/nevermined-io/music-video-orchestrator)
   * Coordinates end-to-end workflows: collects user prompts, splits them into tasks, merges final output.

2. [Song Generator Agent](https://github.com/nevermined-io/song-generation-agent)
   * Produces lyrics, titles, and final audio tracks using LangChain + OpenAI and a chosen music generation API.

3. [Image / Video Generator Agent](https://github.com/nevermined-io/video-generator-agent)
   * Produces Images / Video using 3rd party wrapper APIs (Fal.ai and TTapi, wrapping Flux and Kling.ai)

**Workflow Example**:

```
[ User Prompt ] --> [Music Orchestrator] --> [Song Generation] --> [Script Generation] --> [Image/Video Generation] --> [Final Compilation]
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
7. [Usage](#usage)
8. [Detailed Guide: Creating & Managing Tasks](#detailed-guide-creating--managing-tasks)
9. [Development & Testing](#development--testing)
10. [License](#license)

* * *

**Features**
------------

* **CrewAI + OpenAI**: Uses advanced prompt templates to produce detailed cinematic descriptions.
* **Scene Extraction & Settings**: Splits an existing script into discrete scenes with recommended camera gear, lighting setups, and transitions.
* **Character Extraction**: Provides names, descriptions, wardrobe details, and AI-friendly prompts for each character.
* **Transform Scenes**: Creates final prompts summarizing each scene in a JSON array (duration, setting, character references).
* **Modular Design**: Extend or replace steps with minimal disruption.
* **Logging & Error Handling**: Comprehensive logs at every step, with robust fallback in case of failures.

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
   * Takes the user's "idea" (plus optional tags/duration) and generates a full technical script.
   * The script typically includes scene descriptions, durations, camera gear, transitions, and other cinematic details.

3. **Scene Extraction** (`extractScenes`)
   * Parses the newly generated script to produce structured data: start/end times for each scene, shot types, transitions, etc.

4. **Settings Generation** (`generateSettings`)
   * Identifies each unique environment (e.g., rooftop party, city street, beach) and creates a JSON array describing them.

5. **Characters Extraction** (`extractCharacters`)
   * Finds all references to characters in the script.
   * Produces a list with each character's physical descriptors, wardrobe details, movement style, etc.

Throughout these steps, the agent **updates** each step's status (from `Pending` to `Completed` or `Failed`) in the **Nevermined** system. If a step fails, it logs the error and halts.

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