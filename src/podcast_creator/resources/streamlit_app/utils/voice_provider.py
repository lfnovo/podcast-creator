"""
Voice provider utilities for the Podcast Creator Studio.

Handles voice selection for different TTS providers.
"""

import streamlit as st
from typing import Dict, List, Tuple, Optional
import requests
import json

try:
    from esperanto import AIFactory
    ESPERANTO_AVAILABLE = True
except ImportError:
    ESPERANTO_AVAILABLE = False


class VoiceProvider:
    """Voice provider utility for getting available voices from TTS providers."""
    
    @staticmethod
    def is_esperanto_available() -> bool:
        """Check if esperanto library is available."""
        return ESPERANTO_AVAILABLE
    
    @staticmethod
    def get_available_voices(provider: str, model: str = None) -> Dict[str, str]:
        """
        Get available voices for a TTS provider.
        
        Args:
            provider: TTS provider name (elevenlabs, openai, google)
            model: Optional model name for the provider
            
        Returns:
            Dictionary mapping voice names to voice IDs
        """
        if not ESPERANTO_AVAILABLE:
            return {}
        
        try:
            # Create TTS instance based on provider
            if provider == "elevenlabs":
                model = model or "eleven_flash_v2_5"
                tts = AIFactory.create_text_to_speech(provider, model)
            elif provider == "openai":
                model = model or "tts-1"
                tts = AIFactory.create_text_to_speech(provider, model)
            elif provider == "google":
                model = model or "standard"
                tts = AIFactory.create_text_to_speech(provider, model)
            else:
                return {}
            
            # Get available voices
            voices = tts.available_voices
            
            # Process voices based on provider
            if provider == "elevenlabs":
                # ElevenLabs returns a dict with voice objects
                return {
                    f"{voice.name} ({voice.gender}, {voice.description[:50]}...)": voice.id
                    for voice in voices.values()
                }
            elif provider == "openai":
                # OpenAI has predefined voices
                return {
                    "Alloy": "alloy",
                    "Echo": "echo", 
                    "Fable": "fable",
                    "Onyx": "onyx",
                    "Nova": "nova",
                    "Shimmer": "shimmer"
                }
            elif provider == "google":
                # Google has many voices, return a simplified set
                return {
                    "Standard A": "en-US-Standard-A",
                    "Standard B": "en-US-Standard-B",
                    "Standard C": "en-US-Standard-C",
                    "Standard D": "en-US-Standard-D",
                    "Wavenet A": "en-US-Wavenet-A",
                    "Wavenet B": "en-US-Wavenet-B",
                    "Wavenet C": "en-US-Wavenet-C",
                    "Wavenet D": "en-US-Wavenet-D"
                }
            else:
                return {}
                
        except Exception as e:
            st.error(f"Error getting voices for {provider}: {str(e)}")
            return {}
    
    @staticmethod
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_cached_voices(provider: str, model: str = None) -> Dict[str, str]:
        """
        Get cached available voices for a TTS provider.
        
        Args:
            provider: TTS provider name
            model: Optional model name
            
        Returns:
            Dictionary mapping voice names to voice IDs
        """
        return VoiceProvider.get_available_voices(provider, model)
    
    @staticmethod
    def render_voice_selector(
        provider: str, 
        model: str,
        current_voice_id: str = "",
        key: str = "voice_selector",
        help_text: str = "Choose a voice for this speaker"
    ) -> str:
        """
        Render a voice selector widget.
        
        Args:
            provider: TTS provider name
            model: Model name
            current_voice_id: Currently selected voice ID
            key: Unique key for the widget
            help_text: Help text for the widget
            
        Returns:
            Selected voice ID
        """
        if not ESPERANTO_AVAILABLE:
            st.warning("⚠️ Esperanto library not available. Using text input for voice ID.")
            return st.text_input(
                "Voice ID:", 
                value=current_voice_id,
                key=key,
                help="Enter the voice ID manually"
            )
        
        # Get available voices
        voices = VoiceProvider.get_cached_voices(provider, model)
        
        if not voices:
            st.warning(f"⚠️ No voices available for {provider}. Using text input.")
            return st.text_input(
                "Voice ID:", 
                value=current_voice_id,
                key=key,
                help="Enter the voice ID manually"
            )
        
        # Find current selection
        voice_names = list(voices.keys())
        voice_ids = list(voices.values())
        
        # Try to find current voice in the list
        current_index = 0
        if current_voice_id:
            try:
                current_index = voice_ids.index(current_voice_id)
            except ValueError:
                # Voice not found, add it as an option
                voice_names.insert(0, f"Current: {current_voice_id}")
                voice_ids.insert(0, current_voice_id)
                current_index = 0
        
        # Show selectbox
        selected_name = st.selectbox(
            "Voice:",
            voice_names,
            index=current_index,
            key=key,
            help=help_text
        )
        
        # Return the corresponding voice ID
        selected_index = voice_names.index(selected_name)
        return voice_ids[selected_index]
    
    @staticmethod
    def get_voice_preview_url(provider: str, voice_id: str) -> Optional[str]:
        """
        Get preview URL for a voice if available.
        
        Args:
            provider: TTS provider name
            voice_id: Voice ID
            
        Returns:
            Preview URL if available, None otherwise
        """
        if not ESPERANTO_AVAILABLE or provider != "elevenlabs":
            return None
        
        try:
            tts = AIFactory.create_text_to_speech(provider, "eleven_flash_v2_5")
            voices = tts.available_voices
            
            for voice in voices.values():
                if voice.id == voice_id:
                    return voice.preview_url
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def render_voice_preview(provider: str, voice_id: str):
        """
        Render voice preview if available.
        
        Args:
            provider: TTS provider name
            voice_id: Voice ID
        """
        if provider == "elevenlabs" and voice_id:
            preview_url = VoiceProvider.get_voice_preview_url(provider, voice_id)
            if preview_url:
                st.audio(preview_url, format="audio/mp3")
    
    @staticmethod
    def get_default_voices(provider: str) -> Dict[str, str]:
        """
        Get default voices for a provider when API is not available.
        
        Args:
            provider: TTS provider name
            
        Returns:
            Dictionary of default voices
        """
        defaults = {
            "elevenlabs": {
                "Aria": "9BWtsMINqrJLrRacOk9x",
                "Sarah": "EXAVITQu4vr4xnSDxMaL",
                "Laura": "FGY2WhTYpPnrIDTdsKH5",
                "Charlie": "IKne3meq5aSn9XLyUdCD",
                "George": "JBFqnCBsd6RMkjVDRZzb",
                "Brian": "nPczCjzI2devNBz1zQrb",
                "Daniel": "onwK4e9ZLuTAKqWW03F9",
                "Lily": "pFZP5JQG7iQjIQuC4Bku"
            },
            "openai": {
                "Alloy": "alloy",
                "Echo": "echo",
                "Fable": "fable", 
                "Onyx": "onyx",
                "Nova": "nova",
                "Shimmer": "shimmer"
            },
            "google": {
                "Standard A": "en-US-Standard-A",
                "Standard B": "en-US-Standard-B",
                "Standard C": "en-US-Standard-C",
                "Standard D": "en-US-Standard-D"
            }
        }
        
        return defaults.get(provider, {})