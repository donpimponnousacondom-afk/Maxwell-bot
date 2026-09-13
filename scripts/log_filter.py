import os
import re
import signal
import subprocess
import sys
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import TextIO

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
HEALTH = re.compile(
    r'^(?P<service>(?:[\w.-]+[-_])?ollama(?:[-_]\d+)?)\s+\|\s*'
    r'\[GIN\]\s+\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2}\s*'
    r'\|\s*200\s*\|[^|\r\n]+\|\s*(?P<origin>127\.0\.0\.1|::1)\s*'
    r'\|\s*(?P<request>HEAD\s+"/"|POST\s+"/api/show")\s*$'
)
WINDOW = 30.0


@dataclass
class Repeats:
    started: float
    latest: str
    count: int = 0

    def summary(self, now: float) -> str:
        elapsed = min(now - self.started, WINDOW)
        return (self.latest.rstrip("\r\n")
                + f" [{self.count} additional repeats in {elapsed:g}s; latest occurrence shown]\n")


def coalesce_logs(lines: Iterable[str], output: TextIO, *, clock: Callable[[], float] = monotonic) -> None:
    pending: dict[tuple[str, str, str], Repeats] = {}
    try:
        for line in lines:
            now = clock()
            match = HEALTH.fullmatch(ANSI.sub("", line).rstrip("\r\n"))
            key = (match["service"], match["origin"], match["request"].split()[0]) if match else None
            batch = pending.get(key) if key is not None else None
            repeated = False
            if batch is not None and now - batch.started <= WINDOW:
                repeated = True
                batch.latest = line
                batch.count += 1
            for old_key, old_batch in list(pending.items()):
                if now - old_batch.started >= WINDOW:
                    if old_batch.count:
                        output.write(old_batch.summary(now))
                    del pending[old_key]
            if not repeated:
                output.write(line)
                if key is not None:
                    pending[key] = Repeats(now, line)
            output.flush()
    finally:
        now = clock()
        for batch in pending.values():
            if batch.count:
                output.write(batch.summary(now))
        output.flush()


def follow_logs(command: list[str], env: dict[str, str], *, output_format: str = "plain") -> None:
    stream: Callable[[Iterable[str], TextIO], None] = coalesce_logs
    if output_format == "jsonl":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        try:
            from scripts.log_console.jsonl import write_jsonl
        finally:
            sys.path.pop(0)
        stream = write_jsonl
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="surrogateescape", start_new_session=True) as process:
        try:
            stream(process.stdout, sys.stdout)
            returncode = process.wait()
        except KeyboardInterrupt:
            returncode = 0
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    if returncode:
        raise RuntimeError("Compose command failed")
