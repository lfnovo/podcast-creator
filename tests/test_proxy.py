"""
Unit tests for proxy configuration utilities.
"""

import os
import pytest
from podcast_creator.utils import get_proxy, _redact_proxy_url


class TestGetProxy:
    """Tests for get_proxy() function."""

    @pytest.fixture(autouse=True)
    def clear_env_vars(self):
        """Clear proxy-related env vars before and after each test."""
        env_vars = [
            "PODCAST_CREATOR_PROXY",
            "HTTP_PROXY",
            "HTTPS_PROXY",
        ]
        # Store original values
        original_values = {var: os.environ.get(var) for var in env_vars}

        # Clear all proxy env vars
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

        yield

        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    def test_returns_none_when_no_proxy_configured(self):
        """get_proxy() returns None when no proxy is configured."""
        result = get_proxy()
        assert result is None

    def test_returns_runtime_param_when_provided(self):
        """get_proxy() returns the runtime parameter when provided."""
        result = get_proxy("http://runtime-proxy:8080")
        assert result == "http://runtime-proxy:8080"

    def test_runtime_param_overrides_env_vars(self):
        """Runtime parameter takes precedence over all env vars."""
        os.environ["PODCAST_CREATOR_PROXY"] = "http://env-proxy:8080"
        os.environ["HTTP_PROXY"] = "http://http-proxy:8080"

        result = get_proxy("http://runtime-proxy:8080")
        assert result == "http://runtime-proxy:8080"

    def test_returns_podcast_creator_proxy_when_set(self):
        """get_proxy() returns PODCAST_CREATOR_PROXY when set."""
        os.environ["PODCAST_CREATOR_PROXY"] = "http://podcast-proxy:8080"

        result = get_proxy()
        assert result == "http://podcast-proxy:8080"

    def test_podcast_creator_proxy_overrides_http_proxy(self):
        """PODCAST_CREATOR_PROXY takes precedence over HTTP_PROXY."""
        os.environ["PODCAST_CREATOR_PROXY"] = "http://podcast-proxy:8080"
        os.environ["HTTP_PROXY"] = "http://http-proxy:8080"

        result = get_proxy()
        assert result == "http://podcast-proxy:8080"

    def test_falls_back_to_http_proxy(self):
        """get_proxy() falls back to HTTP_PROXY when PODCAST_CREATOR_PROXY not set."""
        os.environ["HTTP_PROXY"] = "http://http-proxy:8080"

        result = get_proxy()
        assert result == "http://http-proxy:8080"

    def test_http_proxy_overrides_https_proxy(self):
        """HTTP_PROXY takes precedence over HTTPS_PROXY."""
        os.environ["HTTP_PROXY"] = "http://http-proxy:8080"
        os.environ["HTTPS_PROXY"] = "https://https-proxy:8080"

        result = get_proxy()
        assert result == "http://http-proxy:8080"

    def test_falls_back_to_https_proxy(self):
        """get_proxy() falls back to HTTPS_PROXY when neither above set."""
        os.environ["HTTPS_PROXY"] = "https://https-proxy:8080"

        result = get_proxy()
        assert result == "https://https-proxy:8080"

    def test_empty_string_explicitly_disables_proxy(self):
        """Passing empty string explicitly disables proxy."""
        os.environ["PODCAST_CREATOR_PROXY"] = "http://env-proxy:8080"

        result = get_proxy("")
        assert result is None

    def test_supports_authenticated_proxy_url(self):
        """get_proxy() supports proxy URLs with credentials."""
        proxy_url = "http://user:password@proxy.example.com:8080"
        result = get_proxy(proxy_url)
        assert result == proxy_url

    def test_supports_https_proxy_url(self):
        """get_proxy() supports HTTPS proxy URLs."""
        proxy_url = "https://secure-proxy.example.com:443"
        result = get_proxy(proxy_url)
        assert result == proxy_url


class TestRedactProxyUrl:
    """Tests for _redact_proxy_url() function."""

    def test_redacts_credentials_from_proxy_url(self):
        """_redact_proxy_url() redacts username and password."""
        proxy_url = "http://user:password@proxy.example.com:8080"
        result = _redact_proxy_url(proxy_url)

        assert "user" not in result
        assert "password" not in result
        assert "***:***@" in result
        assert "proxy.example.com:8080" in result

    def test_preserves_url_without_credentials(self):
        """_redact_proxy_url() preserves URLs without credentials."""
        proxy_url = "http://proxy.example.com:8080"
        result = _redact_proxy_url(proxy_url)
        assert result == proxy_url

    def test_handles_username_only(self):
        """_redact_proxy_url() handles URLs with username but no password."""
        proxy_url = "http://user@proxy.example.com:8080"
        result = _redact_proxy_url(proxy_url)

        assert "user" not in result
        assert "***:***@" in result

    def test_handles_invalid_url_gracefully(self):
        """_redact_proxy_url() handles invalid URLs gracefully."""
        # This should not raise an exception
        result = _redact_proxy_url("not-a-valid-url")
        assert result is not None
