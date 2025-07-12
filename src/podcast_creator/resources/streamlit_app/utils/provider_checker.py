"""
Provider availability checker for the Podcast Creator Studio.

Checks which AI and TTS providers are available based on environment variables.
"""

import os
import streamlit as st
from typing import Dict, List, Tuple


class ProviderChecker:
    """Utility class for checking provider availability based on environment variables."""
    
    @staticmethod
    def check_available_providers() -> Tuple[List[str], List[str]]:
        """
        Check which providers are available based on environment variables.
        
        Returns:
            Tuple of (available_providers, unavailable_providers)
        """
        provider_status = {}
        
        # AI/LLM Providers
        provider_status["ollama"] = os.environ.get("OLLAMA_API_BASE") is not None
        provider_status["openai"] = os.environ.get("OPENAI_API_KEY") is not None
        provider_status["groq"] = os.environ.get("GROQ_API_KEY") is not None
        provider_status["xai"] = os.environ.get("XAI_API_KEY") is not None
        provider_status["vertexai"] = (
            os.environ.get("VERTEX_PROJECT") is not None
            and os.environ.get("VERTEX_LOCATION") is not None
            and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
        )
        provider_status["gemini"] = (
            os.environ.get("GOOGLE_API_KEY") is not None
            or os.environ.get("GEMINI_API_KEY") is not None
        )
        provider_status["openrouter"] = (
            os.environ.get("OPENROUTER_API_KEY") is not None
            and os.environ.get("OPENAI_API_KEY") is not None
            and os.environ.get("OPENROUTER_BASE_URL") is not None
        )
        provider_status["anthropic"] = os.environ.get("ANTHROPIC_API_KEY") is not None
        provider_status["azure"] = (
            os.environ.get("AZURE_OPENAI_API_KEY") is not None
            and os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
            and os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") is not None
            and os.environ.get("AZURE_OPENAI_API_VERSION") is not None
        )
        provider_status["mistral"] = os.environ.get("MISTRAL_API_KEY") is not None
        provider_status["deepseek"] = os.environ.get("DEEPSEEK_API_KEY") is not None
        
        # TTS Providers
        provider_status["elevenlabs"] = os.environ.get("ELEVENLABS_API_KEY") is not None
        # Note: openai and google are already checked above for LLM, they also do TTS
        
        available_providers = [k for k, v in provider_status.items() if v]
        unavailable_providers = [k for k, v in provider_status.items() if not v]
        
        return available_providers, unavailable_providers
    
    @staticmethod
    def get_available_llm_providers() -> List[str]:
        """
        Get list of available LLM providers.
        
        Returns:
            List of available LLM provider names
        """
        available_providers, _ = ProviderChecker.check_available_providers()
        
        # Filter to only LLM providers (exclude TTS-only providers)
        llm_providers = [
            "ollama", "openai", "groq", "xai", "vertexai", "gemini", 
            "openrouter", "anthropic", "azure", "mistral", "deepseek"
        ]
        
        return [p for p in llm_providers if p in available_providers]
    
    @staticmethod
    def get_available_tts_providers() -> List[str]:
        """
        Get list of available TTS providers.
        
        Returns:
            List of available TTS provider names
        """
        available_providers, _ = ProviderChecker.check_available_providers()
        
        # TTS providers
        tts_providers = ["elevenlabs", "openai", "google"]
        
        return [p for p in tts_providers if p in available_providers]
    
    @staticmethod
    def get_default_models(provider: str) -> Dict[str, str]:
        """
        Get default models for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with default models
        """
        defaults = {
            "openai": {
                "outline": "gpt-4o",
                "transcript": "gpt-4o",
                "tts": "tts-1"
            },
            "anthropic": {
                "outline": "claude-3-5-sonnet-20241022",
                "transcript": "claude-3-5-sonnet-20241022"
            },
            "gemini": {
                "outline": "gemini-1.5-pro",
                "transcript": "gemini-1.5-pro"
            },
            "google": {
                "outline": "gemini-1.5-pro",
                "transcript": "gemini-1.5-pro",
                "tts": "standard"
            },
            "groq": {
                "outline": "llama-3.1-70b-versatile",
                "transcript": "llama-3.1-70b-versatile"
            },
            "ollama": {
                "outline": "llama3.1",
                "transcript": "llama3.1"
            },
            "openrouter": {
                "outline": "meta-llama/llama-3.1-70b-instruct",
                "transcript": "meta-llama/llama-3.1-70b-instruct"
            },
            "azure": {
                "outline": "gpt-4o",
                "transcript": "gpt-4o"
            },
            "mistral": {
                "outline": "mistral-large-latest",
                "transcript": "mistral-large-latest"
            },
            "deepseek": {
                "outline": "deepseek-chat",
                "transcript": "deepseek-chat"
            },
            "xai": {
                "outline": "grok-beta",
                "transcript": "grok-beta"
            },
            "elevenlabs": {
                "tts": "eleven_flash_v2_5"
            }
        }
        
        return defaults.get(provider, {})
    
    @staticmethod
    def render_provider_selector(
        label: str,
        providers: List[str],
        current_provider: str = "",
        key: str = "",
        help_text: str = ""
    ) -> str:
        """
        Render a provider selector with only available providers.
        
        Args:
            label: Label for the selectbox
            providers: List of all possible providers
            current_provider: Currently selected provider
            key: Unique key for the widget
            help_text: Help text for the widget
            
        Returns:
            Selected provider
        """
        available_providers = ProviderChecker.get_available_llm_providers()
        
        # Filter providers to only available ones
        filtered_providers = [p for p in providers if p in available_providers]
        
        if not filtered_providers:
            st.error("❌ No AI providers available. Please configure API keys.")
            return current_provider or ""
        
        # Find current selection index
        current_index = 0
        if current_provider and current_provider in filtered_providers:
            current_index = filtered_providers.index(current_provider)
        elif current_provider not in filtered_providers and filtered_providers:
            # Current provider not available, add it as disabled option
            filtered_providers.insert(0, f"{current_provider} (unavailable)")
            current_index = 0
        
        # Show warning about unavailable providers
        unavailable_count = len(providers) - len(filtered_providers)
        if unavailable_count > 0:
            st.info(f"ℹ️ {unavailable_count} providers unavailable due to missing API keys")
        
        selected = st.selectbox(
            label,
            filtered_providers,
            index=current_index,
            key=key,
            help=help_text
        )
        
        # Clean up the selection if it was marked as unavailable
        if selected and "(unavailable)" in selected:
            return selected.replace(" (unavailable)", "")
        
        return selected
    
    @staticmethod
    def render_tts_provider_selector(
        label: str,
        current_provider: str = "",
        key: str = "",
        help_text: str = ""
    ) -> str:
        """
        Render a TTS provider selector with only available providers.
        
        Args:
            label: Label for the selectbox
            current_provider: Currently selected provider
            key: Unique key for the widget
            help_text: Help text for the widget
            
        Returns:
            Selected provider
        """
        available_providers = ProviderChecker.get_available_tts_providers()
        
        if not available_providers:
            st.error("❌ No TTS providers available. Please configure API keys.")
            return current_provider or ""
        
        # Find current selection index
        current_index = 0
        if current_provider and current_provider in available_providers:
            current_index = available_providers.index(current_provider)
        elif current_provider not in available_providers and available_providers:
            # Current provider not available, add it as disabled option
            available_providers.insert(0, f"{current_provider} (unavailable)")
            current_index = 0
        
        selected = st.selectbox(
            label,
            available_providers,
            index=current_index,
            key=key,
            help=help_text
        )
        
        # Clean up the selection if it was marked as unavailable
        if selected and "(unavailable)" in selected:
            return selected.replace(" (unavailable)", "")
        
        return selected
    
    @staticmethod
    def show_provider_status():
        """Show provider availability status in the UI."""
        available_providers, unavailable_providers = ProviderChecker.check_available_providers()
        
        st.markdown("### 🔌 Provider Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**✅ Available:**")
            if available_providers:
                for provider in sorted(available_providers):
                    st.markdown(f"- {provider}")
            else:
                st.markdown("*No providers configured*")
        
        with col2:
            st.markdown("**❌ Unavailable:**")
            if unavailable_providers:
                for provider in sorted(unavailable_providers):
                    st.markdown(f"- {provider}")
            else:
                st.markdown("*All providers configured*")
        
        if unavailable_providers:
            with st.expander("🔧 Configuration Help"):
                st.markdown("**To enable providers, set these environment variables:**")
                
                config_help = {
                    "openai": "OPENAI_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY", 
                    "groq": "GROQ_API_KEY",
                    "xai": "XAI_API_KEY",
                    "mistral": "MISTRAL_API_KEY",
                    "deepseek": "DEEPSEEK_API_KEY",
                    "elevenlabs": "ELEVENLABS_API_KEY",
                    "gemini": "GOOGLE_API_KEY or GEMINI_API_KEY",
                    "vertexai": "VERTEX_PROJECT, VERTEX_LOCATION, GOOGLE_APPLICATION_CREDENTIALS",
                    "azure": "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION",
                    "openrouter": "OPENROUTER_API_KEY, OPENAI_API_KEY, OPENROUTER_BASE_URL",
                    "ollama": "OLLAMA_API_BASE"
                }
                
                for provider in sorted(unavailable_providers):
                    if provider in config_help:
                        st.markdown(f"**{provider}:** `{config_help[provider]}`")