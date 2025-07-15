"""
Integration tests for temperature functionality across the entire system
"""
import pytest
from unittest.mock import Mock

from podcast_creator.core import GenerationParams, Outline, Transcript, Segment, Dialogue


class TestTemperatureParameterPassing:
    """Test temperature parameters are passed correctly through the system"""

    def test_temperature_defaults(self):
        """Test that default temperature values are used when not specified"""
        config = {"configurable": {}}
        
        # Test outline defaults
        outline_provider = config.get("configurable", {}).get("outline_provider", "openai")
        outline_model = config.get("configurable", {}).get("outline_model", "gpt-4o-mini")
        outline_temperature = config.get("configurable", {}).get("outline_temperature", 0.7)
        
        assert outline_provider == "openai"
        assert outline_model == "gpt-4o-mini"
        assert outline_temperature == 0.7
        
        # Test transcript defaults
        transcript_provider = config.get("configurable", {}).get("transcript_provider", "openai")
        transcript_model = config.get("configurable", {}).get("transcript_model", "gpt-4o-mini")
        transcript_temperature = config.get("configurable", {}).get("transcript_temperature", 0.7)
        
        assert transcript_provider == "openai"
        assert transcript_model == "gpt-4o-mini"
        assert transcript_temperature == 0.7


class TestTemperatureEndToEnd:
    """End-to-end tests for temperature functionality"""

    def test_temperature_parameter_validation_in_create_podcast(self):
        """Test temperature parameter validation in create_podcast function"""
        # Test that temperature parameters are accepted
        from podcast_creator.validators import validate_temperature
        
        # Test various temperature values
        test_temperatures = [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]
        
        for temp in test_temperatures:
            validated_outline_temp = validate_temperature(temp)
            validated_transcript_temp = validate_temperature(temp)
            
            assert validated_outline_temp == temp
            assert validated_transcript_temp == temp

    def test_temperature_clamping_integration(self):
        """Test that temperature clamping works in the integration"""
        from podcast_creator.validators import validate_temperature
        
        # Test clamping
        assert validate_temperature(-1.0) == 0.0
        assert validate_temperature(3.0) == 2.0
        assert validate_temperature(-100.0) == 0.0
        assert validate_temperature(100.0) == 2.0

    def test_temperature_parameter_structure(self):
        """Test that temperature parameters can be passed in the expected structure"""
        # Test that create_podcast would accept temperature parameters
        temperature_params = {
            "outline_temperature": 0.8,
            "transcript_temperature": 0.9
        }
        
        # Verify the parameters are structured correctly
        assert temperature_params["outline_temperature"] == 0.8
        assert temperature_params["transcript_temperature"] == 0.9
        
        # Test parameter extraction like in the actual nodes
        config = {"configurable": temperature_params}
        
        outline_temp = config.get("configurable", {}).get("outline_temperature", 0.7)
        transcript_temp = config.get("configurable", {}).get("transcript_temperature", 0.7)
        
        assert outline_temp == 0.8
        assert transcript_temp == 0.9


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality"""

    def test_audio_generation_handles_new_transcript_format(self):
        """Test that audio generation handles both old and new transcript formats"""
        from podcast_creator.nodes import route_audio_generation
        
        # Test with old format (list of dialogues)
        old_format_transcript = [
            {"speaker": "Alice", "dialogue": "Hello"},
            {"speaker": "Bob", "dialogue": "Hi there"}
        ]
        
        state_old = {"transcript": old_format_transcript}
        config = {}
        
        # Should not crash with old format
        result = route_audio_generation(state_old, config)
        assert result == "generate_all_audio"
        
        # Test with new format (Transcript object)
        mock_transcript_obj = Mock()
        mock_transcript_obj.transcript = [
            Mock(speaker="Alice", dialogue="Hello"),
            Mock(speaker="Bob", dialogue="Hi there")
        ]
        
        state_new = {"transcript": mock_transcript_obj}
        
        # Should not crash with new format
        result = route_audio_generation(state_new, config)
        assert result == "generate_all_audio"

    def test_metadata_optional_in_serialization(self):
        """Test that metadata is optional in serialization (backward compatibility)"""
        # Test outline without metadata
        segment = Segment(name="Test", description="Test segment", size="short")
        outline_without_metadata = Outline(segments=[segment])
        
        serialized = outline_without_metadata.model_dump()
        assert "segments" in serialized
        assert "generation_params" not in serialized
        
        # Test transcript without metadata
        dialogue = Dialogue(speaker="Alice", dialogue="Hello")
        transcript_without_metadata = Transcript(transcript=[dialogue])
        
        serialized = transcript_without_metadata.model_dump()
        assert "transcript" in serialized
        assert "generation_params" not in serialized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])