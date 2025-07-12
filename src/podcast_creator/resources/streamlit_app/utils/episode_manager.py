"""
Episode management utilities for the Podcast Creator Studio.

Handles episode discovery, metadata extraction, and file operations.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import streamlit as st

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


@dataclass
class EpisodeInfo:
    """Information about a podcast episode."""
    name: str
    path: str
    audio_file: Optional[str] = None
    transcript_file: Optional[str] = None
    outline_file: Optional[str] = None
    created_date: Optional[datetime] = None
    duration: Optional[float] = None
    profile_used: Optional[str] = None
    speakers_count: Optional[int] = None
    segments_count: Optional[int] = None
    file_size: Optional[int] = None


class EpisodeManager:
    """Manages podcast episodes including discovery, metadata, and file operations."""
    
    def __init__(self, base_output_dir: str = "output"):
        """
        Initialize the episode manager.
        
        Args:
            base_output_dir: Base directory where episodes are stored
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
    
    def scan_episodes_directory(self) -> List[EpisodeInfo]:
        """
        Scan the output directory for existing episodes.
        
        Returns:
            List of EpisodeInfo objects for found episodes
        """
        episodes = []
        
        if not self.base_output_dir.exists():
            return episodes
        
        for episode_dir in self.base_output_dir.iterdir():
            if episode_dir.is_dir():
                try:
                    episode_info = self.get_episode_info(episode_dir)
                    if episode_info:
                        episodes.append(episode_info)
                except Exception as e:
                    st.warning(f"Error reading episode {episode_dir.name}: {e}")
        
        # Sort by creation date (newest first)
        episodes.sort(key=lambda x: x.created_date or datetime.min, reverse=True)
        return episodes
    
    def get_episode_info(self, episode_path: Path) -> Optional[EpisodeInfo]:
        """
        Extract episode information from an episode directory.
        
        Args:
            episode_path: Path to the episode directory
            
        Returns:
            EpisodeInfo object if valid episode found, None otherwise
        """
        if not episode_path.exists() or not episode_path.is_dir():
            return None
        
        # Look for expected files
        audio_dir = episode_path / "audio"
        clips_dir = episode_path / "clips"
        
        # Find audio file
        audio_file = None
        if audio_dir.exists():
            for audio_path in audio_dir.glob("*.mp3"):
                audio_file = str(audio_path)
                break
        
        # Find transcript file
        transcript_file = None
        transcript_path = episode_path / "transcript.json"
        if transcript_path.exists():
            transcript_file = str(transcript_path)
        
        # Find outline file
        outline_file = None
        outline_path = episode_path / "outline.json"
        if outline_path.exists():
            outline_file = str(outline_path)
        
        # Get creation date from directory
        created_date = None
        try:
            created_date = datetime.fromtimestamp(episode_path.stat().st_ctime)
        except Exception:
            pass
        
        # Get audio duration
        duration = None
        if audio_file and PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(audio_file)
                duration = len(audio) / 1000.0  # Convert to seconds
            except Exception:
                pass
        
        # Get profile information from transcript
        profile_used = None
        speakers_count = None
        segments_count = None
        
        if transcript_file:
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    
                    # Extract speakers count
                    speakers = set()
                    if isinstance(transcript_data, list):
                        for segment in transcript_data:
                            if isinstance(segment, dict) and 'speaker' in segment:
                                speakers.add(segment['speaker'])
                        speakers_count = len(speakers)
                        segments_count = len(transcript_data)
                    elif isinstance(transcript_data, dict):
                        # Handle different transcript formats
                        if 'segments' in transcript_data:
                            segments = transcript_data['segments']
                            for segment in segments:
                                if 'speaker' in segment:
                                    speakers.add(segment['speaker'])
                            speakers_count = len(speakers)
                            segments_count = len(segments)
            except Exception:
                pass
        
        # Get file size
        file_size = None
        if audio_file:
            try:
                file_size = Path(audio_file).stat().st_size
            except Exception:
                pass
        
        return EpisodeInfo(
            name=episode_path.name,
            path=str(episode_path),
            audio_file=audio_file,
            transcript_file=transcript_file,
            outline_file=outline_file,
            created_date=created_date,
            duration=duration,
            profile_used=profile_used,
            speakers_count=speakers_count,
            segments_count=segments_count,
            file_size=file_size
        )
    
    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds, or None if unable to determine
        """
        if not PYDUB_AVAILABLE:
            return None
        
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except Exception:
            return None
    
    def delete_episode(self, episode_path: str) -> bool:
        """
        Delete an episode directory and all its contents.
        
        Args:
            episode_path: Path to the episode directory
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            episode_dir = Path(episode_path)
            if episode_dir.exists() and episode_dir.is_dir():
                shutil.rmtree(episode_dir)
                return True
            return False
        except Exception as e:
            st.error(f"Error deleting episode: {e}")
            return False
    
    def download_episode(self, episode_path: str, download_path: str) -> bool:
        """
        Copy an episode's audio file to a download location.
        
        Args:
            episode_path: Path to the episode directory
            download_path: Where to copy the audio file
            
        Returns:
            True if download was successful, False otherwise
        """
        try:
            episode_dir = Path(episode_path)
            audio_dir = episode_dir / "audio"
            
            if not audio_dir.exists():
                return False
            
            # Find the audio file
            audio_file = None
            for audio_path in audio_dir.glob("*.mp3"):
                audio_file = audio_path
                break
            
            if not audio_file:
                return False
            
            # Copy the file
            shutil.copy2(audio_file, download_path)
            return True
            
        except Exception as e:
            st.error(f"Error downloading episode: {e}")
            return False
    
    def check_episode_exists(self, episode_name: str) -> bool:
        """
        Check if an episode with the given name already exists.
        
        Args:
            episode_name: Name of the episode to check
            
        Returns:
            True if episode exists, False otherwise
        """
        episode_path = self.base_output_dir / episode_name
        return episode_path.exists() and episode_path.is_dir()
    
    def get_episodes_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all episodes.
        
        Returns:
            Dictionary with episode statistics
        """
        episodes = self.scan_episodes_directory()
        
        total_episodes = len(episodes)
        total_duration = 0
        total_size = 0
        
        for episode in episodes:
            if episode.duration:
                total_duration += episode.duration
            if episode.file_size:
                total_size += episode.file_size
        
        return {
            'total_episodes': total_episodes,
            'total_duration': total_duration,
            'total_size': total_size,
            'average_duration': total_duration / total_episodes if total_episodes > 0 else 0
        }
    
    def search_episodes(self, query: str, episodes: List[EpisodeInfo]) -> List[EpisodeInfo]:
        """
        Search episodes by name or other criteria.
        
        Args:
            query: Search query
            episodes: List of episodes to search
            
        Returns:
            Filtered list of episodes
        """
        if not query:
            return episodes
        
        query_lower = query.lower()
        filtered_episodes = []
        
        for episode in episodes:
            if query_lower in episode.name.lower():
                filtered_episodes.append(episode)
        
        return filtered_episodes
    
    def sort_episodes(self, episodes: List[EpisodeInfo], sort_by: str) -> List[EpisodeInfo]:
        """
        Sort episodes by various criteria.
        
        Args:
            episodes: List of episodes to sort
            sort_by: Sorting criteria ('Newest', 'Oldest', 'A-Z', 'Duration')
            
        Returns:
            Sorted list of episodes
        """
        if sort_by == "Newest":
            return sorted(episodes, key=lambda x: x.created_date or datetime.min, reverse=True)
        elif sort_by == "Oldest":
            return sorted(episodes, key=lambda x: x.created_date or datetime.min)
        elif sort_by == "A-Z":
            return sorted(episodes, key=lambda x: x.name.lower())
        elif sort_by == "Duration":
            return sorted(episodes, key=lambda x: x.duration or 0, reverse=True)
        else:
            return episodes
    
    def format_duration(self, duration: Optional[float]) -> str:
        """
        Format duration in seconds to a human-readable string.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if duration is None:
            return "Unknown"
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        if minutes > 0:
            return f"{minutes}:{seconds:02d}"
        else:
            return f"0:{seconds:02d}"
    
    def format_file_size(self, size: Optional[int]) -> str:
        """
        Format file size in bytes to a human-readable string.
        
        Args:
            size: File size in bytes
            
        Returns:
            Formatted file size string
        """
        if size is None:
            return "Unknown"
        
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"