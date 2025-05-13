from crewai import Task, Agent
from typing import Dict, Any, List, Optional
from src.models import (
    ExtractedSceneList,
    SettingList,
    CharacterDetailList,
    TransformedSceneList
)

class ScriptTasks:
    """Factory class for creating script generation related tasks"""
    
    @staticmethod
    def generate_script(title: str, tags: str, lyrics: str, idea: str, agent: Agent, duration: int = 180, mean_scenes: int = 18) -> Task:
        """
        Generate initial script based on input parameters
        
        @param title - Title of the movie/video
        @param tags - Descriptive tags for the content
        @param lyrics - Song lyrics if applicable
        @param idea - Basic concept/idea for the video
        @param agent - Agent assigned to execute this task
        @param duration - Duration in seconds
        @param mean_scenes - Suggested number of scenes
        @return Task for script generation
        """
        return Task(
            name="Generate Script",
            description=f'''Create a detailed technical script for a **3-minute maximum** music video based on the provided idea.

            **Strict Instructions**:  
            1. **Structure**:  
            - Divide the video into **chronological scenes** (numbered) synchronized with song lyrics/musical segments.  
            - Each scene must include:  
                * **Exact duration** (seconds)  
                * **Shot type** (close-up, medium shot, American shot, wide shot, etc.)  
                * **Camera movement** (Steadicam, crane, dolly zoom, horizontal/vertical pan, etc.)  
                * **Visual aesthetic** (color palette, lighting, textures, post-production effects)  
                * **Scene transitions** (hard cut, fade, match cut, etc.)  
            
            2. **Characters**:  
            - List **all characters** (including extras and background actors) with:  
                * Detailed physical description (clothing, hairstyle, makeup, distinctive features)  
                * Specific behavior/actions in each scene where they appear  
                * Type of interaction with other characters or camera  
            
            3. **Mandatory Technical Details**:  
            - Specify **camera gear** suggested for each shot type (e.g., anamorphic lens for wide shots, gimbal stabilizer for tracking movements).  
            - Include **concrete visual references** (e.g., "lighting à la 'Blade Runner 2049' with blue neons and atmospheric smoke").  
            
            4. **Rules**:  
            - Prioritize visual impact over extended narrative.  
            - Use professional cinematography terminology.  
            - Avoid spoken dialogue (unless part of song lyrics).  
            - Ensure coherence between visual atmosphere and music genre.
            - Every scene must have a duration of either 5 or 10 seconds.
            - Plan accordingly the number of scenes given the total duration of the video. 
            - Some locations may be used multiple times in the video.
            - The total number of distinct locations/settings should be limited (ideally 4 or 5 for the whole video), and scenes should reuse locations when possible.
            - Every scene must have at least one character.
            - Optimal number of scenes: {mean_scenes}
            
            5. **Include Scenes with Live Musicians**:
            - At least two scenes must feature a visible band or musicians playing instruments that complement the main story.
            - Show how these musicians integrate into the video's narrative or setting.

            **Input Parameters**:  
            Title: {title}  
            Style Tags: {tags}
            Lyrics: {lyrics}
            Creative Idea: {idea}
            Duration: {duration} seconds''',
            agent=agent,
            expected_output=f'''A string with the complete script with technical details.
            **Output Format**:  
        
                SCENE [NUMBER] - [DURATION IN SECONDS] seconds
                [SHOT TYPE] | [CAMERA MOVEMENT] | [LOCATION]  
                Aesthetic: [Detailed description with colors, lighting & effects]  
                Characters:  
                - [Name/Role]: [Specific actions synchronized to music]  
                Transition: [Transition type to next scene]  
                
                [Repeat structure for each scene]  
                
                CHARACTER LIST (after script):  
                [Name/Role]: [Physical description + wardrobe + behavior]  
            ''',
        )

    @staticmethod
    def extract_scenes(agent: Agent) -> Task:
        """
        Extract individual scenes from the script
        
        @param agent - Agent assigned to execute this task
        @return Task for scene extraction
        """
        return Task(
            name="Extract Scenes",
            description='''Extract technical scene details as a JSON array. 
            Return **one object per SCENE block** in the same order they appear in the script. 
            
            **Important Rules**:
            1. Preserve the **sceneNumber** from the script. If the script says "SCENE 1 - 10 seconds", interpret that as sceneNumber = 1 and duration = 10 seconds.
            2. Convert durations to approximate "startTime" and "endTime" in MM:SS, adding them sequentially.
            3. Do not skip any scenes. Return them in the same order.
            4. If a scene references location or certain camera gear, place that info under the correct fields. 
            5. Do not add or remove scenes; parse exactly from the script.''',
            agent=agent,
            expected_output="A JSON object containing an array of scene objects with technical specifications",
            output_json=ExtractedSceneList
        )

    @staticmethod
    def generate_settings(agent: Agent) -> Task:
        """
        Generate detailed settings information
        
        @param agent - Agent assigned to execute this task
        @return Task for settings generation
        """
        return Task(
            name="Generate Settings",
            description='''Analyze the script and extract DISTINCT SETTINGS/LOCATIONS. For each unique setting:

            **Important**:  
            - The number of distinct settings/locations should be much smaller than the number of scenes (ideally 4 to 6 for the whole video, never less than 3).
            - Each setting must have a unique "settingId" (e.g., "setting1", "setting2", ...).
            - Multiple scenes can and should share the same setting/location when appropriate.
            - Do NOT generate one setting per scene; instead, group scenes that logically occur in the same place.

            1. Create a detailed description including:
               - Physical space characteristics
               - Lighting conditions
               - Color palette
               - Key visual elements
               - Ambient elements (weather, time of day)
               - Image style (e.g., cyberpunk, retro-futuristic, dystopian, comic book, realistic, 3D, etc.)
               - settingId (unique string for reference)
            
            2. Generate an image prompt for each setting''',
            agent=agent,
            expected_output="A JSON object containing an array of setting objects with detailed descriptions and technical requirements",
            output_json=SettingList
        )

    @staticmethod
    def extract_characters(agent: Agent) -> Task:
        """
        Extract character information from the script
        
        @param agent - Agent assigned to execute this task
        @return Task for character extraction
        """
        return Task(
            name="Extract Characters",
            description='''Extract ALL characters from the script with detailed physical descriptors and roles, taking into account the provided song lyrics and tags as additional context.

            Important Instructions:

            - Include every character mentioned in the script, not only the musicians. If there are characters that are part of the narrative (such as background dancers, story characters, or extras), they must all appear in the output list.
            - Their name must match the script's name for the character.
            - Each character must have a unique "characterId" (e.g., "character1", "character2", ...).
            - If there are references to a band or musicians, list each musician separately with details including their instrument, wardrobe, and any unique features.
            - Maintain consistency with the script's descriptions (or make the best assumptions if not explicitly stated).
            - Use the provided song lyrics and tags as additional context when inferring character details.
            - For the "imagePrompt" field:
              Synthesize all the character attributes (physical features, age, gender, height/build, distinctive features, wardrobe details, movement style, key accessories, and any scene-specific changes) into one complete, vivid visual description.
              The prompt should serve as a detailed instruction for a visual generator, clearly conveying how the character should appear in the music video.

            - There should be at least as many characters as are referenced in the script.''',
            agent=agent,
            expected_output="A JSON object containing an array of character objects with detailed profiles",
            output_json=CharacterDetailList
        )

    @staticmethod
    def transform_scenes(agent: Agent) -> Task:
        """
        Transform scenes into detailed technical format
        
        @param agent - Agent assigned to execute this task
        @return Task for scene transformation
        """
        return Task(
            name="Transform Scenes",
            description='''Transform the technical details of the scenes into production prompts including composition details, actions and camera movements.

            **Instructions**:

            1. **Number of prompts**: You must produce as many objects as there are scenes in the input. Each scene must have:
              - sceneNumber (integer)
              - prompt (string) - NOT description
              - charactersInScene (array of strings, referencing the exact character IDs generated in the character extraction step)
              - settingId (string, referencing the exact settingId generated in the settings step; every scene must have a valid settingId)
              - duration (integer, must be 5 or 10)

            2. **Character references**:
              - In "prompt", replace each character name with their full physical description
              - If the character is a musician, mention their instrument in the prompt
              - In "charactersInScene", list only the exact character IDs
              - Exclude any characters not found in the available data

            3. **Scene and Setting Integration**:
              - Each scene MUST reference an existing settingId from the "Generate Settings" task (settings are reused across scenes; do not create a unique setting for every scene).
              - Include the setting's characteristics in the scene description
              - Use all available technical details (shotType, cameraMovement, etc.)
              - Ensure visual consistency with the setting's aesthetic

            4. **Technical Precision**:
              - Use professional cinematography terminology
              - Include specific camera gear and lens information
              - Maintain consistent style throughout all prompts
              
            5. **Technical Details Structure**:
              - The "technicalDetails" object MUST include:
                * shotType (from original scene)
                * cameraMovement (from original scene)
                * lens (recommended lens type)
                * cameraGear (specific equipment)
                * lighting (lighting setup)
                * colorPalette (MUST be included from the original scene's colorPalette)
                * timeOfDay (when the scene takes place)

            **MANDATORY**:  
            - Every scene must have a valid settingId and at least one character in charactersInScene.  
            - If a scene occurs in a location already described, use the same settingId.  
            - If a character appears in a scene, use the exact characterId from the character list.  
            - Do not leave charactersInScene or settingId empty.  
            ''',
            agent=agent,
            expected_output="A JSON object containing an array of transformed scene objects with complete technical details",
            output_json=TransformedSceneList
        ) 