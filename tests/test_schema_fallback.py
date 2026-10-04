"""
Tests for the generic JSON fallback when an endpoint rejects json_schema (#51)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest
from loguru import logger

from podcast_creator.nodes import (
    _is_json_schema_rejection,
    generate_outline_node,
    generate_transcript_node,
)

SCHEMA_UNSUPPORTED = "Error code: 400 - response_format json_schema is not supported by this model"
RESPONSE_FORMAT_UNAVAILABLE = (
    'Error code: 400 - {"error": {"message": "This response_format type is unavailable now", '
    '"type": "invalid_request_error"}}'
)


def _error(cls, status, message):
    response = httpx.Response(status, request=httpx.Request("POST", "http://test"))
    return cls(message, response=response, body=None)


def _bad_request(message):
    return _error(openai.BadRequestError, 400, message)


@pytest.fixture
def warnings():
    messages = []
    sink = logger.add(lambda m: messages.append(m), level="WARNING", format="{message}")
    yield messages
    logger.remove(sink)


def _language_model(*responses):
    """A fake esperanto model whose LangChain model returns/raises each response in turn."""
    lc = MagicMock()
    lc.ainvoke = AsyncMock(side_effect=list(responses))
    model = MagicMock()
    model.to_langchain.return_value = lc
    return model


def _outline_state(**extra):
    return {
        "briefing": "test",
        "num_segments": 1,
        "content": "content",
        "speaker_profile": MagicMock(speakers=[]),
        **extra,
    }


def _transcript_state(num_segments=2, **extra):
    outline = MagicMock()
    outline.segments = [MagicMock(size="short") for _ in range(num_segments)]
    for i, segment in enumerate(outline.segments):
        segment.name = f"Segment {i}"
    speaker_profile = MagicMock()
    speaker_profile.get_speaker_names.return_value = ["Alice", "Bob"]
    return {
        "briefing": "test",
        "content": "content",
        "outline": outline,
        "speaker_profile": speaker_profile,
        **extra,
    }


def _structured_types(mock_factory):
    return [c.kwargs["config"]["structured"]["type"] for c in mock_factory.create_language.call_args_list]


OUTLINE_OK = MagicMock(content='{"segments": []}')
TRANSCRIPT_OK = MagicMock(content='{"transcript": []}')


class TestRejectionDetection:
    def test_esperanto_helper_message(self):
        assert _is_json_schema_rejection(_bad_request(SCHEMA_UNSUPPORTED))

    def test_response_format_400_without_json_schema_wording(self):
        assert _is_json_schema_rejection(_bad_request(RESPONSE_FORMAT_UNAVAILABLE))

    def test_unrelated_400_is_not_a_rejection(self):
        assert not _is_json_schema_rejection(_bad_request("Error code: 400 - max_tokens too large"))

    def test_auth_error_mentioning_response_format_is_not_a_rejection(self):
        error = _error(openai.AuthenticationError, 401, "Error code: 401 - response_format: invalid api key")
        assert not _is_json_schema_rejection(error)


@patch("podcast_creator.nodes.get_outline_prompter")
@patch("podcast_creator.nodes.outline_parser")
@patch("podcast_creator.nodes.AIFactory")
class TestOutlineFallback:
    @pytest.mark.parametrize("message", [SCHEMA_UNSUPPORTED, RESPONSE_FORMAT_UNAVAILABLE])
    def test_falls_back_to_json_once(self, mock_factory, mock_parser, mock_prompter, warnings, message):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser.invoke.return_value = MagicMock(segments=[])
        mock_factory.create_language.side_effect = [
            _language_model(_bad_request(message)),
            _language_model(OUTLINE_OK),
        ]

        result = asyncio.run(
            generate_outline_node(_outline_state(), {"configurable": {"outline_provider": "deepseek", "outline_model": "deepseek-chat"}})
        )

        assert _structured_types(mock_factory) == ["json_schema", "json"]
        assert result["json_mode_models"] == ["deepseek/deepseek-chat"]
        assert len([w for w in warnings if "rejected json_schema" in w]) == 1
        mock_parser.invoke.assert_called_once_with('{"segments": []}')

    def test_supported_endpoint_makes_no_extra_request(self, mock_factory, mock_parser, mock_prompter, warnings):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser.invoke.return_value = MagicMock(segments=[])
        mock_factory.create_language.return_value = _language_model(OUTLINE_OK)

        result = asyncio.run(generate_outline_node(_outline_state(), {"configurable": {}}))

        assert _structured_types(mock_factory) == ["json_schema"]
        assert result["json_mode_models"] == []
        assert warnings == []

    def test_other_4xx_errors_are_raised_without_fallback(self, mock_factory, mock_parser, mock_prompter):
        mock_prompter.return_value.render.return_value = "prompt"
        error = _error(openai.AuthenticationError, 401, "Error code: 401 - invalid api key")
        model = _language_model(error)
        mock_factory.create_language.return_value = model

        with pytest.raises(openai.AuthenticationError):
            asyncio.run(generate_outline_node(_outline_state(), {"configurable": {}}))

        assert _structured_types(mock_factory) == ["json_schema"]
        assert model.to_langchain.return_value.ainvoke.await_count == 1  # 4xx is not retried

    def test_explicit_structured_config_is_never_overridden(self, mock_factory, mock_parser, mock_prompter):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_factory.create_language.return_value = _language_model(_bad_request(SCHEMA_UNSUPPORTED))
        explicit = {"type": "json_schema", "schema": {"type": "object"}}

        with pytest.raises(openai.BadRequestError):
            asyncio.run(
                generate_outline_node(
                    _outline_state(), {"configurable": {"outline_config": {"structured": explicit}}}
                )
            )

        assert mock_factory.create_language.call_count == 1
        assert mock_factory.create_language.call_args.kwargs["config"]["structured"] == explicit


@patch("podcast_creator.nodes.get_transcript_prompter")
@patch("podcast_creator.nodes.create_validated_transcript_parser")
@patch("podcast_creator.nodes.AIFactory")
class TestTranscriptFallback:
    def test_falls_back_once_and_reuses_json_for_later_segments(
        self, mock_factory, mock_parser_factory, mock_prompter, warnings
    ):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser_factory.return_value.invoke.return_value = MagicMock(transcript=[])
        json_model = _language_model(TRANSCRIPT_OK, TRANSCRIPT_OK)
        mock_factory.create_language.side_effect = [
            _language_model(_bad_request(SCHEMA_UNSUPPORTED)),
            json_model,
        ]

        result = asyncio.run(generate_transcript_node(_transcript_state(num_segments=2), {"configurable": {}}))

        assert _structured_types(mock_factory) == ["json_schema", "json"]
        assert json_model.to_langchain.return_value.ainvoke.await_count == 2
        assert result["json_mode_models"] == ["openai/gpt-4o-mini"]
        assert len([w for w in warnings if "rejected json_schema" in w]) == 1

    def test_downgrade_from_outline_carries_over(self, mock_factory, mock_parser_factory, mock_prompter, warnings):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser_factory.return_value.invoke.return_value = MagicMock(transcript=[])
        mock_factory.create_language.return_value = _language_model(TRANSCRIPT_OK)
        state = _transcript_state(num_segments=1, json_mode_models=["openai/gpt-4o-mini"])

        result = asyncio.run(generate_transcript_node(state, {"configurable": {}}))

        assert _structured_types(mock_factory) == ["json"]
        assert result["json_mode_models"] == ["openai/gpt-4o-mini"]
        assert warnings == []

    def test_downgrade_is_per_model(self, mock_factory, mock_parser_factory, mock_prompter):
        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser_factory.return_value.invoke.return_value = MagicMock(transcript=[])
        mock_factory.create_language.return_value = _language_model(TRANSCRIPT_OK)
        state = _transcript_state(num_segments=1, json_mode_models=["deepseek/deepseek-chat"])

        asyncio.run(generate_transcript_node(state, {"configurable": {}}))

        assert _structured_types(mock_factory) == ["json_schema"]
