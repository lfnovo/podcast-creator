"""
Tests for core metadata functionality including GenerationParams, Outline, and Transcript models
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from podcast_creator.core import GenerationParams, Outline, Transcript, Segment, Dialogue


class TestGenerationParams:
    """Tests for GenerationParams model"""

    def test_generation_params_creation(self):
        """Test basic GenerationParams creation"""
        params = GenerationParams(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            timestamp="2025-07-15T16:35:30.123456"
        )
        
        assert params.provider == "openai"
        assert params.model == "gpt-4o-mini"
        assert params.temperature == 0.7
        assert params.timestamp == "2025-07-15T16:35:30.123456"

    def test_generation_params_serialization(self):
        """Test GenerationParams serialization"""
        params = GenerationParams(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            temperature=0.8,
            timestamp="2025-07-15T16:35:30.123456"
        )
        
        serialized = params.model_dump()
        expected = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-latest",
            "temperature": 0.8,
            "timestamp": "2025-07-15T16:35:30.123456"
        }
        assert serialized == expected


class TestOutlineWithMetadata:
    """Tests for Outline model with generation metadata"""

    def test_outline_without_metadata(self):
        """Test outline without generation metadata (backward compatibility)"""
        segment = Segment(name="Intro", description="Introduction", size="short")
        outline = Outline(segments=[segment])
        
        assert len(outline.segments) == 1
        assert outline.generation_params is None
        
        # Test serialization
        serialized = outline.model_dump()
        assert "segments" in serialized
        assert "generation_params" not in serialized

    def test_outline_with_metadata(self):
        """Test outline with generation metadata"""
        segment = Segment(name="Intro", description="Introduction", size="short")
        gen_params = GenerationParams(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            timestamp="2025-07-15T16:35:30.123456"
        )
        outline = Outline(segments=[segment], generation_params=gen_params)
        
        assert len(outline.segments) == 1
        assert outline.generation_params is not None
        assert outline.generation_params.provider == "openai"
        assert outline.generation_params.temperature == 0.7

    def test_outline_serialization_with_metadata(self):
        """Test outline serialization includes metadata"""
        segment = Segment(name="Intro", description="Introduction", size="short")
        gen_params = GenerationParams(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            timestamp="2025-07-15T16:35:30.123456"
        )
        outline = Outline(segments=[segment], generation_params=gen_params)
        
        serialized = outline.model_dump()
        assert "segments" in serialized
        assert "generation_params" in serialized
        assert serialized["generation_params"]["provider"] == "openai"
        assert serialized["generation_params"]["temperature"] == 0.7

    def test_outline_json_serialization(self):
        """Test outline JSON serialization with metadata"""
        segment = Segment(name="Intro", description="Introduction", size="short")
        gen_params = GenerationParams(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            timestamp="2025-07-15T16:35:30.123456"
        )
        outline = Outline(segments=[segment], generation_params=gen_params)
        
        json_str = outline.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "segments" in parsed
        assert "generation_params" in parsed
        assert parsed["generation_params"]["provider"] == "openai"
        assert parsed["generation_params"]["temperature"] == 0.7


class TestTranscriptWithMetadata:
    """Tests for Transcript model with generation metadata"""

    def test_transcript_without_metadata(self):
        """Test transcript without generation metadata (backward compatibility)"""
        dialogue = Dialogue(speaker="Alice", dialogue="Hello world")
        transcript = Transcript(transcript=[dialogue])
        
        assert len(transcript.transcript) == 1
        assert transcript.generation_params is None
        
        # Test serialization
        serialized = transcript.model_dump()
        assert "transcript" in serialized
        assert "generation_params" not in serialized

    def test_transcript_with_metadata(self):
        """Test transcript with generation metadata"""
        dialogue = Dialogue(speaker="Alice", dialogue="Hello world")
        gen_params = GenerationParams(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            temperature=0.8,
            timestamp="2025-07-15T16:35:30.123456"
        )
        transcript = Transcript(transcript=[dialogue], generation_params=gen_params)
        
        assert len(transcript.transcript) == 1
        assert transcript.generation_params is not None
        assert transcript.generation_params.provider == "anthropic"
        assert transcript.generation_params.temperature == 0.8

    def test_transcript_serialization_with_metadata(self):
        """Test transcript serialization includes metadata"""
        dialogue = Dialogue(speaker="Alice", dialogue="Hello world")
        gen_params = GenerationParams(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            temperature=0.8,
            timestamp="2025-07-15T16:35:30.123456"
        )
        transcript = Transcript(transcript=[dialogue], generation_params=gen_params)
        
        serialized = transcript.model_dump()
        assert "transcript" in serialized
        assert "generation_params" in serialized
        assert serialized["generation_params"]["provider"] == "anthropic"
        assert serialized["generation_params"]["temperature"] == 0.8

    def test_transcript_json_serialization(self):
        """Test transcript JSON serialization with metadata"""
        dialogue = Dialogue(speaker="Alice", dialogue="Hello world")
        gen_params = GenerationParams(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            temperature=0.8,
            timestamp="2025-07-15T16:35:30.123456"
        )
        transcript = Transcript(transcript=[dialogue], generation_params=gen_params)
        
        json_str = transcript.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "transcript" in parsed
        assert "generation_params" in parsed
        assert parsed["generation_params"]["provider"] == "anthropic"
        assert parsed["generation_params"]["temperature"] == 0.8


class TestMetadataIntegration:
    """Integration tests for metadata functionality"""

    def test_metadata_timestamp_format(self):
        """Test that timestamp is in correct ISO format"""
        # Mock datetime.now() to return a consistent value
        with patch('podcast_creator.nodes.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.isoformat.return_value = "2025-07-15T16:35:30.123456"
            mock_datetime.now.return_value = mock_now
            
            params = GenerationParams(
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.7,
                timestamp=mock_now.isoformat()
            )
            
            # Verify timestamp format
            timestamp = params.timestamp
            try:
                # Should be parseable as ISO format
                datetime.fromisoformat(timestamp)
                assert True
            except ValueError:
                pytest.fail(f"Timestamp {timestamp} is not in valid ISO format")

    def test_different_providers_metadata(self):
        """Test metadata with different AI providers"""
        providers_configs = [
            ("openai", "gpt-4o-mini", 0.7),
            ("anthropic", "claude-3-5-sonnet-latest", 0.8),
            ("openai", "gpt-3.5-turbo", 0.5),
        ]
        
        for provider, model, temp in providers_configs:
            params = GenerationParams(
                provider=provider,
                model=model,
                temperature=temp,
                timestamp="2025-07-15T16:35:30.123456"
            )
            
            assert params.provider == provider
            assert params.model == model
            assert params.temperature == temp

    def test_temperature_values_in_metadata(self):
        """Test various temperature values in metadata"""
        temperature_values = [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]
        
        for temp in temperature_values:
            params = GenerationParams(
                provider="openai",
                model="gpt-4o-mini",
                temperature=temp,
                timestamp="2025-07-15T16:35:30.123456"
            )
            
            assert params.temperature == temp
            
            # Test in outline
            segment = Segment(name="Test", description="Test", size="short")
            outline = Outline(segments=[segment], generation_params=params)
            assert outline.generation_params.temperature == temp
            
            # Test in transcript
            dialogue = Dialogue(speaker="Alice", dialogue="Test")
            transcript = Transcript(transcript=[dialogue], generation_params=params)
            assert transcript.generation_params.temperature == temp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])