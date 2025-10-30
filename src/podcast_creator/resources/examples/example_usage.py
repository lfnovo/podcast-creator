#!/usr/bin/env python3
"""
Example usage of the multi-speaker podcast creator
"""
import asyncio
from podcast_creator import create_podcast


async def main():
    """Generate a sample multi-speaker podcast"""
    
    content = """
    The field of artificial intelligence has seen remarkable advances in 2024, particularly in the areas 
    of large language models, multimodal AI, and AI safety research. Companies are increasingly adopting 
    AI technologies for business processes, while researchers continue to push the boundaries of what's 
    possible with machine learning.

    Key developments include improvements in reasoning capabilities, better alignment techniques, and 
    new applications in fields like healthcare, education, and creative industries.
    """
    
    briefing = """
    Create an engaging podcast discussion about AI developments in 2024. The conversation should be 
    informative yet accessible, covering both technical advances and practical implications. The tone 
    should be professional but conversational, suitable for a tech-savvy audience.
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