"""
Utility functions for podcast-creator.

Provides helper functions for proxy configuration and other common utilities.
"""

import os
from typing import Optional
from urllib.parse import urlparse, urlunparse


def _redact_proxy_url(proxy_url: str) -> str:
    """
    Redact credentials from a proxy URL for safe logging.

    Args:
        proxy_url: The proxy URL that may contain credentials

    Returns:
        The proxy URL with credentials redacted (e.g., http://***:***@host:port)
    """
    try:
        parsed = urlparse(proxy_url)
        if parsed.username or parsed.password:
            # Reconstruct URL with redacted credentials
            redacted_netloc = "***:***@" + (parsed.hostname or "")
            if parsed.port:
                redacted_netloc += f":{parsed.port}"
            return urlunparse(
                (parsed.scheme, redacted_netloc, parsed.path, "", "", "")
            )
        return proxy_url
    except Exception:
        # If parsing fails, return a generic message
        return "<proxy configured>"


def get_proxy(runtime_proxy: Optional[str] = None) -> Optional[str]:
    """
    Get the proxy URL with priority resolution.

    Configuration priority (highest to lowest):
    1. Runtime proxy parameter (passed as argument)
    2. PODCAST_CREATOR_PROXY environment variable
    3. HTTP_PROXY environment variable
    4. HTTPS_PROXY environment variable
    5. None (no proxy)

    Args:
        runtime_proxy: Optional runtime proxy override. Pass empty string ""
                      to explicitly disable proxy for this call.

    Returns:
        str | None: Proxy URL or None if no proxy configured

    Examples:
        >>> get_proxy()  # Returns from env or None
        'http://proxy.example.com:8080'

        >>> get_proxy("http://custom-proxy:8080")  # Runtime override
        'http://custom-proxy:8080'

        >>> get_proxy("")  # Explicitly disable proxy
        None
    """
    # 1. Runtime override (highest priority)
    if runtime_proxy is not None:
        if runtime_proxy == "":
            return None  # Explicitly disabled
        return runtime_proxy

    # 2. App-specific environment variable
    env_proxy = os.environ.get("PODCAST_CREATOR_PROXY")
    if env_proxy:
        return env_proxy

    # 3. Standard HTTP_PROXY
    env_proxy = os.environ.get("HTTP_PROXY")
    if env_proxy:
        return env_proxy

    # 4. Standard HTTPS_PROXY
    env_proxy = os.environ.get("HTTPS_PROXY")
    if env_proxy:
        return env_proxy

    # 5. No proxy configured
    return None
