import asyncio
import copy
import json
import logging
from unittest.mock import AsyncMock

import aiohttp
import pytest

import error_reporting
import providers
from providers import (
    OllamaProvider,
    ProviderEmptyResponseError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderUpstreamError,
    ProviderUsageExhaustedError,
)


class Response:
    def __init__(self, body=b"", status=200, *, chunks=None, headers=None, error=None):
        self.raw_body = body
        self.status = status
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.chunks = chunks if chunks is not None else [body]
        self.content = self
        self.error = error
        self.read_chunks = 0
        self.json_calls = 0
        self.text_calls = 0
        self._body = None

    async def __aenter__(self):
        if self.error is not None:
            raise self.error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get_encoding(self):
        return self.headers["Content-Type"].split("charset=")[-1] if "charset=" in self.headers["Content-Type"] else "utf-8"

    async def json(self, *, content_type=None):
        assert content_type is None
        self.json_calls += 1
        self._body = self.raw_body
        return json.loads(self.raw_body.decode(self.get_encoding()))

    async def text(self):
        self.text_calls += 1
        self._body = self.raw_body
        return self.raw_body.decode("utf-8")

    async def iter_any(self):
        for chunk in self.chunks:
            self.read_chunks += 1
            yield chunk


class Session:
    closed = False

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, *, json, timeout, headers):
        self.requests.append((url, copy.deepcopy(json), timeout, dict(headers)))
        return self.responses.pop(0)

    def get(self, url, *, timeout, headers):
        self.requests.append((url, {}, timeout, dict(headers)))
        return self.responses.pop(0)


def provider_for(responses, **kwargs):
    provider = OllamaProvider(
        "https://primary.example.test/v1", "synthetic-model", 8192, 0.6, **kwargs
    )
    provider.available = True
    provider._session = Session(responses)
    return provider


def success():
    return Response(b'{"choices":[{"message":{"role":"assistant","content":"ok"}}]}')


@pytest.fixture(autouse=True)
def incident_state(monkeypatch):
    monkeypatch.setattr(error_reporting, "_store", None)
    monkeypatch.setattr(error_reporting, "_secrets", ())


@pytest.fixture
def private_store(tmp_path):
    return error_reporting.configure_incident_store(tmp_path / "incidents.json")


@pytest.fixture
def production_handler(private_store):
    handler = error_reporting.IncidentLoggingHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        yield private_store
    finally:
        root_logger.removeHandler(handler)
        handler.close()


@pytest.fixture
def captured(monkeypatch):
    reports = []

    def capture(source, summary, *, exception=None, details="", context=None):
        reports.append({
            "source": source, "summary": summary, "exception": exception,
            "details": details, "context": context,
        })
        return f"synthetic-incident-{len(reports)}"

    monkeypatch.setattr(providers, "capture_incident", capture)
    return reports


@pytest.fixture(autouse=True)
def retry_sleep(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(providers.asyncio, "sleep", sleep)
    return sleep


MESSAGES = [{"role": "user", "content": "synthetic private prompt not needed in diagnostics"}]


def test_full_http400_body_is_private_with_exact_request_metadata(captured, caplog):
    body = "reason=" + "x" * 300 + "; missing reasoning_content in assistant continuation; END405"
    response = Response(body.encode(), 400, headers={
        "X-Request-ID": "synthetic-request-400", "CF-Ray": "synthetic-ray",
        "Retry-After": "7", "Set-Cookie": "synthetic-response-cookie",
    })
    provider = provider_for(
        [response], retry_attempts=4, api_key="synthetic-provider-key",
        extra_headers={"Cookie": "synthetic-request-cookie"},
        extra_body={"provider": {"only": ["synthetic-upstream"]}, "reasoning": {"effort": "high"}},
    )
    tools = [{"type": "function", "function": {"name": "synthetic_tool", "parameters": {"type": "object"}}}]
    with pytest.raises(ProviderRequestError) as caught:
        asyncio.run(provider.generate_chat_completion(MESSAGES, tools=tools, model="override-model"))
    error = caught.value
    assert str(error) == "Provider API error: 400"
    assert body not in str(error) + repr(error) + caplog.text
    assert body in error.incident_details
    assert error.incident_id == "synthetic-incident-1"
    assert len(captured) == len(provider._session.requests) == 1
    report = captured[0]
    assert report["exception"] is error
    details = report["details"]
    for expected in (
        '"status": 400', '"attempt": "1/4"', '"model": "override-model"',
        '"max_tokens": 8192', '"temperature": 0.6', '"effort": "high"',
        "synthetic-upstream", "synthetic_tool", "synthetic-request-400", "synthetic-ray",
        "https://primary.example.test/v1/chat/completions", "ProviderRequestError",
    ):
        assert expected in details
    for excluded in (
        "Authorization", "Cookie", "synthetic-provider-key", "synthetic-request-cookie",
        "synthetic-response-cookie", MESSAGES[0]["content"],
    ):
        assert excluded not in details
    assert provider._session.requests[0][3]["Authorization"] == "Bearer synthetic-provider-key"
    assert response.text_calls == 1


@pytest.mark.parametrize("status", [500, 502, 503, 504, 429])
def test_retried_http_failures_recover_in_one_incident(status, captured, retry_sleep):
    first = "first upstream explanation " + "a" * 400
    second = "second upstream explanation " + "b" * 400
    provider = provider_for([
        Response(first.encode(), status), Response(second.encode(), status), success(),
    ], retry_attempts=3)
    result = asyncio.run(provider.generate_response(MESSAGES))
    assert result == "ok"
    assert len(provider._session.requests) == 3
    assert [call.args[0] for call in retry_sleep.await_args_list] == [10, 20]
    assert len(captured) == 1
    assert captured[0]["exception"] is None
    assert "recovered" in captured[0]["summary"]
    assert first in captured[0]["details"] and second in captured[0]["details"]
    assert '"attempt": "3/3"' in captured[0]["details"]
    assert '"content":"ok"' not in captured[0]["details"]


def test_invalid_encoding_http_error_keeps_cached_bytes_and_existing_decode_failure(captured):
    body = b"upstream non-UTF8 explanation: \xff" + b"x" * 405
    response = Response(body, 400)
    provider = provider_for([response], retry_attempts=1)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)
    assert body.decode("utf-8", errors="replace") in caught.value.incident_details
    assert '"status": 400' in caught.value.incident_details
    assert response.text_calls == 1
    assert len(captured) == len(provider._session.requests) == 1


def test_terminal_transient_failures_preserve_budget_and_exception(captured, retry_sleep):
    provider = provider_for([
        Response(b"first server explanation", 503), Response(b"last server explanation", 503),
    ], retry_attempts=2)
    with pytest.raises(RuntimeError, match="transient HTTP 503 failure after retries") as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert len(provider._session.requests) == 2
    assert [call.args[0] for call in retry_sleep.await_args_list] == [10]
    assert len(captured) == 1
    assert captured[0]["exception"] is caught.value
    assert "first server explanation" in caught.value.incident_details
    assert "last server explanation" in caught.value.incident_details


def test_http400_fallback_retains_both_endpoint_attempts(captured, retry_sleep):
    provider = provider_for(
        [Response(b"primary rejection " + b"a" * 405, 400), success()],
        retry_attempts=5, fallback_base_url="https://fallback.example.test/v1",
        fallback_model="fallback-model", fallback_api_key="synthetic-fallback-key",
    )
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert [request[1]["model"] for request in provider._session.requests] == ["synthetic-model", "fallback-model"]
    retry_sleep.assert_not_awaited()
    assert len(captured) == 1
    assert "primary rejection " + "a" * 405 in captured[0]["details"]
    assert "https://fallback.example.test/v1/chat/completions" in captured[0]["details"]


@pytest.mark.parametrize("rejection, field", [
    ("stream_options is an unsupported parameter", "stream_options"),
    ("tools are not supported", "tools"),
])
def test_payload_corrections_keep_attempt_budget_and_parameters(rejection, field, captured, retry_sleep):
    provider = provider_for([Response(rejection.encode(), 400), success()], retry_attempts=2)
    tools = [{"type": "function", "function": {"name": "synthetic_tool"}}]
    assert asyncio.run(provider.generate_response(MESSAGES, tools=tools)) == "ok"
    assert len(provider._session.requests) == 2
    assert field in provider._session.requests[0][1]
    assert field not in provider._session.requests[1][1]
    retry_sleep.assert_not_awaited()
    assert len(captured) == 1
    assert rejection in captured[0]["details"]


def test_quota_body_not_echoed_and_no_retry_added(captured, caplog, retry_sleep):
    body = "insufficient_quota: private balance explanation " + "q" * 405
    provider = provider_for([Response(body.encode(), 429)], retry_attempts=5)
    with pytest.raises(ProviderUsageExhaustedError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert len(provider._session.requests) == len(captured) == 1
    assert body in caught.value.incident_details
    assert "private balance" not in str(caught.value) + repr(caught.value) + caplog.text
    retry_sleep.assert_not_awaited()


@pytest.mark.parametrize("response_format", ["json", "sse"])
def test_http200_error_preserves_full_body_and_same_error(captured, caplog, response_format):
    explanation = "invalid tool input " + "x" * 405 + " complete private suffix"
    payload = {"error": {"code": 400, "message": explanation, "metadata": {"raw": "useful upstream detail"}}}
    raw_json = json.dumps(payload, indent=2).encode()
    if response_format == "json":
        body = b" \n" + raw_json + b"\n "
        response = Response(body)
    else:
        prefix = b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        body = prefix + b"event: error\ndata: " + json.dumps(payload).encode() + b"\n\n"
        response = Response(chunks=[body, b"unread trailing transport data"], headers={"Content-Type": "text/event-stream"})
    provider = provider_for([response], retry_attempts=1)
    with pytest.raises(ProviderUpstreamError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert len(captured) == len(provider._session.requests) == 1
    assert body.decode() in caught.value.incident_details
    assert explanation not in str(caught.value) + repr(caught.value) + caplog.text
    assert "useful upstream detail" in captured[0]["details"]
    assert captured[0]["exception"] is caught.value
    assert "unread trailing transport data" not in captured[0]["details"]
    if response_format == "sse":
        assert response.read_chunks == 1
    else:
        assert response.json_calls == 1 and response.text_calls == 0


def test_http200_json_diagnostics_preserve_declared_text_encoding(captured):
    body = '{"error":{"message":"upstream explanation Ωé"}}'
    response = Response(body.encode("utf-16"), headers={"Content-Type": "application/json; charset=utf-16"})
    provider = provider_for([response], retry_attempts=1)
    with pytest.raises(ProviderUpstreamError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert body in caught.value.incident_details
    assert len(captured) == 1


def test_upstream_exception_keeps_private_details_without_public_body():
    explanation = {"message": "private upstream explanation " + "x" * 405, "metadata": {"raw": "tail"}}
    error = ProviderUpstreamError(explanation)
    assert json.loads(error.incident_details) == explanation
    assert "private upstream explanation" not in str(error) + repr(error)


@pytest.mark.parametrize("body, error_name", [
    (b"{malformed private JSON body " + b"x" * 405, "JSONDecodeError"),
    (b'{"invalid":"\xff"}', "UnicodeDecodeError"),
])
def test_malformed_json_preserves_body_and_underlying_decode_trace(body, error_name, captured, caplog):
    provider = provider_for([Response(body)], retry_attempts=1)
    with pytest.raises(ProviderResponseError, match="JSON decoding failed") as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert body.decode("utf-8", errors="replace") in caught.value.incident_details
    assert error_name in caught.value.incident_details
    assert "Traceback (most recent call last)" in caught.value.incident_details
    assert "private JSON" not in str(caught.value) + caplog.text
    assert len(captured) == 1


@pytest.mark.parametrize("body", [b"null", b'["private nonobject body"]', b'{"unexpected":"private shape"}'])
def test_http200_wrong_shape_is_captured_before_existing_retry(body, captured, retry_sleep):
    provider = provider_for([Response(body), success()], retry_attempts=2)
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert body.decode() in captured[0]["details"]
    assert len(captured) == 1
    assert len(provider._session.requests) == 2
    assert [call.args[0] for call in retry_sleep.await_args_list] == [10]


@pytest.mark.parametrize("tail", [b"data: {malformed private frame}\n\n", b"data: unterminated private tail"])
def test_malformed_sse_body_is_preserved_without_new_retries(tail, captured):
    provider = provider_for([
        Response(chunks=[tail], headers={"Content-Type": "text/event-stream"}),
    ], retry_attempts=1)
    with pytest.raises(ProviderResponseError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert tail.decode() in caught.value.incident_details
    assert "private" not in str(caught.value)
    assert len(captured) == len(provider._session.requests) == 1


def test_skipped_bad_sse_frame_records_recovered_incident_not_fabricated_error(captured):
    body = (
        b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'
        b'data: {malformed private frame}\n\n'
        b'data: [DONE]\n\n'
    )
    provider = provider_for([Response(chunks=[body], headers={"Content-Type": "text/event-stream"})])
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert len(captured) == len(provider._session.requests) == 1
    assert isinstance(captured[0]["exception"], json.JSONDecodeError)
    assert body.decode() in captured[0]["details"]
    assert "JSONDecodeError" in captured[0]["details"]


@pytest.mark.parametrize("error", [TimeoutError("private timeout detail"), aiohttp.ClientConnectionError("private network detail")])
def test_transport_failure_preserves_real_exception_trace_and_safe_wrapper(error, captured, caplog, retry_sleep):
    error.__cause__ = OSError("underlying synthetic OS detail")
    provider = provider_for([Response(error=error)], retry_attempts=1)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(provider.generate_response(MESSAGES, timeout=17))
    assert caught.value.__cause__ is error
    assert str(error) in caught.value.incident_details
    assert "underlying synthetic OS detail" in caught.value.incident_details
    assert "__aenter__" in caught.value.incident_details
    assert "Traceback (most recent call last)" in caught.value.incident_details
    assert "private" not in str(caught.value) + repr(caught.value) + caplog.text
    assert len(captured) == len(provider._session.requests) == 1
    assert captured[0]["exception"] is caught.value
    retry_sleep.assert_not_awaited()


def test_timeout_then_network_recovery_keeps_all_traces_and_backoff(captured, retry_sleep):
    provider = provider_for([
        Response(error=TimeoutError("original timeout detail")),
        Response(error=aiohttp.ClientConnectionError("original network detail")),
        success(),
    ], retry_attempts=3)
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert [call.args[0] for call in retry_sleep.await_args_list] == [10, 20]
    assert len(captured) == 1
    assert "original timeout detail" in captured[0]["details"]
    assert "original network detail" in captured[0]["details"]


def test_empty_response_recovery_keeps_original_shape_and_nonstream_switch(captured, retry_sleep):
    body = b'{"choices":[{"message":{"content":"","reasoning_content":"private scratchpad"}}]}'
    provider = provider_for([Response(body), success()], retry_attempts=2, empty_response_retries=1)
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert len(captured) == 1
    assert body.decode() in captured[0]["details"]
    assert [request[1]["stream"] for request in provider._session.requests] == [True, False]
    assert [call.args[0] for call in retry_sleep.await_args_list] == [10]


def test_terminal_empty_response_uses_original_typed_error(captured):
    provider = provider_for([Response(b'{"choices":[{"message":{"content":""}}]}')], retry_attempts=1)
    with pytest.raises(ProviderEmptyResponseError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert captured[0]["exception"] is caught.value
    assert "Empty response from provider" == str(caught.value)


def test_healthy_json_and_sse_never_capture_incidents(captured):
    stream = Response(
        chunks=[b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n'],
        headers={"Content-Type": "text/event-stream"},
    )
    provider = provider_for([success(), stream])
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert len(provider._session.requests) == 2
    assert captured == []


def test_provider_registers_all_configured_keys_without_capturing_request_headers(monkeypatch, captured):
    registered = []
    monkeypatch.setattr(providers, "register_secrets", lambda values: registered.extend(values))
    provider_for(
        [], api_key=" synthetic-primary-key ", fallback_api_key=" synthetic-fallback-key ",
        vision_api_key=" synthetic-vision-key ",
    )
    assert registered == ["synthetic-primary-key", "synthetic-fallback-key", "synthetic-vision-key"]
    assert captured == []


def test_concurrent_calls_on_shared_provider_keep_diagnostics_separate(captured):
    async def run():
        first_started = asyncio.Event()
        second_started = asyncio.Event()

        class FirstResponse(Response):
            async def __aenter__(self):
                first_started.set()
                await second_started.wait()
                return self

        class SecondResponse(Response):
            async def __aenter__(self):
                await first_started.wait()
                second_started.set()
                return self

        provider = provider_for([
            FirstResponse(b"request-A private body", 400, headers={"X-Request-ID": "request-A-id"}),
            SecondResponse(b"request-B private body", 400, headers={"X-Request-ID": "request-B-id"}),
        ], retry_attempts=1)
        return await asyncio.gather(
            provider.generate_response(MESSAGES, model="request-A-model"),
            provider.generate_response(MESSAGES, model="request-B-model"),
            return_exceptions=True,
        )

    results = asyncio.run(run())
    assert len(captured) == 2
    assert len({result.incident_id for result in results}) == 2
    for own, other, error in [("A", "B", results[0]), ("B", "A", results[1])]:
        assert isinstance(error, ProviderRequestError)
        assert f"request-{own} private body" in error.incident_details
        assert f"request-{own}-model" in error.incident_details
        assert f"request-{own}-id" in error.incident_details
        assert f"request-{other}" not in error.incident_details


def test_real_store_redacts_registered_key_and_common_credentials(private_store, caplog):
    key = "synthetic-private-provider-credential-12345"
    body = (
        f"upstream echoed {key}\nAuthorization: Bearer other-header-secret\n"
        "Cookie: private-session-cookie\n"
        "-----BEGIN PRIVATE KEY-----\nsynthetic-private-key-material\n-----END PRIVATE KEY-----\n"
        + "full useful explanation " + "x" * 405 + " EXACT FINAL UPSTREAM DETAIL"
    )
    provider = provider_for([Response(body.encode(), 400)], api_key=key, retry_attempts=1)
    with pytest.raises(ProviderRequestError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    incident = private_store.get(0)
    assert incident.incident_id == caught.value.incident_id
    assert private_store.get(1) is None
    report = incident.format_report()
    persisted = private_store.path.read_text()
    for secret in (key, "other-header-secret", "private-session-cookie", "synthetic-private-key-material"):
        assert secret not in report + persisted + str(caught.value) + repr(caught.value) + caplog.text
    assert "[REDACTED]" in report
    assert "x" * 405 + " EXACT FINAL UPSTREAM DETAIL" in report
    assert body in caught.value.incident_details


def test_outer_capture_enriches_same_exception_without_duplicate_store_entry(private_store):
    provider = provider_for([Response(b"complete upstream rejection " + b"x" * 405, 400)], retry_attempts=1)
    with pytest.raises(ProviderRequestError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    error = caught.value
    first = private_store.get(0)
    assert error.incident_id == first.incident_id
    assert error_reporting.capture_incident("bot", "outer command failure", exception=error) == first.incident_id
    enriched = private_store.get(0)
    assert private_store.get(1) is None
    assert "outer command failure" in enriched.details
    assert "test_outer_capture_enriches_same_exception_without_duplicate_store_entry" in enriched.traceback
    assert "complete upstream rejection " + "x" * 405 in enriched.details


def test_recovered_incident_is_redacted_and_not_coalesced_with_next_request(private_store):
    key = "synthetic-private-recovery-key-12345"
    provider = provider_for([
        Response(f"first failed request echoed {key}".encode(), 503), success(),
        Response(b"second unrelated request", 400),
    ], api_key=key, retry_attempts=2)
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    first = private_store.get(0)
    assert key not in first.format_report()
    with pytest.raises(ProviderRequestError):
        asyncio.run(provider.generate_response(MESSAGES))
    assert private_store.get(0).incident_id != first.incident_id
    assert private_store.get(1).incident_id == first.incident_id
    assert private_store.get(2) is None
    assert "first failed request" not in private_store.get(0).details


def test_midstream_network_error_retains_received_body_and_trace(captured):
    partial = b'data: {"choices":[{"delta":{"content":"partial private content"}}]}\n\n'

    class BrokenStream(Response):
        async def iter_any(self):
            yield partial
            raise aiohttp.ClientPayloadError("synthetic stream connection reset")

    provider = provider_for([BrokenStream(headers={"Content-Type": "text/event-stream"})], retry_attempts=1)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert partial.decode() in caught.value.incident_details
    assert "synthetic stream connection reset" in caught.value.incident_details
    assert "ClientPayloadError" in caught.value.incident_details
    assert "partial private content" not in str(caught.value)
    assert len(captured) == len(provider._session.requests) == 1


def test_unconfigured_capture_still_retains_private_exception_details():
    body = b"unconfigured private upstream body " + b"x" * 405
    provider = provider_for([Response(body, 400)], retry_attempts=1)
    with pytest.raises(ProviderRequestError) as caught:
        asyncio.run(provider.generate_response(MESSAGES))
    assert body.decode() in caught.value.incident_details
    assert not hasattr(caught.value, "incident_id")
    assert error_reporting.get_incident_store() is None


@pytest.mark.parametrize("error_type", [TimeoutError, aiohttp.ClientConnectionError])
@pytest.mark.parametrize("recovered", [True, False])
def test_production_warning_handler_groups_retries_and_terminal_wrapper(error_type, recovered, production_handler):
    errors = [error_type("first private transport cause"), error_type("second private transport cause")]
    responses = [Response(error=error) for error in errors]
    if recovered:
        responses.append(success())
    provider = provider_for(responses, retry_attempts=len(responses))
    if recovered:
        assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    else:
        with pytest.raises(RuntimeError) as caught:
            asyncio.run(provider.generate_response(MESSAGES))
        assert caught.value.__cause__ is errors[-1]
        logging.getLogger("synthetic.outer").error(
            "Outer provider handler", exc_info=(type(caught.value), caught.value, caught.value.__traceback__),
        )
        assert caught.value.incident_id == errors[0].incident_id
    store = production_handler
    incident = store.get(0)
    assert store.get(1) is None
    assert incident.incident_id == errors[0].incident_id == errors[1].incident_id
    assert "first private transport cause" in incident.format_report()
    assert "second private transport cause" in incident.format_report()
    assert "https://primary.example.test/v1/chat/completions" in incident.details
    assert len(provider._session.requests) == len(responses)


def test_production_handler_honors_existing_exception_incident(production_handler):
    error = aiohttp.ClientConnectionError("already captured underlying transport")
    previous_id = error_reporting.capture_incident("transport", "lower level failure", exception=error)
    provider = provider_for([Response(error=error), success()], retry_attempts=2)
    assert asyncio.run(provider.generate_response(MESSAGES)) == "ok"
    assert production_handler.get(0).incident_id == previous_id
    assert production_handler.get(1) is None
    assert "recovered" in production_handler.get(0).details


def test_production_handler_keeps_concurrent_retry_groups_separate(production_handler):
    async def run():
        first_started = asyncio.Event()
        second_started = asyncio.Event()

        class PausedFailure(Response):
            async def __aenter__(self):
                first_started.set()
                await second_started.wait()
                raise self.error

        class SecondFailure(Response):
            async def __aenter__(self):
                await first_started.wait()
                second_started.set()
                raise self.error

        first = provider_for([
            PausedFailure(error=TimeoutError("request A first failure")),
            Response(error=TimeoutError("request A second failure")), success(),
        ], retry_attempts=3)
        second = provider_for([
            SecondFailure(error=aiohttp.ClientConnectionError("request B first failure")), success(),
        ], retry_attempts=2)
        return await asyncio.gather(first.generate_response(MESSAGES), second.generate_response(MESSAGES))

    assert asyncio.run(run()) == ["ok", "ok"]
    records = [production_handler.get(index) for index in range(2)]
    assert all(records)
    assert records[0].incident_id != records[1].incident_id
    assert production_handler.get(2) is None
    first = next(record for record in records if "request A first failure" in record.format_report())
    second = next(record for record in records if "request B first failure" in record.format_report())
    assert "request A second failure" in first.format_report()
    assert "request B" not in first.format_report()
    assert "request A" not in second.format_report()


def test_failed_models_probe_captures_body_without_new_requests(captured):
    body = b"synthetic initialization rejection " + b"x" * 405
    provider = provider_for([Response(body, 401)])
    assert asyncio.run(provider.initialize()) is False
    assert len(captured) == len(provider._session.requests) == 1
    assert body.decode() in captured[0]["details"]
    assert "https://primary.example.test/v1/models" in captured[0]["details"]
