"""
Tests for the retry utilities module
"""
import os
from unittest.mock import patch

import pytest

from podcast_creator.retry import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_WAIT_MAX,
    DEFAULT_WAIT_MULTIPLIER,
    create_retry_decorator,
    get_retry_config,
)


class TestGetRetryConfig:
    """Tests for get_retry_config()"""

    def test_defaults_when_no_overrides(self):
        """Returns hardcoded defaults when no configurable or env vars."""
        cfg = get_retry_config()
        assert cfg == {
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
            "wait_multiplier": DEFAULT_WAIT_MULTIPLIER,
            "wait_max": DEFAULT_WAIT_MAX,
        }

    def test_configurable_overrides(self):
        """Configurable dict values take precedence."""
        cfg = get_retry_config({"retry_max_attempts": 5, "retry_wait_multiplier": 10})
        assert cfg["max_attempts"] == 5
        assert cfg["wait_multiplier"] == 10
        assert cfg["wait_max"] == DEFAULT_WAIT_MAX

    def test_env_var_overrides(self):
        """Environment variables override defaults."""
        with patch.dict(os.environ, {"PODCAST_RETRY_MAX_ATTEMPTS": "7"}):
            cfg = get_retry_config()
        assert cfg["max_attempts"] == 7

    def test_configurable_takes_precedence_over_env(self):
        """Configurable dict wins over env vars."""
        with patch.dict(os.environ, {"PODCAST_RETRY_MAX_ATTEMPTS": "7"}):
            cfg = get_retry_config({"retry_max_attempts": 2})
        assert cfg["max_attempts"] == 2

    def test_none_configurable_treated_as_empty(self):
        """None configurable falls through to env/defaults."""
        cfg = get_retry_config(None)
        assert cfg["max_attempts"] == DEFAULT_MAX_ATTEMPTS


class TestCreateRetryDecorator:
    """Tests for create_retry_decorator()"""

    def test_retries_on_runtime_error(self):
        """Retries transient errors up to max_attempts."""
        call_count = 0

        @create_retry_decorator(max_attempts=3, wait_multiplier=0, wait_max=0)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient failure")
            return "ok"

        result = flaky()
        assert result == "ok"
        assert call_count == 3

    def test_does_not_retry_value_error(self):
        """Non-retryable exceptions are raised immediately."""
        call_count = 0

        @create_retry_decorator(max_attempts=3, wait_multiplier=0, wait_max=0)
        def bad_input():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            bad_input()
        assert call_count == 1

    def test_does_not_retry_type_error(self):
        """TypeError is not retried."""
        call_count = 0

        @create_retry_decorator(max_attempts=3, wait_multiplier=0, wait_max=0)
        def bad_type():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            bad_type()
        assert call_count == 1

    def test_exhausts_retries_and_reraises(self):
        """After exhausting all attempts, the last exception is reraised."""
        call_count = 0

        @create_retry_decorator(max_attempts=2, wait_multiplier=0, wait_max=0)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("still broken")

        with pytest.raises(RuntimeError, match="still broken"):
            always_fails()
        assert call_count == 2
