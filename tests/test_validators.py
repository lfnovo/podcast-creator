"""
Tests for validators module
"""
import pytest
from unittest.mock import patch
from podcast_creator.validators import validate_temperature


class TestValidateTemperature:
    """Tests for validate_temperature function"""

    def test_validate_temperature_valid_values(self):
        """Test valid temperature values"""
        # Test exact boundaries
        assert validate_temperature(0.0) == 0.0
        assert validate_temperature(2.0) == 2.0
        
        # Test valid range
        assert validate_temperature(0.5) == 0.5
        assert validate_temperature(1.0) == 1.0
        assert validate_temperature(1.5) == 1.5
        
        # Test float conversion
        assert validate_temperature(1) == 1.0
        assert isinstance(validate_temperature(1), float)

    def test_validate_temperature_clamp_below_minimum(self):
        """Test temperature clamping below minimum"""
        with patch('podcast_creator.validators.logger') as mock_logger:
            result = validate_temperature(-0.5)
            assert result == 0.0
            mock_logger.warning.assert_called_once_with(
                "Temperature -0.5 below minimum, clamping to 0.0"
            )

    def test_validate_temperature_clamp_above_maximum(self):
        """Test temperature clamping above maximum"""
        with patch('podcast_creator.validators.logger') as mock_logger:
            result = validate_temperature(3.0)
            assert result == 2.0
            mock_logger.warning.assert_called_once_with(
                "Temperature 3.0 above maximum, clamping to 2.0"
            )

    def test_validate_temperature_extreme_values(self):
        """Test extreme temperature values"""
        with patch('podcast_creator.validators.logger') as mock_logger:
            # Very negative
            result = validate_temperature(-100.0)
            assert result == 0.0
            
            # Very positive
            result = validate_temperature(100.0)
            assert result == 2.0
            
            # Should have logged warnings
            assert mock_logger.warning.call_count == 2

    def test_validate_temperature_invalid_type(self):
        """Test invalid temperature types"""
        with pytest.raises(TypeError, match="Temperature must be a number, got str"):
            validate_temperature("invalid")
        
        with pytest.raises(TypeError, match="Temperature must be a number, got NoneType"):
            validate_temperature(None)
        
        with pytest.raises(TypeError, match="Temperature must be a number, got list"):
            validate_temperature([1.0])
        
        with pytest.raises(TypeError, match="Temperature must be a number, got dict"):
            validate_temperature({"temp": 1.0})

    def test_validate_temperature_edge_cases(self):
        """Test edge cases"""
        # Test very small positive number
        result = validate_temperature(0.001)
        assert result == 0.001
        
        # Test very close to maximum
        result = validate_temperature(1.999)
        assert result == 1.999
        
        # Test exactly at boundaries
        result = validate_temperature(0.0)
        assert result == 0.0
        
        result = validate_temperature(2.0)
        assert result == 2.0

    def test_validate_temperature_integer_input(self):
        """Test integer input is converted to float"""
        result = validate_temperature(0)
        assert result == 0.0
        assert isinstance(result, float)
        
        result = validate_temperature(1)
        assert result == 1.0
        assert isinstance(result, float)
        
        result = validate_temperature(2)
        assert result == 2.0
        assert isinstance(result, float)

    def test_validate_temperature_float_precision(self):
        """Test float precision is maintained"""
        test_value = 0.123456789
        result = validate_temperature(test_value)
        assert result == test_value
        
        test_value = 1.987654321
        result = validate_temperature(test_value)
        assert result == test_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])