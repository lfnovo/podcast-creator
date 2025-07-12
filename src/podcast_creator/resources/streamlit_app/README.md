# Podcast Creator Studio - Streamlit Interface

A comprehensive web interface for the podcast-creator library that enables users to manage speaker profiles, episode profiles, and generate AI-powered podcasts. 

🚀 **Launch directly with**: `podcast-creator ui`

## Features

### 🏠 Home Dashboard
- Quick stats (episodes, profiles)
- Recent episodes overview
- Quick access to main functions

### 🎙️ Speaker Profiles Management
- Create, edit, clone, and delete speaker profiles
- Import/export profiles from/to JSON files
- Support for multiple TTS providers (ElevenLabs, OpenAI, Google)
- Manage up to 4 speakers per profile

### 📺 Episode Profiles Management
- Create, edit, clone, and delete episode configurations
- Link episode profiles to speaker profiles
- Configure AI models, segments, and default briefings
- Grid-based profile overview

### 🎬 Podcast Generation
- Generate podcasts using episode and speaker profiles
- **Multi-content support**: Combine multiple sources in structured arrays
- Support for multiple content sources:
  - Direct text input
  - File upload (TXT, PDF, DOCX, MD, JSON)
  - URL content extraction (with content-core)
- **Voice selection dropdowns**: Provider-specific voice options
- **Provider availability checking**: Shows only available AI providers
- Real-time generation progress tracking
- Episode name conflict detection with overwrite confirmation
- Comprehensive error handling with retry options

### 📚 Episode Library
- Browse generated episodes with search and filtering
- Audio playback with built-in player
- View transcripts and outlines
- Download episodes as MP3 files
- Delete episodes with confirmation
- Grid and list view modes
- Library statistics

## Quick Start

### 🚀 **Recommended: Use CLI Command**

```bash
# Install podcast-creator
pip install podcast-creator

# Launch the web interface (handles all setup automatically)
podcast-creator ui

# Custom port/host
podcast-creator ui --port 8080 --host 0.0.0.0
```

The CLI command automatically:
- Checks for required dependencies
- Offers to run initialization if needed  
- Extracts and runs the bundled Streamlit app
- Uses your current directory for all configs

### 📁 **Manual Installation (Development)**

1. **Install dependencies:**
   ```bash
   uv add streamlit pydub requests content-core
   ```

2. **Run manually:**
   ```bash
   streamlit run app.py
   ```

3. **Open your browser to:**
   ```
   http://localhost:8501
   ```

## Configuration

### 🎯 **Automatic Configuration (CLI)**

When using `podcast-creator ui`, the app:
- Uses your current working directory for all configs
- Automatically creates missing files via `podcast-creator init`
- Supports all podcast-creator configuration options

### 📁 **File Structure**

The app uses these files in your working directory:
- `speakers_config.json`: Speaker profile configurations
- `episodes_config.json`: Episode profile configurations  
- `prompts/`: Jinja2 template directory
- `output/`: Generated podcasts directory

## Profile Structure

### Speaker Profile Format
```json
{
  "profiles": {
    "profile_name": {
      "tts_provider": "elevenlabs",
      "tts_model": "eleven_flash_v2_5",
      "speakers": [
        {
          "name": "Speaker Name",
          "voice_id": "voice_id_from_provider",
          "backstory": "Rich background that informs expertise",
          "personality": "Speaking style and traits"
        }
      ]
    }
  }
}
```

### Episode Profile Format
```json
{
  "profiles": {
    "profile_name": {
      "speaker_config": "speaker_profile_name",
      "outline_model": "gpt-4o",
      "transcript_model": "gpt-4o",
      "num_segments": 4,
      "default_briefing": "Instructions for podcast generation"
    }
  }
}
```

## Error Handling

The application includes comprehensive error handling:

- **API Errors**: Timeout, rate limiting, authentication issues
- **Content Errors**: Invalid or missing content
- **File Errors**: Missing files, permission issues
- **Generation Errors**: Podcast creation failures

All errors display user-friendly messages with suggested solutions and retry options.

## Features Overview

### Content Extraction
- **Multi-Content Support**: Combine multiple sources in structured arrays
- **Text Input**: Direct paste of content
- **File Upload**: Supports common document formats (TXT, PDF, DOCX, MD, JSON)
- **URL Extraction**: Fetch content from web pages (requires content-core)
- **Content Management**: Add, remove, and reorder content pieces

### Profile Management
- **CRUD Operations**: Full create, read, update, delete functionality
- **Voice Selection**: Provider-specific dropdown menus
- **Provider Checking**: Shows only available AI providers based on API keys
- **Import/Export**: JSON-based profile sharing
- **Validation**: Comprehensive profile validation
- **Cloning**: Duplicate profiles for quick customization

### Podcast Generation
- **Episode Profiles**: Use pre-configured settings
- **Multi-Content Generation**: Pass structured content arrays to AI prompts
- **Provider Availability**: Dynamic provider selection based on environment
- **Override Options**: Customize generation parameters
- **Progress Tracking**: Real-time generation status
- **Error Recovery**: Retry failed generations

### Episode Library
- **Audio Playback**: Built-in Streamlit audio player
- **Transcript Viewing**: Formatted dialogue display with speaker names
- **Download**: Save episodes as MP3 files
- **Search & Filter**: Find episodes quickly
- **Statistics**: Library overview metrics

## Troubleshooting

### Common Issues

1. **"content-core library not available"**
   - Install with: `uv add content-core`
   - Or use direct text input instead

2. **"podcast-creator library not available"**
   - Make sure you're in the correct project directory
   - The main podcast-creator package should be installed

3. **Audio files not playing**
   - Check that episodes were generated successfully
   - Verify the output directory contains audio files

4. **Profile import failures**
   - Ensure JSON format is correct
   - Check that required fields are present

### Getting Help

- Check the error messages for specific guidance
- Use the retry functionality for temporary issues
- Verify your API keys and configuration
- Ensure all required dependencies are installed

## Development

The application is structured as follows:

```
streamlit_app/
├── app.py                 # Main application
├── utils/                 # Utility modules
│   ├── episode_manager.py # Episode management
│   ├── profile_manager.py # Profile CRUD operations
│   ├── content_extractor.py # Content processing
│   ├── async_helpers.py   # Async utilities
│   └── error_handler.py   # Error handling
├── requirements.txt       # Dependencies
└── README.md             # This file
```

The app follows Streamlit best practices with modular utilities and comprehensive error handling.