import pytest

from response_observability import suppress_delivered_image_previews


CDN = "https://cdn.discordapp.com/attachments/100/200/generated_image.png"
SIGNED_CDN = CDN + "?ex=abc&is=def&hm=123"
PERMANENT = "https://images.example/generated.png?version=1"
SUCCESS = "Tool image_generator: Image sent to chat: synthetic prompt"


@pytest.mark.parametrize("prefix", [
    SUCCESS,
    "Tool hd_image: HD image generated successfully: synthetic prompt",
    "Tool hd_image: HD image edited successfully: synthetic prompt",
])
def test_successful_image_results_hide_only_delivered_image_links(prefix):
    results = [f"{prefix}\nImage URL: {SIGNED_CDN}\nPermanent URL: {PERMANENT} (never expires)"]
    text = f"Fresh shot: [generated_image.png]({CDN})\nPermanent: {PERMANENT}\nhttps://example.com/article"
    expected = f"Fresh shot: [generated_image.png](<{CDN}>)\nPermanent: <{PERMANENT}>\nhttps://example.com/article"
    assert suppress_delivered_image_previews(text, results) == expected


@pytest.mark.parametrize("text,expected", [
    (CDN, f"<{CDN}>"),
    (SIGNED_CDN, f"<{SIGNED_CDN}>"),
    (CDN + "?ex=new&hm=other", f"<{CDN}?ex=new&hm=other>"),
    (f"[shot]({CDN})", f"[shot](<{CDN}>)"),
    (f'[shot]({CDN} "a title")', f'[shot](<{CDN}> "a title")'),
    (f"({CDN}).", f"(<{CDN}>)."),
    (f"{CDN}, again {CDN}!", f"<{CDN}>, again <{CDN}>!"),
    (f"<{CDN}>", f"<{CDN}>"),
    (f"[shot](<{CDN}>)", f"[shot](<{CDN}>)"),
    (f"`{CDN}`", f"`{CDN}`"),
    (f"```text\n{CDN}\n```", f"```text\n{CDN}\n```"),
])
def test_signed_attachment_matching_preserves_literal_urls_and_is_idempotent(text, expected):
    results = [f"{SUCCESS}\nImage URL: {SIGNED_CDN}"]
    formatted = suppress_delivered_image_previews(text, results)
    assert formatted == expected
    assert suppress_delivered_image_previews(formatted, results) == formatted


@pytest.mark.parametrize("url", [
    CDN + "-other.png",
    CDN + "/other",
    CDN.replace("/200/", "/201/"),
    CDN.replace("cdn.discordapp.com", "cdn.discordapp.com.evil.example"),
    CDN.replace("cdn.discordapp.com", "media.discordapp.net"),
    "https://example.com/redirect?url=" + CDN,
    PERMANENT + "&variant=2",
    PERMANENT.replace("version=1", "version=2"),
    PERMANENT.split("?")[0],
    "https://cdn.discordapp.com/image?id=2",
])
def test_other_urls_and_query_based_resources_remain_untouched(url):
    results = [
        f"{SUCCESS}\nImage URL: {SIGNED_CDN}\nPermanent URL: {PERMANENT}",
        f"{SUCCESS}\nImage URL: https://cdn.discordapp.com/image?id=1",
    ]
    text = f"[other]({url})"
    assert suppress_delivered_image_previews(text, results) == text


@pytest.mark.parametrize("prefix", [
    "Tool image_generator: Error generating image:",
    "Tool hd_image: Error: Cannot send HD image",
    "Tool web_search: Image sent to chat:",
    "Tool send_media: Image sent to chat:",
])
def test_failed_and_other_tool_results_do_not_suppress_previews(prefix):
    results = [f"{prefix}\nImage URL: {SIGNED_CDN}"]
    assert suppress_delivered_image_previews(CDN, results) == CDN
    assert suppress_delivered_image_previews(CDN, []) == CDN


def test_media_discord_attachment_host_supports_queryless_link():
    url = CDN.replace("cdn.discordapp.com", "media.discordapp.net")
    results = [f"{SUCCESS}\nImage URL: {url}?ex=abc&hm=123"]
    assert suppress_delivered_image_previews(url, results) == f"<{url}>"


@pytest.mark.parametrize("text,expected", [
    (f"[generated_image.png]({CDN})", f"[generated_image.png]({CDN})"),
    ("[article](https://example.com/article)", "[article](https://example.com/article)"),
    ("[TOOL_CALL:web_search]answer[/web_search]", "answer"),
    ("[tool]answer[/tool]", "answer"),
    ("[tool foo=bar]answer[/tool]", "answer"),
    (f"[tool][shot]({CDN})[/tool]", f"[shot]({CDN})"),
    (f"[shot]({CDN})[tool]done[/tool]", f"[shot]({CDN})done"),
    (f"[first]({CDN}) [second](https://example.com/page)", f"[first]({CDN}) [second](https://example.com/page)"),
    ('[tool]{"payload": "hidden"}[/tool]answer', "answer"),
])
def test_visible_reply_keeps_inline_link_labels_and_removes_protocol_markers(text, expected):
    from bot import _sanitize_visible_reply

    assert _sanitize_visible_reply(text) == expected
