#!/usr/bin/env python3
"""
Example usage of the multi-speaker podcast creator
"""
import asyncio
from podcast_creator import create_podcast


async def main():
    """Generate a sample multi-speaker podcast"""
    
    """Generate a sample multi-speaker podcast"""
    
    content = """
    We are generating a podcast for German language learners who enjoy true crime stories.
    The podcast has various difficultiy levels which are selected by the user and should be reflected in the podcast.

    The possible difficulty levels are:
    - Easy
    - Medium
    - Hard
    - Expert

    The podcast needs to be easily digestible, and the language should vary based on the difficulty level.

    The selected difficulty level is:

        === EASY (A2-B1 Level) ===
        Language Characteristics:
        - Use present tense primarily (Präsens)
        - Simple past tense only for common verbs (war, hatte, ging, kam)
        - Short sentences (max 10-15 words)
        - Simple sentence structure: Subject-Verb-Object
        - Avoid subordinate clauses when possible
        - Use common, everyday vocabulary (top 1000-2000 most frequent words)
        - Repeat key vocabulary throughout the episode
        - Avoid idioms and colloquialisms unless explained immediately

        Grammar to Use:
        - Basic conjunctions: und, aber, oder, denn
        - Modal verbs in present tense: kann, muss, will, soll
        - Simple prepositions: in, auf, mit, für, zu

        Grammar to Avoid:
        - Subjunctive mood (Konjunktiv)
        - Passive voice
        - Complex relative clauses
        - Genitive case (use "von" instead)
        - Complex compound words

        Speaking Style:
        - Speak slightly slower than native speed
        - Clear pauses between sentences
        - Natural but measured pace
        - Repeat important information in different words
        - Use "Das heißt..." or "Also..." to rephrase complex ideas
    """
    
    briefing = """
        Create an engaging podcast discussion about a famous German bank heist - the Berliner Sparkasse 
        tunnel robbery. The conversation should tell the story chronologically, from planning through 
        execution to aftermath, highlighting the clever planning, unexpected mishaps, and how the criminals 
        were eventually caught. The tone should be light-hearted and entertaining while remaining 
        informative, suitable for German language learners who enjoy true crime stories. Include interesting 
        details about the tunnel construction, the heist night, and the cultural impact in Germany. Keep it 
        suspenseful but avoid graphic content - focus on the human elements, mistakes, and ironies that made 
        this heist memorable.
    """
    
    print("🎙️ Generating multi-speaker podcast...")
    
    result = await create_podcast(
        content=content,
        briefing=briefing,
        episode_name="ai_developments_2024",
        output_dir="output/ai_developments_2024",
        speaker_config="ai_researchers",  # Uses Dr. Sarah Chen & Marcus Rivera
        outline_provider="openai",
        outline_model="gpt-4o-mini",
        transcript_provider="anthropic",
        transcript_model="claude-3-5-sonnet-latest",
        num_segments=3,
        generate_audio=True
    )
    
    print("✅ Podcast generated successfully!")
    print(f"📁 Final audio: {result['final_output_file_path']}")
    print(f"🎵 Total clips: {result['audio_clips_count']}")
    print(f"💬 Transcript segments: {len(result['transcript'])}")
    
    # Show which speakers were used
    speakers_used = set(dialogue.speaker for dialogue in result['transcript'])
    print(f"👥 Speakers: {', '.join(speakers_used)}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())