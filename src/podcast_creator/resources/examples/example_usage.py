#!/usr/bin/env python3
"""
Example usage of the multi-speaker podcast creator
"""
import asyncio
from podcast_creator import create_podcast
from podcast_creator.core import Difficulty


async def main():
    """Generate a sample multi-speaker podcast"""
    
    print("🎙️ Generating multi-speaker podcast...")
    
    result = await create_podcast(
        content="The Berliner Sparkasse Tunnel Robbery",
        difficulty=Difficulty.EASY,
        episode_name="BerlinerSparkasseTunnelRobbery",
        output_dir="output/testcast",
        speaker_config="curious_duo", 
        outline_provider="openai",
        outline_model="gpt-4o-mini",
        transcript_provider="openai",
        transcript_model="gpt-4o-mini",
        num_segments=3,
        generate_audio=False
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