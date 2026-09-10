import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_tools import HDImageGeneratorTool


@pytest.fixture
def hd_image(monkeypatch):
    config = SimpleNamespace(
        OLLAMA_BASE_URL="https://openrouter.ai/api/v1",
        OLLAMA_API_KEY="synthetic-chat-key",
        OLLAMA_MODEL="synthetic-chat-model",
        OLLAMA_EXTRA_BODY={"provider": {"only": ["synthetic-chat-provider"]}},
        GEMINI_IMAGE_BASE_URL="",
        GEMINI_IMAGE_API_KEY="",
    )
    tool = HDImageGeneratorTool(
        SimpleNamespace(
            config=config,
            memory=SimpleNamespace(add_to_channel_memory=AsyncMock()),
            _current_progress_by_channel={},
        )
    )
    message = SimpleNamespace(
        attachments=[],
        channel=SimpleNamespace(
            id=42,
            send=AsyncMock(return_value=SimpleNamespace(attachments=[])),
        ),
    )
    response = MagicMock(status=200)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    response.text = AsyncMock(
        return_value=json.dumps(
            {"choices": [{"message": {"content": "data:image/png;base64,aW1hZ2U="}}]}
        )
    )
    session = MagicMock()
    session.post.return_value = response
    get_session = AsyncMock(return_value=session)
    monkeypatch.setattr("bot_tools._get_shared_session", get_session)
    monkeypatch.setattr("bot_tools._persist_public_image", MagicMock(return_value=("", "")))
    return tool, message, session, get_session


@pytest.mark.parametrize("base", [None, "", "   ", "/"])
@pytest.mark.parametrize("image", [None, "https://example.invalid/input.png"])
def test_chat_openrouter_settings_cannot_enable_hd_image(hd_image, monkeypatch, base, image):
    tool, message, session, get_session = hd_image
    if base is None:
        del tool.bot.config.GEMINI_IMAGE_BASE_URL
    else:
        tool.bot.config.GEMINI_IMAGE_BASE_URL = base
    message.attachments = [
        SimpleNamespace(
            url="https://example.invalid/attachment.png",
            content_type="image/png",
            filename="attachment.png",
        )
    ]
    load_image = AsyncMock(return_value=(b"image", ""))
    monkeypatch.setattr(tool, "_load_one", load_image)

    result = asyncio.run(tool.execute(message, prompt="a red fox", image=image))

    assert result == (
        "Error: HD image generation is not configured "
        "(set GEMINI_IMAGE_BASE_URL explicitly; chat settings are not used)"
    )
    load_image.assert_not_awaited()
    get_session.assert_not_awaited()
    session.get.assert_not_called()
    session.post.assert_not_called()
    message.channel.send.assert_not_awaited()


@pytest.mark.parametrize("suffix", ["", "/", "/chat/completions"])
@pytest.mark.parametrize("model", ["", "dedicated-image-model"])
def test_hd_image_uses_explicit_endpoint_and_key(hd_image, suffix, model):
    tool, message, session, _ = hd_image
    tool.bot.config.GEMINI_IMAGE_BASE_URL = "https://images.example.invalid/v1" + suffix
    tool.bot.config.GEMINI_IMAGE_API_KEY = "synthetic-image-key"
    tool.bot.config.GEMINI_IMAGE_MODEL = model

    result = asyncio.run(tool.execute(message, prompt="a red fox"))

    assert result.startswith("HD image generated successfully")
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args == ("https://images.example.invalid/v1/chat/completions",)
    assert kwargs["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer synthetic-image-key",
    }
    assert kwargs["json"] == {
        "model": model or "gemini-3.1-flash-image",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "a red fox"}]}],
    }
    message.channel.send.assert_awaited_once()


@pytest.mark.parametrize("key_present", [True, False])
def test_explicit_keyless_image_endpoint_never_borrows_chat_key(hd_image, key_present):
    tool, message, session, _ = hd_image
    tool.bot.config.GEMINI_IMAGE_BASE_URL = "http://127.0.0.1:1234/v1"
    if not key_present:
        del tool.bot.config.GEMINI_IMAGE_API_KEY

    result = asyncio.run(tool.execute(message, prompt="a red fox"))

    assert result.startswith("HD image generated successfully")
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args == ("http://127.0.0.1:1234/v1/chat/completions",)
    assert kwargs["headers"] == {"Content-Type": "application/json"}
    message.channel.send.assert_awaited_once()
