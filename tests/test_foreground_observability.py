"""Drive the real foreground handler with synthetic transport and context fixtures."""

import asyncio
from contextlib import nullcontext
from dataclasses import replace
import json
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bot import MaxwellBot
from bot_tools import SendMessageTool
from provider_telemetry import CallMetrics
from providers import ProviderResult
from response_observability import DeliveryMeasurements, FOOTER_MARKER, RunningBuild


class Channel:
    id = 100
    guild = SimpleNamespace(id=9)

    def __init__(self):
        self.sent = []

    async def send(self, content=None, **kwargs):
        assert len(content or "") <= 2000
        sent = SimpleNamespace(
            id=1000 + len(self.sent), channel=self, content=content, kwargs=kwargs
        )
        self.sent.append(sent)
        return sent


class Message:
    id = 7
    author = SimpleNamespace(id=7, bot=False, display_name="root")
    content = "hello"
    reference = None

    def __init__(self):
        self.channel = Channel()
        self.guild = self.channel.guild

    async def reply(self, content=None, **kwargs):
        return await self.channel.send(content, **kwargs)


@pytest.fixture
def measured_call():
    return CallMetrics(
        call_id="A",
        provider="provider.example",
        endpoint="primary",
        model="model-A",
        input_tokens=123,
        output_tokens=50,
        reasoning_tokens=10,
        input_source="provider",
        output_source="provider",
        elapsed_ms=2000,
        ttft_ms=125,
        ttft_estimated=False,
        stream=True,
        attempt=1,
        output_bytes=160,
    )


@pytest.fixture
def foreground_bot():
    bot = SimpleNamespace(
        _control={"max_tool_iterations": 3, "footer_format": "{{MODEL}} {{TTFT}}"},
        config=SimpleNamespace(ENABLE_IMAGE_INPUT=False, OLLAMA_MAX_TOKENS=1000),
        bot_name="Maxwell",
        user=SimpleNamespace(id=42),
        tools={},
        memory=SimpleNamespace(),
        _delivery_measurements=DeliveryMeasurements(),
        _replying_channels=set(),
        _active_requests={},
        _active_request_user={},
        _message_snapshots={},
        _message_update_state={},
        _current_progress_by_channel={},
        _last_bot_reply={},
        _token_tracker=SimpleNamespace(record=Mock()),
        _check_sleep_gate=AsyncMock(return_value=True),
        _begin_inflight_context=lambda message, content: {"message_ids": set()},
        _enter_live_typing=AsyncMock(),
        _exit_live_typing=AsyncMock(),
        _directly_addressed=lambda message: False,
        _arm_conversation_watch=Mock(),
        _record_rem_event=AsyncMock(),
        _is_short_live_turn=lambda *args: False,
        _extract_media=AsyncMock(return_value=([], [])),
        _extract_embeds=AsyncMock(return_value=[]),
        _extract_linked_media=AsyncMock(return_value=[]),
        _ensure_reply_chain_resolved=AsyncMock(),
        _iter_resolved_reply_chain=lambda message: [],
        _reply_media_message_id=lambda *args: None,
        _should_use_cached_media_context=lambda *args: False,
        _current_binary_media=lambda media: [],
        _format_media_summary=lambda *args: "",
        _message_carries_media=lambda message: False,
        _cache_media_context=Mock(),
        _message_update_fingerprint=lambda message: (),
        _message_media_fingerprint=lambda message: (),
        _progress_enabled=lambda guild: False,
        _build_messages=AsyncMock(return_value=[{"role": "user", "content": "hello"}]),
        _build_openai_tools=lambda *args, **kwargs: [],
        _select_tool_protocol=lambda tools: (False, []),
        _acquire_ai_slot=AsyncMock(),
        _release_ai_slot=AsyncMock(),
        _ensure_reasoning_trace=AsyncMock(),
        _render_custom_emojis=lambda text, guild: text,
        _extract_stickers_from_text=lambda text, guild: (text, []),
        _reply_typing=lambda *args, **kwargs: nullcontext(),
        _respect_slowmode=AsyncMock(),
        _mark_bot_sent=Mock(),
        add_message_to_memory=AsyncMock(),
        _mark_inbox_announced=AsyncMock(),
        _end_inflight_context=Mock(),
        _tick_media_context=Mock(),
        _flush_deferred_context_extraction=Mock(),
    )

    async def refresh(context, *args):
        return args

    bot._apply_inflight_refresh = refresh
    bot._wait_for_late_embeds = AsyncMock(side_effect=lambda message, content: message)
    for name in (
        "_native_calls_from",
        "_usage_from",
        "_recover_text_tool_calls",
        "_send_with_slowmode",
    ):
        setattr(bot, name, MethodType(getattr(MaxwellBot, name), bot))
    bot._split_response = MaxwellBot._split_response
    return bot


def configure_dispatch(bot):
    tool = SendMessageTool(bot)

    async def dispatch(
        message, response, *, native_tool_calls=None, response_metrics=None, **kwargs
    ):
        results = []
        for call in native_tool_calls or []:
            function = call["function"]
            if function["name"] == "send_message":
                result = await tool.execute(
                    message,
                    _response_metrics=response_metrics,
                    **json.loads(function["arguments"]),
                )
                results.append("Tool send_message: " + result)
            else:
                results.append("Tool web_search: synthetic result")
        return str(response), results, []

    bot._dispatch_tool_calls = AsyncMock(side_effect=dispatch)


def tool_call(name, **arguments):
    return {
        "id": "tool-1",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


@pytest.mark.parametrize("mode", ["plain", "terminal", "followup", "empty_followup"])
def test_real_foreground_handler_preserves_producing_call(
    foreground_bot, measured_call, mode
):
    async def scenario():
        bot, message = foreground_bot, Message()
        first = measured_call
        second = replace(first, call_id="B", model="model-B", ttft_ms=777)
        configure_dispatch(bot)
        if mode == "plain":
            responses = [ProviderResult("plain answer", metrics=first)]
        elif mode == "terminal":
            responses = [
                ProviderResult(
                    "",
                    tool_calls=[tool_call("send_message", content="done")],
                    metrics=first,
                )
            ]
        elif mode == "followup":
            responses = [
                ProviderResult(
                    '{"name":"send_message","arguments":{"content":"checking"}}',
                    metrics=first,
                ),
                ProviderResult("finished answer", metrics=second),
            ]
        else:
            responses = [
                ProviderResult(
                    "partial answer",
                    tool_calls=[tool_call("web_search", query="test")],
                    metrics=first,
                ),
                ProviderResult("", metrics=second),
            ]
        bot._generate_response = AsyncMock(side_effect=responses)
        await MaxwellBot._handle_message(bot, message)
        assert bot._generate_response.await_count == len(responses)
        assert message.channel.sent
        assert all(
            "something broke" not in sent.content for sent in message.channel.sent
        )
        expected = [first, second] if mode == "followup" else [first]
        assert len(message.channel.sent) == len(expected)
        for sent, metrics in zip(message.channel.sent, expected):
            assert sent.content.endswith(FOOTER_MARKER)
            assert metrics.model in sent.content
            assert bot._delivery_measurements.lookup("100", str(sent.id))[1] is metrics
        dispatches = bot._dispatch_tool_calls.call_args_list
        assert dispatches[0].kwargs["response_metrics"] is first
        if mode == "followup":
            assert dispatches[1].kwargs["response_metrics"] is second
        if mode == "empty_followup":
            assert message.channel.sent[0].content.startswith("partial answer")
            assert "model-B" not in message.channel.sent[0].content
        for call in bot.add_message_to_memory.call_args_list:
            assert FOOTER_MARKER not in call.args[1]["content"]
        for call in bot._record_rem_event.call_args_list:
            assert FOOTER_MARKER not in call.args[2]

    asyncio.run(scenario())


def test_sticker_only_send_preserves_empty_clean_chunk_and_registers_once(
    measured_call,
):
    async def scenario():
        bot = SimpleNamespace(
            _control={},
            bot_name="Maxwell",
            _delivery_measurements=DeliveryMeasurements(),
            _extract_stickers_from_text=lambda text, guild: ("", ["sticker"]),
        )
        message = Message()
        tool = SendMessageTool(bot)
        tool._chunks = lambda text, limit: [] if not text else [text]
        result = await tool.execute(
            message, content="sticker:wave", _response_metrics=measured_call
        )
        assert result == "__MESSAGE_SENT__\n"
        assert len(message.channel.sent) == 1
        sent = message.channel.sent[0]
        assert sent.content == ""
        assert sent.kwargs["stickers"] == ["sticker"]
        assert (
            bot._delivery_measurements.lookup("100", str(sent.id))[1] is measured_call
        )
        assert len(bot._delivery_measurements.records) == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("command", ["version", "footer status", "help"])
def test_multichar_prefix_commands_and_help_fit_discord(command):
    async def scenario():
        bot = SimpleNamespace(
            _control={},
            command_prefix="!!",
            _is_admin=lambda uid: True,
            _running_build=RunningBuild(
                "a" * 40, "branch", "date", "subject", False, "start", "3.14"
            ),
        )
        bot._handle_footer_command = MethodType(MaxwellBot._handle_footer_command, bot)
        message = Message()
        message.content = "!!" + command
        await MaxwellBot._handle_command(bot, message)
        assert message.channel.sent
        assert not any(
            "Something went wrong" in sent.content for sent in message.channel.sent
        )
        text = "\n".join(sent.content for sent in message.channel.sent)
        assert {
            "version": "Running build:",
            "footer status": "Footer: on",
            "help": "!!footer",
        }[command] in text
        assert all(len(sent.content) <= 2000 for sent in message.channel.sent)

    asyncio.run(scenario())
