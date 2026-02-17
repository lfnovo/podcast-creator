import os
from typing import Any, Dict, Optional

from loguru import logger
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity import RetryCallState

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_WAIT_MULTIPLIER = 2
DEFAULT_WAIT_MAX = 30

NON_RETRYABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    FileNotFoundError,
    AssertionError,
)


def _log_retry(retry_state: RetryCallState) -> None:
    """Log retry attempts with useful context."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    wait = retry_state.next_action.sleep if retry_state.next_action else 0
    logger.warning(
        f"Retry attempt {retry_state.attempt_number} failed with "
        f"{type(exception).__name__}: {exception}. "
        f"Waiting {wait:.1f}s before next attempt."
    )


def get_retry_config(configurable: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Read retry settings from configurable dict, env vars, or defaults.

    Priority: configurable dict > environment variables > hardcoded defaults.
    """
    configurable = configurable or {}

    max_attempts = (
        configurable.get("retry_max_attempts")
        or _int_env("PODCAST_RETRY_MAX_ATTEMPTS")
        or DEFAULT_MAX_ATTEMPTS
    )
    wait_multiplier = (
        configurable.get("retry_wait_multiplier")
        or _int_env("PODCAST_RETRY_WAIT_MULTIPLIER")
        or DEFAULT_WAIT_MULTIPLIER
    )
    wait_max = (
        configurable.get("retry_wait_max")
        or _int_env("PODCAST_RETRY_WAIT_MAX")
        or DEFAULT_WAIT_MAX
    )

    return {
        "max_attempts": int(max_attempts),
        "wait_multiplier": int(wait_multiplier),
        "wait_max": int(wait_max),
    }


def _int_env(name: str) -> Optional[int]:
    """Read an integer from an environment variable, or return None."""
    val = os.environ.get(name)
    return int(val) if val is not None else None


def create_retry_decorator(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    wait_multiplier: int = DEFAULT_WAIT_MULTIPLIER,
    wait_max: int = DEFAULT_WAIT_MAX,
) -> Any:
    """Return a tenacity retry decorator with exponential backoff.

    Non-retryable exceptions (programming/input errors) are raised immediately.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait_multiplier, max=wait_max),
        retry=retry_if_not_exception_type(NON_RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )
