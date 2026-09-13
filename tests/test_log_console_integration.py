import io
import json
import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import error_reporting
from scripts import instance, log_filter
from scripts.log_console import jsonl


def test_jsonl_cli_follows_logs_without_lock_or_container_mutation(monkeypatch):
    app = instance.Instance.__new__(instance.Instance)
    app.project = "maxwell-fixture"
    app.env = {"DOCKER_HOST": "unix:///synthetic/docker.sock"}
    app.inventory = Mock(return_value=[])
    app.docker = Mock(side_effect=AssertionError("no lifecycle operation"))
    account = object()
    follower = Mock()
    monkeypatch.setattr(instance, "service_account", Mock(return_value=account))
    monkeypatch.setattr(instance, "Instance", Mock(return_value=app))
    monkeypatch.setattr(instance.sys, "argv", ["instance.py", "fixture", "logs", "--format", "jsonl"])
    monkeypatch.setattr(instance.os, "open", Mock(side_effect=AssertionError("logs do not acquire operation lock")))
    monkeypatch.setattr(log_filter, "follow_logs", follower)
    instance.main()
    app.inventory.assert_called_once_with()
    app.docker.assert_not_called()
    command, env = follower.call_args.args
    assert command[-4:] == ["logs", "--follow", "--tail", "100"]
    assert env is app.env
    assert follower.call_args.kwargs == {"output_format": "jsonl"}


@pytest.mark.parametrize("action", ["up", "start", "stop", "restart", "down", "backup", "restore"])
def test_format_option_is_rejected_before_any_identity_access(monkeypatch, capsys, action):
    account = Mock(side_effect=AssertionError("no identity lookup"))
    monkeypatch.setattr(instance, "service_account", account)
    monkeypatch.setattr(instance.sys, "argv", ["instance.py", "fixture", action, "--format", "jsonl"])
    with pytest.raises(SystemExit) as error:
        instance.main()
    assert error.value.code == 2
    assert "--format is only available for logs" in capsys.readouterr().err
    account.assert_not_called()


@pytest.mark.parametrize("interrupted", [False, True])
def test_jsonl_follower_uses_same_child_only_interrupt_cleanup(monkeypatch, interrupted):
    process = Mock(pid=12345, stdout=io.StringIO("bot-1 | synthetic\n"))
    process.__enter__ = Mock(return_value=process)
    process.__exit__ = Mock(return_value=False)
    process.wait.return_value = 0
    popen = Mock(return_value=process)
    killpg = Mock()
    stream = Mock(side_effect=KeyboardInterrupt if interrupted else None)
    monkeypatch.setattr(log_filter.subprocess, "Popen", popen)
    monkeypatch.setattr(log_filter.os, "killpg", killpg)
    monkeypatch.setattr(jsonl, "write_jsonl", stream)
    monkeypatch.setattr(log_filter, "coalesce_logs", Mock(side_effect=AssertionError("JSONL must not coalesce")))
    command, env = ["docker", "compose", "logs", "--follow"], {"DOCKER_HOST": "synthetic"}
    old_path = sys.path.copy()
    log_filter.follow_logs(command, env, output_format="jsonl")
    assert sys.path == old_path
    popen.assert_called_once_with(command, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                  errors="surrogateescape", start_new_session=True)
    stream.assert_called_once_with(process.stdout, sys.stdout)
    assert killpg.call_args_list == [call(12345, signal.SIGTERM), call(12345, signal.SIGKILL)]
    assert process.wait.call_args_list[-2:] == [call(timeout=5), call()]


def test_script_mode_jsonl_needs_only_stdlib_and_inert_redactor(tmp_path):
    scripts = tmp_path / "scripts"
    package = scripts / "log_console"
    package.mkdir(parents=True)
    (scripts / "log_filter.py").write_bytes(Path(log_filter.__file__).read_bytes())
    for source in Path(jsonl.__file__).parent.glob("*.py"):
        (package / source.name).write_bytes(source.read_bytes())
    (tmp_path / "error_reporting.py").write_bytes(Path(error_reporting.__file__).read_bytes())
    (tmp_path / "config.py").write_text('raise AssertionError("configuration must not be imported")\n')
    program = (
        "import sys; sys.path.insert(0, sys.argv[1]); import log_filter; "
        "log_filter.follow_logs([sys.executable, '-c', \"print('bot-1 | synthetic recovery fixture')\"], "
        "{}, output_format='jsonl')"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-E", "-s", "-c", program, str(scripts)],
        cwd=tmp_path, env={"HOME": str(tmp_path), "PATH": "/usr/local/bin:/usr/bin:/bin"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    record = json.loads(result.stdout)
    assert record["message"] == "synthetic recovery fixture" and record["timestamp_origin"] == "observed"
