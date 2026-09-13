import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .recognizers import COMPOSE, DOCKER_TIME, ENVELOPES, RECOGNIZERS, Envelope, EnvelopeRecognizer, EventRecognizer
from .safety import EvidenceRedactor, JSONValue, SGR, safe_fields


TIMEZONE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")
LIVE_COLLAPSED_SCOPES = frozenset({"subagent"})


def timezone_fact(timestamp: str | None) -> str | None:
    match = TIMEZONE.search(timestamp) if timestamp else None
    return ("UTC" if match[1] == "Z" else match[1]) if match else ("unspecified" if timestamp else None)


def iso_timestamp(timestamp: str) -> str:
    normalized = timestamp.replace(" - ", "T").replace("/", "-").replace(" ", "T").replace(",", ".")
    return re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    timestamp_origin: str
    source_timestamp: str | None
    source_timezone: str | None
    docker_timestamp: str | None
    observed_at: str
    service: str | None
    logger: str | None
    level: str | None
    scope: str
    kind: str
    message: str
    details: dict[str, JSONValue]
    source_line: str

    @property
    def live_collapsed(self) -> bool:
        return self.scope in LIVE_COLLAPSED_SCOPES

    def json_line(self) -> str:
        return json.dumps({"schema_version": 1, **asdict(self)}, ensure_ascii=True, allow_nan=False) + "\n"


class EventParser:
    def __init__(
        self, *, envelopes: tuple[EnvelopeRecognizer, ...] = ENVELOPES,
        recognizers: tuple[EventRecognizer, ...] = RECOGNIZERS,
    ) -> None:
        self.envelopes = envelopes
        self.recognizers = recognizers
        self.redactor = EvidenceRedactor()

    def parse(self, line: str, *, observed_at: datetime | None = None) -> LogEvent:
        observed = (observed_at or datetime.now(UTC)).isoformat()
        text = SGR.sub("", line).removesuffix("\n").removesuffix("\r")
        compose = COMPOSE.fullmatch(text)
        service, body = (compose["service"], compose["body"]) if compose else (None, text)
        envelope = next((found for recognize in self.envelopes if (found := recognize(body))), None)
        docker = DOCKER_TIME.fullmatch(body) if envelope is None else None
        docker_timestamp = docker["timestamp"] if docker else None
        if docker:
            body = docker["body"]
            envelope = next((found for recognize in self.envelopes if (found := recognize(body))), None)
        envelope = envelope or Envelope(body)
        recognized = next((found for recognize in self.recognizers if (found := recognize(envelope, service))), None)
        details = safe_fields(recognized.details) if recognized else {}
        if recognized and recognized.detail_prefix is not None:
            message = recognized.detail_prefix + json.dumps(details, ensure_ascii=True, allow_nan=False)
        else:
            message = self.redactor.message(envelope.message, service=service)
        source_line = text[:len(text) - len(envelope.message)] + message if envelope.message else text
        timestamp = envelope.source_timestamp or docker_timestamp or observed
        origin = "producer" if envelope.source_timestamp else ("docker" if docker_timestamp else "observed")
        return LogEvent(
            timestamp=iso_timestamp(timestamp), timestamp_origin=origin,
            source_timestamp=envelope.source_timestamp, source_timezone=timezone_fact(envelope.source_timestamp),
            docker_timestamp=docker_timestamp, observed_at=observed,
            service=service, logger=envelope.logger, level=envelope.level,
            scope=recognized.scope if recognized else "service",
            kind=recognized.kind if recognized else "text", message=message,
            details=details, source_line=source_line,
        )
