"""
Podcast Creator Studio - Streamlit Interface

A comprehensive web interface for managing speaker profiles, episode profiles,
and generating podcasts using the podcast-creator library.
"""

import nest_asyncio
nest_asyncio.apply()

import streamlit as st
import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path to import podcast_creator
sys.path.append(str(Path(__file__).parent.parent))

# Import utilities
from utils import EpisodeManager, ProfileManager, ContentExtractor, run_async_in_streamlit, ErrorHandler, VoiceProvider, ProviderChecker

# Use current working directory for all profile management
WORKING_DIR = Path.cwd()

# Configure page
st.set_page_config(
    page_title="Podcast Creator Studio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f1f1f;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        margin: 0;
        opacity: 0.9;
    }
    
    .quick-action-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .quick-action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<div class="main-header">🎙️ Podcast Creator Studio</div>', unsafe_allow_html=True)
    
    # Initialize current page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    
    # Handle programmatic navigation
    if st.session_state.get('navigate_to_library', False):
        st.session_state.current_page = "📚 Episode Library"
        st.session_state.navigate_to_library = False
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        st.markdown("---")
        
        # Navigation menu
        pages = [
            "🏠 Home",
            "🎙️ Speaker Profiles", 
            "📺 Episode Profiles",
            "🎬 Generate Podcast",
            "📚 Episode Library"
        ]
        
        # Find current page index
        current_index = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
        
        page = st.selectbox(
            "Choose a page:",
            pages,
            index=current_index,
            key="navigation_selectbox"
        )
        
        # Update current page if changed
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        
        if st.button("🎬 Generate Podcast", use_container_width=True):
            st.session_state.current_page = "🎬 Generate Podcast"
            st.rerun()
            
        if st.button("📚 View Episodes", use_container_width=True):
            st.session_state.current_page = "📚 Episode Library"
            st.rerun()
    
    # Use the current page from session state
    page = st.session_state.current_page
    
    # Route to appropriate page
    if page == "🏠 Home":
        show_home_page()
    elif page == "🎙️ Speaker Profiles":
        show_speaker_profiles_page()
    elif page == "📺 Episode Profiles":
        show_episode_profiles_page()
    elif page == "🎬 Generate Podcast":
        show_generate_podcast_page()
    elif page == "📚 Episode Library":
        show_episode_library_page()

def show_home_page():
    """Display the home page with dashboard and quick stats."""
    st.subheader("Welcome to Podcast Creator Studio")
    st.markdown("Your all-in-one solution for AI-powered podcast creation")
    
    # Initialize managers
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Get stats
    try:
        episodes_stats = episode_manager.get_episodes_stats()
        profiles_stats = profile_manager.get_profiles_stats()
        
        # Quick stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{episodes_stats['total_episodes']}</p>
                <p class="stat-label">Total Episodes</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{profiles_stats['speaker_profiles_count']}</p>
                <p class="stat-label">Speaker Profiles</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{profiles_stats['episode_profiles_count']}</p>
                <p class="stat-label">Episode Profiles</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Recent episodes
        st.subheader("Recent Episodes")
        
        recent_episodes = episode_manager.scan_episodes_directory()
        if recent_episodes:
            for episode in recent_episodes[:5]:  # Show last 5 episodes
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{episode.name}**")
                    if episode.created_date:
                        st.markdown(f"*Created: {episode.created_date.strftime('%Y-%m-%d %H:%M')}*")
                    if episode.duration:
                        st.markdown(f"*Duration: {episode_manager.format_duration(episode.duration)}*")
                
                with col2:
                    if episode.audio_file and st.button("▶️ Play", key=f"play_{episode.name}"):
                        st.session_state.selected_episode = episode
                        st.session_state.current_page = "📚 Episode Library"
                        st.rerun()
                
                with col3:
                    if st.button("📄 Details", key=f"details_{episode.name}"):
                        st.session_state.selected_episode = episode
                        st.session_state.current_page = "📚 Episode Library"
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("📝 No episodes found. Start by generating your first podcast!")
        
        st.markdown("---")
        
        # Provider Status
        st.markdown("---")
        ProviderChecker.show_provider_status()
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎬 Create New Podcast", use_container_width=True, type="primary"):
                st.session_state.current_page = "🎬 Generate Podcast"
                st.rerun()
        
        with col2:
            if st.button("📁 Import Profiles", use_container_width=True):
                st.session_state.current_page = "🎙️ Speaker Profiles"
                st.rerun()
    
    except Exception as e:
        st.error(f"Error loading home page data: {str(e)}")
        st.markdown("Please check that all required files are in place and try again.")

def show_speaker_profiles_page():
    """Display the speaker profiles management page."""
    st.subheader("🎙️ Speaker Profiles")
    st.markdown("Manage your speaker configurations")
    
    # Initialize profile manager
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Load profiles
    try:
        profiles = profile_manager.load_speaker_profiles()
        profile_names = list(profiles.get("profiles", {}).keys())
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ New Profile", use_container_width=True):
                st.session_state.show_new_speaker_form = True
                st.rerun()
        
        with col2:
            if st.button("📁 Import", use_container_width=True):
                st.session_state.show_import_speaker_form = True
                st.rerun()
        
        with col3:
            if st.button("💾 Export All", use_container_width=True):
                export_data = profile_manager.export_speaker_profiles()
                st.download_button(
                    label="Download speakers_config.json",
                    data=json.dumps(export_data, indent=2),
                    file_name="speakers_config.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        
        # Import form
        if st.session_state.get("show_import_speaker_form", False):
            st.subheader("📁 Import Speaker Profiles")
            
            uploaded_file = st.file_uploader(
                "Choose a JSON file to import",
                type=['json'],
                key="speaker_import_file"
            )
            
            if uploaded_file is not None:
                try:
                    file_content = uploaded_file.read().decode('utf-8')
                    imported_names = profile_manager.import_speaker_profiles(file_content)
                    
                    if imported_names:
                        st.success(f"✅ Successfully imported {len(imported_names)} profiles: {', '.join(imported_names)}")
                        st.session_state.show_import_speaker_form = False
                        st.rerun()
                    else:
                        st.warning("⚠️ No new profiles imported. Check if profiles already exist or file format is correct.")
                except Exception as e:
                    st.error(f"❌ Error importing profiles: {str(e)}")
            
            if st.button("❌ Cancel Import"):
                st.session_state.show_import_speaker_form = False
                st.rerun()
            
            st.markdown("---")
        
        # New profile form
        if st.session_state.get("show_new_speaker_form", False):
            st.subheader("➕ Create New Speaker Profile")
            
            profile_name = st.text_input("Profile Name:", placeholder="e.g., my_podcasters", key="new_profile_name")
            
            col1, col2 = st.columns(2)
            with col1:
                tts_provider = ProviderChecker.render_tts_provider_selector(
                    "TTS Provider:",
                    current_provider="elevenlabs",
                    key="new_tts_provider",
                    help_text="Choose a Text-to-Speech provider"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(tts_provider)
                default_model = defaults.get("tts", "eleven_flash_v2_5")
                tts_model = st.text_input("TTS Model:", value=default_model, key="new_tts_model")
            
            st.markdown("### Speakers")
            
            # Initialize speakers in session state
            if 'new_speakers' not in st.session_state:
                st.session_state.new_speakers = [{'name': '', 'voice_id': '', 'backstory': '', 'personality': ''}]
            
            for i, speaker in enumerate(st.session_state.new_speakers):
                st.markdown(f"**Speaker {i+1}:**")
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    speaker_name = st.text_input(f"Name:", key=f"new_speaker_name_{i}", value=speaker.get('name', ''))
                    
                    # Voice selection with provider-specific voices
                    voice_id = VoiceProvider.render_voice_selector(
                        provider=tts_provider,
                        model=tts_model,
                        current_voice_id=speaker.get('voice_id', ''),
                        key=f"new_voice_id_{i}",
                        help_text=f"Choose a voice from {tts_provider}"
                    )
                    
                    # Show voice preview if available
                    if voice_id and tts_provider == "elevenlabs":
                        with st.expander("🎵 Voice Preview"):
                            VoiceProvider.render_voice_preview(tts_provider, voice_id)
                    
                    backstory = st.text_area(f"Backstory:", key=f"new_backstory_{i}", value=speaker.get('backstory', ''))
                    personality = st.text_area(f"Personality:", key=f"new_personality_{i}", value=speaker.get('personality', ''))
                    
                    # Update speaker data
                    st.session_state.new_speakers[i] = {
                        'name': speaker_name,
                        'voice_id': voice_id,
                        'backstory': backstory,
                        'personality': personality
                    }
                
                with col2:
                    if len(st.session_state.new_speakers) > 1:
                        if st.button(f"🗑️", key=f"new_remove_speaker_{i}"):
                            st.session_state.new_speakers.pop(i)
                            st.rerun()
                
                st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Add Speaker", key="new_add_speaker") and len(st.session_state.new_speakers) < 4:
                    st.session_state.new_speakers.append({'name': '', 'voice_id': '', 'backstory': '', 'personality': ''})
                    st.rerun()
            
            st.markdown("---")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Create Profile", type="primary", key="create_speaker_profile"):
                    if not profile_name:
                        st.error("Profile name is required")
                    elif profile_name in profile_names:
                        st.error(f"Profile '{profile_name}' already exists")
                    else:
                        # Create profile data
                        profile_data = {
                            "tts_provider": tts_provider,
                            "tts_model": tts_model,
                            "speakers": st.session_state.new_speakers
                        }
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_speaker_profile(profile_data)
                        if validation_errors:
                            st.error("❌ Validation errors:")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Create the profile
                            if profile_manager.create_speaker_profile(profile_name, profile_data):
                                st.success(f"✅ Profile '{profile_name}' created successfully!")
                                st.session_state.show_new_speaker_form = False
                                if 'new_speakers' in st.session_state:
                                    del st.session_state.new_speakers
                                st.rerun()
                            else:
                                st.error("❌ Failed to create profile")
            
            with col2:
                if st.button("❌ Cancel", key="cancel_new_speaker"):
                    st.session_state.show_new_speaker_form = False
                    if 'new_speakers' in st.session_state:
                        del st.session_state.new_speakers
                    st.rerun()
            
            st.markdown("---")
        
        # Edit profile form
        if st.session_state.get("edit_speaker_profile"):
            edit_profile_name = st.session_state.edit_speaker_profile
            edit_profile_data = profile_manager.get_speaker_profile(edit_profile_name)
            
            if edit_profile_data:
                st.subheader(f"✏️ Edit Speaker Profile: {edit_profile_name}")
                
                col1, col2 = st.columns(2)
                with col1:
                    current_tts_provider = edit_profile_data.get('tts_provider', 'elevenlabs')
                    tts_provider = ProviderChecker.render_tts_provider_selector(
                        "TTS Provider:",
                        current_provider=current_tts_provider,
                        key="edit_speaker_tts_provider",
                        help_text="Choose a Text-to-Speech provider"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(tts_provider)
                    default_model = defaults.get("tts", "eleven_flash_v2_5")
                    
                    current_tts_model = edit_profile_data.get('tts_model', default_model)
                    tts_model = st.text_input(
                        "TTS Model:", 
                        value=current_tts_model,
                        key="edit_speaker_tts_model"
                    )
                
                st.markdown("### Speakers")
                
                # Initialize edit speakers
                if 'edit_speakers' not in st.session_state:
                    st.session_state.edit_speakers = edit_profile_data.get('speakers', [])
                
                for i, speaker in enumerate(st.session_state.edit_speakers):
                    st.markdown(f"**Speaker {i+1}:**")
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        speaker_name = st.text_input(
                            f"Name:", 
                            key=f"edit_speaker_name_{i}", 
                            value=speaker.get('name', '')
                        )
                        
                        # Voice selection with provider-specific voices
                        voice_id = VoiceProvider.render_voice_selector(
                            provider=tts_provider,
                            model=tts_model,
                            current_voice_id=speaker.get('voice_id', ''),
                            key=f"edit_voice_id_{i}",
                            help_text=f"Choose a voice from {tts_provider}"
                        )
                        
                        # Show voice preview if available
                        if voice_id and tts_provider == "elevenlabs":
                            with st.expander("🎵 Voice Preview"):
                                VoiceProvider.render_voice_preview(tts_provider, voice_id)
                        
                        backstory = st.text_area(
                            f"Backstory:", 
                            key=f"edit_backstory_{i}", 
                            value=speaker.get('backstory', '')
                        )
                        personality = st.text_area(
                            f"Personality:", 
                            key=f"edit_personality_{i}", 
                            value=speaker.get('personality', '')
                        )
                        
                        # Update speaker data
                        st.session_state.edit_speakers[i] = {
                            'name': speaker_name,
                            'voice_id': voice_id,
                            'backstory': backstory,
                            'personality': personality
                        }
                    
                    with col2:
                        if len(st.session_state.edit_speakers) > 1:
                            if st.button(f"🗑️", key=f"edit_remove_speaker_{i}"):
                                st.session_state.edit_speakers.pop(i)
                                st.rerun()
                    
                    st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("➕ Add Speaker", key="edit_add_speaker") and len(st.session_state.edit_speakers) < 4:
                        st.session_state.edit_speakers.append({'name': '', 'voice_id': '', 'backstory': '', 'personality': ''})
                        st.rerun()
                
                st.markdown("---")
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Save Changes", type="primary", key="save_speaker_changes"):
                        # Update profile data
                        updated_profile_data = {
                            "tts_provider": tts_provider,
                            "tts_model": tts_model,
                            "speakers": st.session_state.edit_speakers
                        }
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_speaker_profile(updated_profile_data)
                        if validation_errors:
                            st.error("❌ Validation errors:")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Update the profile
                            if profile_manager.update_speaker_profile(edit_profile_name, updated_profile_data):
                                st.success(f"✅ Profile '{edit_profile_name}' updated successfully!")
                                st.session_state.edit_speaker_profile = None
                                if 'edit_speakers' in st.session_state:
                                    del st.session_state.edit_speakers
                                st.rerun()
                            else:
                                st.error("❌ Failed to update profile")
                
                with col2:
                    if st.button("❌ Cancel Edit", key="cancel_edit_speaker"):
                        st.session_state.edit_speaker_profile = None
                        if 'edit_speakers' in st.session_state:
                            del st.session_state.edit_speakers
                        st.rerun()
                
                st.markdown("---")
            else:
                st.error(f"Speaker profile '{edit_profile_name}' not found")
                st.session_state.edit_speaker_profile = None
                st.rerun()
        
        # Display existing profiles
        st.subheader("Existing Speaker Profiles")
        
        if profile_names:
            for profile_name in profile_names:
                profile_data = profiles["profiles"][profile_name]
                
                with st.expander(f"🎙️ {profile_name}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**TTS Provider:** {profile_data.get('tts_provider', 'N/A')}")
                        st.markdown(f"**TTS Model:** {profile_data.get('tts_model', 'N/A')}")
                        st.markdown(f"**Number of Speakers:** {len(profile_data.get('speakers', []))}")
                        
                        # Show speakers
                        speakers = profile_data.get('speakers', [])
                        if speakers:
                            st.markdown("**Speakers:**")
                            for i, speaker in enumerate(speakers):
                                st.markdown(f"• **{speaker.get('name', 'Unnamed')}** - {speaker.get('voice_id', 'No voice ID')}")
                    
                    with col2:
                        st.markdown("**Actions:**")
                        
                        # Edit button
                        if st.button("✏️ Edit", key=f"edit_{profile_name}"):
                            st.session_state.edit_speaker_profile = profile_name
                            st.rerun()
                        
                        # Clone button
                        if st.button("📋 Clone", key=f"clone_{profile_name}"):
                            new_name = f"{profile_name}_copy"
                            if profile_manager.clone_speaker_profile(profile_name, new_name):
                                st.success(f"✅ Profile cloned as '{new_name}'")
                                st.rerun()
                            else:
                                st.error("❌ Failed to clone profile")
                        
                        # Export button
                        export_data = profile_manager.export_speaker_profiles([profile_name])
                        st.download_button(
                            label="💾 Export",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"{profile_name}_speaker_config.json",
                            mime="application/json",
                            key=f"export_{profile_name}"
                        )
                        
                        # Delete button
                        if st.button("🗑️ Delete", key=f"delete_{profile_name}"):
                            if profile_manager.delete_speaker_profile(profile_name):
                                st.success(f"✅ Profile '{profile_name}' deleted")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete profile")
        else:
            st.info("No speaker profiles found. Create your first profile to get started!")
    
    except Exception as e:
        st.error(f"Error loading speaker profiles: {str(e)}")
        st.markdown("Please check your configuration files and try again.")

def show_episode_profiles_page():
    """Display the episode profiles management page."""
    st.subheader("📺 Episode Profiles")
    st.markdown("Manage your episode configurations")
    
    # Define available providers for use throughout the function
    all_providers = ["openai", "anthropic", "google", "groq", "ollama", "openrouter", "azure", "mistral", "deepseek", "xai"]
    
    # Initialize profile manager
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Load profiles
    try:
        profiles = profile_manager.load_episode_profiles()
        profile_names = list(profiles.get("profiles", {}).keys())
        speaker_profile_names = profile_manager.get_speaker_profile_names()
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ New Profile", use_container_width=True):
                st.session_state.show_new_episode_form = True
                st.rerun()
        
        with col2:
            if st.button("📁 Import", use_container_width=True):
                st.session_state.show_import_episode_form = True
                st.rerun()
        
        with col3:
            if st.button("💾 Export All", use_container_width=True):
                export_data = profile_manager.export_episode_profiles()
                st.download_button(
                    label="Download episodes_config.json",
                    data=json.dumps(export_data, indent=2),
                    file_name="episodes_config.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        
        # Import form
        if st.session_state.get("show_import_episode_form", False):
            st.subheader("📁 Import Episode Profiles")
            
            uploaded_file = st.file_uploader(
                "Choose a JSON file to import",
                type=['json'],
                key="episode_import_file"
            )
            
            if uploaded_file is not None:
                try:
                    file_content = uploaded_file.read().decode('utf-8')
                    imported_names = profile_manager.import_episode_profiles(file_content)
                    
                    if imported_names:
                        st.success(f"✅ Successfully imported {len(imported_names)} profiles: {', '.join(imported_names)}")
                        st.session_state.show_import_episode_form = False
                        st.rerun()
                    else:
                        st.warning("⚠️ No new profiles imported. Check if profiles already exist or file format is correct.")
                except Exception as e:
                    st.error(f"❌ Error importing profiles: {str(e)}")
            
            if st.button("❌ Cancel Import"):
                st.session_state.show_import_episode_form = False
                st.rerun()
            
            st.markdown("---")
        
        # New profile form
        if st.session_state.get("show_new_episode_form", False):
            st.subheader("➕ Create New Episode Profile")
            
            profile_name = st.text_input("Profile Name:", placeholder="e.g., my_tech_talks", key="new_episode_name")
            
            if speaker_profile_names:
                speaker_config = st.selectbox("Speaker Profile:", speaker_profile_names, key="new_episode_speaker")
            else:
                st.error("⚠️ No speaker profiles found. Please create a speaker profile first.")
                speaker_config = None
            
            st.markdown("### AI Model Configuration")
            
            # Outline Model Configuration
            st.markdown("**Outline Generation:**")
            col1, col2 = st.columns(2)
            with col1:
                outline_provider = ProviderChecker.render_provider_selector(
                    "Outline Provider:",
                    all_providers,
                    current_provider="openai",
                    key="new_episode_outline_provider",
                    help_text="Choose an AI provider for generating podcast outlines"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(outline_provider)
                default_outline_model = defaults.get("outline", "gpt-4o")
                
                outline_model = st.text_input(
                    "Outline Model:",
                    value=default_outline_model,
                    placeholder=default_outline_model,
                    key="new_episode_outline_model"
                )
            
            # Transcript Model Configuration
            st.markdown("**Transcript Generation:**")
            col1, col2 = st.columns(2)
            with col1:
                transcript_provider = ProviderChecker.render_provider_selector(
                    "Transcript Provider:",
                    all_providers,
                    current_provider="openai",
                    key="new_episode_transcript_provider",
                    help_text="Choose an AI provider for generating podcast transcripts"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(transcript_provider)
                default_transcript_model = defaults.get("transcript", "gpt-4o")
                
                transcript_model = st.text_input(
                    "Transcript Model:",
                    value=default_transcript_model,
                    placeholder=default_transcript_model,
                    key="new_episode_transcript_model"
                )
            
            num_segments = st.slider("Number of Segments:", 1, 10, 4, key="new_episode_segments")
            default_briefing = st.text_area(
                "Default Briefing:", 
                value="Create an engaging discussion about the topic",
                height=100,
                key="new_episode_briefing"
            )
            
            st.markdown("---")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Create Profile", type="primary", key="create_episode_profile"):
                    if not profile_name:
                        st.error("Profile name is required")
                    elif profile_name in profile_names:
                        st.error(f"Profile '{profile_name}' already exists")
                    elif not speaker_config:
                        st.error("Speaker profile is required")
                    else:
                        # Create profile data with provider information
                        profile_data = {
                            "speaker_config": speaker_config,
                            "outline_model": outline_model,
                            "outline_provider": outline_provider,
                            "transcript_model": transcript_model,
                            "transcript_provider": transcript_provider,
                            "num_segments": num_segments,
                            "default_briefing": default_briefing
                        }
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_episode_profile(profile_data)
                        if validation_errors:
                            st.error("❌ Validation errors:")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Create the profile
                            if profile_manager.create_episode_profile(profile_name, profile_data):
                                st.success(f"✅ Profile '{profile_name}' created successfully!")
                                st.session_state.show_new_episode_form = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to create profile")
            
            with col2:
                if st.button("❌ Cancel", key="cancel_new_episode"):
                    st.session_state.show_new_episode_form = False
                    st.rerun()
            
            st.markdown("---")
        
        # Edit profile form
        if st.session_state.get("edit_episode_profile"):
            edit_profile_name = st.session_state.edit_episode_profile
            edit_profile_data = profile_manager.get_episode_profile(edit_profile_name)
            
            if edit_profile_data:
                st.subheader(f"✏️ Edit Episode Profile: {edit_profile_name}")
                
                # Profile name (allow renaming)
                new_profile_name = st.text_input(
                    "Profile Name:", 
                    value=edit_profile_name,
                    key="edit_episode_profile_name"
                )
                
                if speaker_profile_names:
                    current_speaker_index = 0
                    if edit_profile_data['speaker_config'] in speaker_profile_names:
                        current_speaker_index = speaker_profile_names.index(edit_profile_data['speaker_config'])
                    
                    speaker_config = st.selectbox(
                        "Speaker Profile:", 
                        speaker_profile_names, 
                        index=current_speaker_index,
                        key="edit_episode_speaker"
                    )
                else:
                    st.error("⚠️ No speaker profiles found.")
                    speaker_config = edit_profile_data.get('speaker_config', '')
                
                st.markdown("### AI Model Configuration")
                
                # Outline Model Configuration
                st.markdown("**Outline Generation:**")
                col1, col2 = st.columns(2)
                with col1:
                    current_outline_provider = edit_profile_data.get('outline_provider', 'openai')
                    outline_provider = ProviderChecker.render_provider_selector(
                        "Outline Provider:",
                        all_providers,
                        current_provider=current_outline_provider,
                        key="edit_episode_outline_provider",
                        help_text="Choose an AI provider for generating podcast outlines"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(outline_provider)
                    default_model = defaults.get("outline", "gpt-4o")
                    
                    current_outline_model = edit_profile_data.get('outline_model', default_model)
                    outline_model = st.text_input(
                        "Outline Model:", 
                        value=current_outline_model,
                        placeholder=default_model,
                        key="edit_episode_outline_model"
                    )
                
                # Transcript Model Configuration
                st.markdown("**Transcript Generation:**")
                col1, col2 = st.columns(2)
                with col1:
                    current_transcript_provider = edit_profile_data.get('transcript_provider', 'openai')
                    transcript_provider = ProviderChecker.render_provider_selector(
                        "Transcript Provider:",
                        all_providers,
                        current_provider=current_transcript_provider,
                        key="edit_episode_transcript_provider",
                        help_text="Choose an AI provider for generating podcast transcripts"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(transcript_provider)
                    default_model = defaults.get("transcript", "gpt-4o")
                    
                    current_transcript_model = edit_profile_data.get('transcript_model', default_model)
                    transcript_model = st.text_input(
                        "Transcript Model:", 
                        value=current_transcript_model,
                        placeholder=default_model,
                        key="edit_episode_transcript_model"
                    )
                
                num_segments = st.slider(
                    "Number of Segments:", 
                    1, 10, 
                    value=edit_profile_data.get('num_segments', 4),
                    key="edit_episode_segments"
                )
                
                default_briefing = st.text_area(
                    "Default Briefing:", 
                    value=edit_profile_data.get('default_briefing', ''),
                    height=100,
                    key="edit_episode_briefing"
                )
                
                st.markdown("---")
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Save Changes", type="primary", key="save_episode_changes"):
                        if not new_profile_name.strip():
                            st.error("Profile name cannot be empty")
                        elif new_profile_name != edit_profile_name and new_profile_name in profile_names:
                            st.error(f"Profile name '{new_profile_name}' already exists")
                        else:
                            # Update profile data with provider information
                            updated_profile_data = {
                                "speaker_config": speaker_config,
                                "outline_model": outline_model,
                                "outline_provider": outline_provider,
                                "transcript_model": transcript_model,
                                "transcript_provider": transcript_provider,
                                "num_segments": num_segments,
                                "default_briefing": default_briefing
                            }
                            
                            # Validate profile
                            validation_errors = profile_manager.validate_episode_profile(updated_profile_data)
                            if validation_errors:
                                st.error("❌ Validation errors:")
                                for error in validation_errors:
                                    st.error(f"• {error}")
                            else:
                                # Handle renaming if needed
                                if new_profile_name != edit_profile_name:
                                    # Create new profile with new name
                                    if profile_manager.create_episode_profile(new_profile_name, updated_profile_data):
                                        # Delete old profile
                                        if profile_manager.delete_episode_profile(edit_profile_name):
                                            st.success(f"✅ Profile renamed from '{edit_profile_name}' to '{new_profile_name}' and updated successfully!")
                                        else:
                                            st.warning(f"✅ New profile '{new_profile_name}' created, but failed to delete old profile '{edit_profile_name}'")
                                    else:
                                        st.error("❌ Failed to create renamed profile")
                                else:
                                    # Update existing profile
                                    if profile_manager.update_episode_profile(edit_profile_name, updated_profile_data):
                                        st.success(f"✅ Profile '{edit_profile_name}' updated successfully!")
                                    else:
                                        st.error("❌ Failed to update profile")
                                
                                st.session_state.edit_episode_profile = None
                                st.rerun()
                
                with col2:
                    if st.button("❌ Cancel Edit", key="cancel_edit_episode"):
                        st.session_state.edit_episode_profile = None
                        st.rerun()
                
                st.markdown("---")
            else:
                st.error(f"Episode profile '{edit_profile_name}' not found")
                st.session_state.edit_episode_profile = None
                st.rerun()
        
        # Display existing profiles
        st.subheader("Existing Episode Profiles")
        
        if profile_names:
            # Display as grid
            cols = st.columns(3)
            
            for i, profile_name in enumerate(profile_names):
                profile_data = profiles["profiles"][profile_name]
                
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"### 📺 {profile_name}")
                        st.markdown(f"**Speaker:** {profile_data.get('speaker_config', 'N/A')}")
                        st.markdown(f"**Segments:** {profile_data.get('num_segments', 'N/A')}")
                        
                        outline_provider = profile_data.get('outline_provider', 'openai')
                        outline_model = profile_data.get('outline_model', 'N/A')
                        st.markdown(f"**Outline:** {outline_provider}/{outline_model}")
                        
                        transcript_provider = profile_data.get('transcript_provider', 'openai')
                        transcript_model = profile_data.get('transcript_model', 'N/A')
                        st.markdown(f"**Transcript:** {transcript_provider}/{transcript_model}")
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_ep_{profile_name}", use_container_width=True):
                                st.session_state.edit_episode_profile = profile_name
                                st.rerun()
                        
                        with col2:
                            if st.button("📋 Clone", key=f"clone_ep_{profile_name}", use_container_width=True):
                                new_name = f"{profile_name}_copy"
                                if profile_manager.clone_episode_profile(profile_name, new_name):
                                    st.success(f"✅ Cloned as '{new_name}'")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to clone")
                        
                        # Export button
                        export_data = profile_manager.export_episode_profiles([profile_name])
                        st.download_button(
                            label="💾 Export",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"{profile_name}_episode_config.json",
                            mime="application/json",
                            key=f"export_ep_{profile_name}",
                            use_container_width=True
                        )
                        
                        # Delete button
                        if st.button("🗑️ Delete", key=f"delete_ep_{profile_name}", use_container_width=True):
                            if profile_manager.delete_episode_profile(profile_name):
                                st.success(f"✅ Deleted '{profile_name}'")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete")
                        
                        # Show more details in expander
                        with st.expander("📋 Details"):
                            st.markdown(f"**Outline Provider:** {profile_data.get('outline_provider', 'openai')}")
                            st.markdown(f"**Outline Model:** {profile_data.get('outline_model', 'N/A')}")
                            st.markdown(f"**Transcript Provider:** {profile_data.get('transcript_provider', 'openai')}")
                            st.markdown(f"**Transcript Model:** {profile_data.get('transcript_model', 'N/A')}")
                            st.markdown("**Default Briefing:**")
                            st.text(profile_data.get('default_briefing', 'No briefing set'))
        else:
            st.info("No episode profiles found. Create your first profile to get started!")
    
    except Exception as e:
        st.error(f"Error loading episode profiles: {str(e)}")
        st.markdown("Please check your configuration files and try again.")

def show_generate_podcast_page():
    """Display the podcast generation page."""
    st.subheader("🎬 Generate Podcast")
    st.markdown("Create new podcast episodes")
    
    # Initialize managers
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    
    try:
        # Load available profiles
        episode_profiles = profile_manager.get_episode_profile_names()
        speaker_profiles = profile_manager.get_speaker_profile_names()
        
        if not episode_profiles:
            st.error("⚠️ No episode profiles found. Please create an episode profile first.")
            if st.button("📺 Go to Episode Profiles"):
                st.session_state.current_page = "📺 Episode Profiles"
                st.rerun()
            return
        
        # Content input section
        st.markdown("### Step 1: Content Collection")
        
        # Initialize session state for content pieces
        if 'content_pieces' not in st.session_state:
            st.session_state.content_pieces = []
        
        # Add new content section
        with st.expander("➕ Add Content", expanded=len(st.session_state.content_pieces) == 0):
            content_source = st.radio(
                "Content Source:",
                ["Text Input", "File Upload", "URL"],
                horizontal=True,
                key="new_content_source"
            )
            
            if content_source == "Text Input":
                text_content = st.text_area("Enter your content:", height=150, placeholder="Paste your content here...", key="new_text_input")
                
                if st.button("📝 Add Text Content", disabled=not text_content.strip()):
                    if text_content.strip():
                        content_piece = {
                            'type': 'text',
                            'title': f"Text Content {len(st.session_state.content_pieces) + 1}",
                            'content': text_content.strip(),
                            'source': 'Direct input'
                        }
                        st.session_state.content_pieces.append(content_piece)
                        st.rerun()
            
            elif content_source == "File Upload":
                uploaded_file = st.file_uploader(
                    "Upload a file:", 
                    type=['txt', 'pdf', 'docx', 'md', 'json'],
                    help="Supported formats: TXT, PDF, DOCX, MD, JSON",
                    key="new_file_uploader"
                )
                
                if uploaded_file is not None and st.button("📄 Add File Content"):
                    try:
                        if ContentExtractor.is_content_core_available():
                            with st.spinner("Extracting content from file..."):
                                extracted_content = ContentExtractor.extract_from_uploaded_file(uploaded_file)
                                content_piece = {
                                    'type': 'file',
                                    'title': uploaded_file.name,
                                    'content': extracted_content,
                                    'source': f"File: {uploaded_file.name}"
                                }
                                st.session_state.content_pieces.append(content_piece)
                                st.success(f"✅ Added content from {uploaded_file.name}")
                                st.rerun()
                        else:
                            st.error("⚠️ content-core library not available. Install it with: `pip install content-core`")
                    except Exception as e:
                        st.error(f"❌ Error extracting content: {str(e)}")
            
            else:  # URL
                url = st.text_input("Enter URL:", placeholder="https://example.com/article", key="new_url_input")
                
                if url and st.button("🔗 Add URL Content"):
                    if ContentExtractor.validate_url(url):
                        try:
                            if ContentExtractor.is_content_core_available():
                                with st.spinner("Extracting content from URL..."):
                                    extracted_content = run_async_in_streamlit(ContentExtractor.extract_from_url, url)
                                    content_piece = {
                                        'type': 'url',
                                        'title': url,
                                        'content': extracted_content,
                                        'source': f"URL: {url}"
                                    }
                                    st.session_state.content_pieces.append(content_piece)
                                    st.success(f"✅ Added content from URL")
                                    st.rerun()
                            else:
                                st.error("⚠️ content-core library not available. Install it with: `pip install content-core`")
                        except Exception as e:
                            ErrorHandler.handle_streamlit_error(e, {"url": url})
                    else:
                        st.error("❌ Invalid or inaccessible URL")
        
        # Display content pieces
        if st.session_state.content_pieces:
            st.markdown("### Content Pieces")
            
            total_content = ""
            total_chars = 0
            total_words = 0
            
            for i, piece in enumerate(st.session_state.content_pieces):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        # Show content piece info
                        type_icon = {"text": "📝", "file": "📄", "url": "🔗"}.get(piece['type'], "📄")
                        st.markdown(f"**{type_icon} {piece['title']}**")
                        st.markdown(f"*Source: {piece['source']}*")
                        
                        # Content stats
                        piece_stats = ContentExtractor.get_content_stats(piece['content'])
                        st.markdown(f"📊 {piece_stats['character_count']} chars, {piece_stats['word_count']} words")
                        
                        # Preview
                        with st.expander("👀 Preview"):
                            preview = ContentExtractor.truncate_content(piece['content'], 300)
                            st.text(preview)
                    
                    with col2:
                        # Move up/down buttons
                        if i > 0:
                            if st.button("⬆️", key=f"move_up_{i}", help="Move up"):
                                st.session_state.content_pieces[i], st.session_state.content_pieces[i-1] = st.session_state.content_pieces[i-1], st.session_state.content_pieces[i]
                                st.rerun()
                        
                        if i < len(st.session_state.content_pieces) - 1:
                            if st.button("⬇️", key=f"move_down_{i}", help="Move down"):
                                st.session_state.content_pieces[i], st.session_state.content_pieces[i+1] = st.session_state.content_pieces[i+1], st.session_state.content_pieces[i]
                                st.rerun()
                    
                    with col3:
                        # Delete button
                        if st.button("🗑️", key=f"delete_content_{i}", help="Delete"):
                            st.session_state.content_pieces.pop(i)
                            st.rerun()
                
                # Add to statistics
                total_chars += piece_stats['character_count']
                total_words += piece_stats['word_count']
            
            # Actions
            if st.button("🔄 Clear All Content", type="secondary"):
                st.session_state.content_pieces = []
                st.rerun()
            
            # Set content for generation (pass array instead of concatenated string)
            content_pieces = st.session_state.content_pieces
            content_stats = {
                'character_count': total_chars,
                'word_count': total_words,
                'paragraph_count': len(st.session_state.content_pieces),  # Number of pieces instead of paragraphs
                'estimated_reading_time': max(1, total_words // 200)
            }
        else:
            st.info("📝 No content added yet. Use the 'Add Content' section above to add text, files, or URLs.")
            content_pieces = []
            content_stats = None
        
        st.markdown("---")
        
        # Configuration section
        st.markdown("### Step 2: Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            episode_profile = st.selectbox(
                "Episode Profile:",
                episode_profiles,
                help="Choose a pre-configured episode profile",
                key="episode_profile_select"
            )
        
        with col2:
            use_defaults = st.checkbox("Use profile defaults", value=True, key="use_profile_defaults")
        
        # Load selected profile data
        profile_data = profile_manager.get_episode_profile(episode_profile)
        
        if profile_data:
            st.markdown(f"**Profile Info:** {profile_data.get('default_briefing', 'No description')}")
            
            # Override options
            if not use_defaults:
                with st.expander("🔧 Override Settings", expanded=True):
                    speaker_config = st.selectbox(
                        "Speaker Config:",
                        speaker_profiles,
                        index=speaker_profiles.index(profile_data['speaker_config']) if profile_data['speaker_config'] in speaker_profiles else 0
                    )
                    
                    outline_model = st.text_input(
                        "Outline Model:",
                        value=profile_data.get('outline_model', 'gpt-4o')
                    )
                    
                    transcript_model = st.text_input(
                        "Transcript Model:",
                        value=profile_data.get('transcript_model', 'gpt-4o')
                    )
                    
                    num_segments = st.slider(
                        "Number of Segments:",
                        1, 10,
                        value=profile_data.get('num_segments', 4)
                    )
                    
                    briefing = st.text_area(
                        "Briefing:",
                        value=profile_data.get('default_briefing', ''),
                        height=100
                    )
                    
                    briefing_suffix = st.text_input(
                        "Briefing Suffix:",
                        placeholder="Additional instructions..."
                    )
            else:
                # Use profile defaults
                speaker_config = profile_data['speaker_config']
                outline_model = profile_data.get('outline_model', 'gpt-4o')
                transcript_model = profile_data.get('transcript_model', 'gpt-4o')
                num_segments = profile_data.get('num_segments', 4)
                briefing = profile_data.get('default_briefing', '')
                briefing_suffix = ""
        
        st.markdown("---")
        
        # Briefing editor section
        st.markdown("### Step 3: Briefing Editor")
        
        # Initialize briefing in session state if not exists or if profile changed
        if 'custom_briefing' not in st.session_state or 'last_episode_profile' not in st.session_state:
            st.session_state.custom_briefing = briefing
            st.session_state.last_episode_profile = episode_profile
        elif st.session_state.last_episode_profile != episode_profile:
            # Profile changed, update briefing
            st.session_state.custom_briefing = briefing
            st.session_state.last_episode_profile = episode_profile
        
        # Always show briefing editor
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_briefing = st.text_area(
                "Edit Briefing:",
                value=st.session_state.custom_briefing,
                height=120,
                help="Edit the briefing that will be sent to the AI model for podcast generation",
                key="custom_briefing_editor"
            )
        with col2:
            if st.button("🔄 Reset to Default", key="reset_briefing"):
                st.session_state.custom_briefing = briefing
                st.rerun()
        
        # Update session state
        st.session_state.custom_briefing = custom_briefing
        
        # Show briefing preview
        if custom_briefing:
            with st.expander("📋 Briefing Preview"):
                st.markdown(f"**Final briefing that will be sent to the AI:**")
                final_briefing = custom_briefing
                if not use_defaults and briefing_suffix:
                    final_briefing += f"\n\n{briefing_suffix}"
                st.text(final_briefing)
        
        st.markdown("---")
        
        # Output settings section
        st.markdown("### Step 4: Output Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            episode_name = st.text_input(
                "Episode Name:",
                placeholder="my_awesome_podcast",
                help="This will be used as the folder name"
            )
        
        with col2:
            output_dir = st.text_input(
                "Output Directory:",
                value="output",
                help="Base directory for podcast output"
            )
        
        # Check if episode exists
        if episode_name:
            episode_exists = episode_manager.check_episode_exists(episode_name)
            if episode_exists:
                st.warning(f"⚠️ Episode '{episode_name}' already exists. Generation will overwrite existing files.")
                overwrite_confirmed = st.checkbox("✅ I understand and want to overwrite", key="overwrite_confirm")
            else:
                overwrite_confirmed = True
        else:
            overwrite_confirmed = True
        
        st.markdown("---")
        
        # Generation section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Validate content pieces instead of concatenated content
            has_valid_content = bool(content_pieces and any(
                piece.get('content', '').strip() and len(piece.get('content', '').strip()) >= 50 
                for piece in content_pieces
            ))
            
            can_generate = (
                has_valid_content and 
                episode_name and 
                overwrite_confirmed
            )
            
            if not content_pieces:
                st.info("📝 Please add content pieces to generate a podcast")
            elif not has_valid_content:
                st.error("❌ Content pieces are too short or invalid. Please provide at least 50 characters of meaningful text in at least one piece.")
            elif not episode_name:
                st.error("❌ Please provide an episode name")
            elif not overwrite_confirmed:
                st.error("❌ Please confirm overwrite to proceed")
        
        with col2:
            if st.button(
                "🎬 Generate Podcast", 
                type="primary", 
                disabled=not can_generate,
                use_container_width=True
            ):
                st.session_state.start_generation = True
                st.rerun()
        
        # Handle podcast generation
        if st.session_state.get("start_generation", False):
            st.session_state.start_generation = False
            
            # Show generation progress
            progress_container = st.container()
            status_container = st.container()
            
            progress_bar = progress_container.progress(0)
            status_text = status_container.empty()
            
            try:
                status_text.text("🚀 Starting podcast generation...")
                progress_bar.progress(10)
                
                # Import podcast creator
                try:
                    from podcast_creator import create_podcast, configure
                    # Configure to use current working directory
                    configure(working_dir=str(WORKING_DIR))
                    podcast_creator_available = True
                except ImportError:
                    podcast_creator_available = False
                    st.error("❌ podcast-creator library not available. Please install it first.")
                    return
                
                if podcast_creator_available:
                    status_text.text("📝 Preparing generation parameters...")
                    progress_bar.progress(20)
                    
                    # Prepare parameters
                    generation_params = {
                        "content": [piece['content'] for piece in content_pieces],
                        "episode_name": episode_name,
                        "output_dir": f"{output_dir}/{episode_name}",
                        "episode_profile": episode_profile
                    }
                    
                    # Add overrides if not using defaults
                    if not use_defaults:
                        generation_params.update({
                            "speaker_config": speaker_config,
                            "outline_model": outline_model,
                            "transcript_model": transcript_model,
                            "num_segments": num_segments,
                            "briefing": st.session_state.custom_briefing
                        })
                        
                        if briefing_suffix:
                            generation_params["briefing_suffix"] = briefing_suffix
                    else:
                        # Even when using defaults, use the custom briefing if modified
                        if st.session_state.custom_briefing != briefing:
                            generation_params["briefing"] = st.session_state.custom_briefing
                    
                    status_text.text("🎙️ Generating podcast... This may take several minutes...")
                    progress_bar.progress(30)
                    
                    # Generate podcast
                    async def generate():
                        return await create_podcast(**generation_params)
                    
                    result = run_async_in_streamlit(generate)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Podcast generation completed!")
                    
                    # Clear content after successful generation
                    st.session_state.generated_content = ""
                    st.session_state.content_stats = None
                    st.session_state.content_pieces = []
                    
                    # Show success message
                    st.success(f"🎉 Podcast '{episode_name}' generated successfully!")
                    
                    if 'final_output_file_path' in result:
                        st.markdown(f"**Audio file:** `{result['final_output_file_path']}`")
                    
                    # Quick actions
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📚 View in Library", type="primary"):
                            st.session_state.current_page = "📚 Episode Library"
                            st.session_state.navigate_to_library = True
                            st.rerun()
                    
                    with col2:
                        if st.button("🎬 Generate Another"):
                            st.rerun()
                    
                    # Clean up progress indicators
                    progress_bar.empty()
                    status_text.empty()
            
            except Exception as e:
                # Clean up progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Handle the error
                total_content_length = sum(len(piece.get('content', '')) for piece in content_pieces) if content_pieces else 0
                ErrorHandler.handle_streamlit_error(e, {
                    "episode_name": episode_name,
                    "episode_profile": episode_profile,
                    "content_pieces_count": len(content_pieces) if content_pieces else 0,
                    "total_content_length": total_content_length
                })
                
                # Show retry button
                if st.button("🔄 Retry Generation", type="primary"):
                    st.session_state.start_generation = True
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error loading generation page: {str(e)}")
        st.markdown("Please check your configuration and try again.")

def show_episode_library_page():
    """Display the episode library and playback page."""
    st.subheader("📚 Episode Library")
    st.markdown("Browse and play your generated episodes")
    
    # Initialize episode manager
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    
    try:
        # Load episodes
        all_episodes = episode_manager.scan_episodes_directory()
        
        if not all_episodes:
            st.info("📝 No episodes found. Start by generating your first podcast!")
            if st.button("🎬 Generate Your First Podcast", type="primary"):
                st.session_state.current_page = "🎬 Generate Podcast"
                st.rerun()
            return
        
        # Search and filter controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 Search episodes:", placeholder="Search by name...")
        
        with col2:
            sort_by = st.selectbox("Sort by:", ["Newest", "Oldest", "A-Z", "Duration"])
        
        with col3:
            view_mode = st.radio("View:", ["Grid", "List"], horizontal=True)
        
        # Filter and sort episodes
        filtered_episodes = episode_manager.search_episodes(search_query, all_episodes)
        sorted_episodes = episode_manager.sort_episodes(filtered_episodes, sort_by)
        
        # Show episode count
        st.markdown(f"**{len(sorted_episodes)} episode(s) found**")
        st.markdown("---")
        
        # Handle selected episode for playback
        selected_episode = st.session_state.get("selected_episode")
        
        # Episode playback section
        if selected_episode and selected_episode.audio_file:
            with st.container(border=True):
                st.markdown(f"### 🎵 Now Playing: {selected_episode.name}")
                
                # Audio player
                if Path(selected_episode.audio_file).exists():
                    audio_file = open(selected_episode.audio_file, 'rb')
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mp3')
                    audio_file.close()
                    
                    # Episode details
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if selected_episode.duration:
                            st.metric("Duration", episode_manager.format_duration(selected_episode.duration))
                    
                    with col2:
                        if selected_episode.speakers_count:
                            st.metric("Speakers", selected_episode.speakers_count)
                    
                    with col3:
                        if selected_episode.file_size:
                            st.metric("File Size", episode_manager.format_file_size(selected_episode.file_size))
                    
                    # Action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("📄 View Transcript", use_container_width=True):
                            st.session_state.show_transcript = True
                            st.rerun()
                    
                    with col2:
                        if st.button("📊 View Outline", use_container_width=True):
                            st.session_state.show_outline = True
                            st.rerun()
                    
                    with col3:
                        # Download button
                        if st.download_button(
                            label="⬇️ Download",
                            data=audio_bytes,
                            file_name=f"{selected_episode.name}.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        ):
                            st.success("📥 Download started!")
                    
                    with col4:
                        if st.button("🗑️ Delete", use_container_width=True):
                            st.session_state.confirm_delete = selected_episode.name
                            st.rerun()
                else:
                    st.error("❌ Audio file not found")
                
                # Show transcript
                if st.session_state.get("show_transcript", False):
                    if selected_episode.transcript_file and Path(selected_episode.transcript_file).exists():
                        with st.expander("📄 Transcript", expanded=True):
                            try:
                                with open(selected_episode.transcript_file, 'r', encoding='utf-8') as f:
                                    transcript_data = json.load(f)
                                
                                if isinstance(transcript_data, list):
                                    for i, segment in enumerate(transcript_data):
                                        if isinstance(segment, dict):
                                            speaker = segment.get('speaker', f'Speaker {i+1}')
                                            # Try multiple possible field names for the text content
                                            text = (segment.get('text') or 
                                                   segment.get('content') or 
                                                   segment.get('dialogue') or 
                                                   segment.get('message') or 
                                                   segment.get('speech') or '')
                                            
                                            # Debug: Show available keys if text is empty
                                            if not text and st.session_state.get('debug_transcript', False):
                                                st.warning(f"Debug - Segment {i+1} keys: {list(segment.keys())}")
                                                st.json(segment)
                                            
                                            if text:
                                                st.markdown(f"**{speaker}:** {text}")
                                                st.markdown("---")
                                            else:
                                                st.markdown(f"**{speaker}:** *[No content found]*")
                                                st.markdown("---")
                                else:
                                    st.text(str(transcript_data))
                                
                                # Add debug toggle
                                if st.checkbox("🐛 Debug Mode - Show Raw Data", key="debug_transcript_toggle"):
                                    st.session_state.debug_transcript = True
                                    st.json(transcript_data)
                                else:
                                    st.session_state.debug_transcript = False
                            except Exception as e:
                                st.error(f"Error loading transcript: {str(e)}")
                            
                            if st.button("❌ Close Transcript"):
                                st.session_state.show_transcript = False
                                st.rerun()
                    else:
                        st.error("❌ Transcript file not found")
                
                # Show outline
                if st.session_state.get("show_outline", False):
                    if selected_episode.outline_file and Path(selected_episode.outline_file).exists():
                        with st.expander("📊 Outline", expanded=True):
                            try:
                                with open(selected_episode.outline_file, 'r', encoding='utf-8') as f:
                                    outline_data = json.load(f)
                                st.json(outline_data)
                            except Exception as e:
                                st.error(f"Error loading outline: {str(e)}")
                            
                            if st.button("❌ Close Outline"):
                                st.session_state.show_outline = False
                                st.rerun()
                    else:
                        st.error("❌ Outline file not found")
                
                # Stop playback button
                if st.button("⏹️ Stop Playback"):
                    st.session_state.selected_episode = None
                    st.session_state.show_transcript = False
                    st.session_state.show_outline = False
                    st.rerun()
            
            st.markdown("---")
        
        # Handle delete confirmation
        if st.session_state.get("confirm_delete"):
            episode_to_delete = st.session_state.confirm_delete
            
            st.warning(f"⚠️ Are you sure you want to delete episode '{episode_to_delete}'?")
            st.markdown("This action cannot be undone and will permanently delete all episode files.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Yes, Delete", type="primary"):
                    # Find the episode to delete
                    for episode in sorted_episodes:
                        if episode.name == episode_to_delete:
                            if episode_manager.delete_episode(episode.path):
                                st.success(f"✅ Episode '{episode_to_delete}' deleted successfully")
                                if st.session_state.get("selected_episode") and st.session_state.selected_episode.name == episode_to_delete:
                                    st.session_state.selected_episode = None
                                st.session_state.confirm_delete = None
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete episode")
                            break
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.confirm_delete = None
                    st.rerun()
            
            st.markdown("---")
        
        # Display episodes
        if view_mode == "Grid":
            # Grid view
            cols = st.columns(3)
            
            for i, episode in enumerate(sorted_episodes):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"### 🎙️ {episode.name}")
                        
                        if episode.created_date:
                            st.markdown(f"**Created:** {episode.created_date.strftime('%Y-%m-%d %H:%M')}")
                        
                        if episode.duration:
                            st.markdown(f"**Duration:** {episode_manager.format_duration(episode.duration)}")
                        
                        if episode.speakers_count:
                            st.markdown(f"**Speakers:** {episode.speakers_count}")
                        
                        if episode.profile_used:
                            st.markdown(f"**Profile:** {episode.profile_used}")
                        
                        # Action buttons
                        if episode.audio_file and st.button("▶️ Play", key=f"play_grid_{i}", use_container_width=True):
                            st.session_state.selected_episode = episode
                            st.rerun()
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if episode.transcript_file and st.button("📄", key=f"transcript_grid_{i}", help="View Transcript"):
                                st.session_state.selected_episode = episode
                                st.session_state.show_transcript = True
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑️", key=f"delete_grid_{i}", help="Delete Episode"):
                                st.session_state.confirm_delete = episode.name
                                st.rerun()
        
        else:
            # List view
            for i, episode in enumerate(sorted_episodes):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"### 🎙️ {episode.name}")
                        if episode.created_date:
                            st.markdown(f"*Created: {episode.created_date.strftime('%Y-%m-%d %H:%M')}*")
                    
                    with col2:
                        info_lines = []
                        if episode.duration:
                            info_lines.append(f"Duration: {episode_manager.format_duration(episode.duration)}")
                        if episode.speakers_count:
                            info_lines.append(f"Speakers: {episode.speakers_count}")
                        if episode.profile_used:
                            info_lines.append(f"Profile: {episode.profile_used}")
                        
                        for line in info_lines:
                            st.markdown(line)
                    
                    with col3:
                        if episode.audio_file and st.button("▶️ Play", key=f"play_list_{i}"):
                            st.session_state.selected_episode = episode
                            st.rerun()
                        
                        if episode.transcript_file and st.button("📄 Transcript", key=f"transcript_list_{i}"):
                            st.session_state.selected_episode = episode
                            st.session_state.show_transcript = True
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"delete_list_{i}"):
                            st.session_state.confirm_delete = episode.name
                            st.rerun()
        
        # Library statistics
        if sorted_episodes:
            with st.expander("📊 Library Statistics", expanded=False):
                stats = episode_manager.get_episodes_stats()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Episodes", stats['total_episodes'])
                
                with col2:
                    if stats['total_duration'] > 0:
                        total_hours = stats['total_duration'] / 3600
                        st.metric("Total Duration", f"{total_hours:.1f} hours")
                
                with col3:
                    if stats['average_duration'] > 0:
                        st.metric("Average Duration", episode_manager.format_duration(stats['average_duration']))
                
                with col4:
                    if stats['total_size'] > 0:
                        st.metric("Total Size", episode_manager.format_file_size(stats['total_size']))
    
    except Exception as e:
        st.error(f"Error loading episode library: {str(e)}")
        st.markdown("Please check your output directory and try again.")

if __name__ == "__main__":
    main()