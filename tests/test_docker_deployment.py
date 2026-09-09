from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def deployment():
    return yaml.safe_load((ROOT / "compose.yaml").read_text())


def test_one_bot_and_api_share_whole_private_state():
    services = deployment()["services"]
    for name in ("bot", "api"):
        service = services[name]
        mounts = {item["target"]: item for item in service["volumes"]}
        assert mounts["/state/data"]["source"] == "${INSTANCE_DIR}/data"
        assert mounts["/config"]["read_only"] is True
        assert "read_only" not in mounts["/config/prompts"]
        assert all(not item["bind"]["create_host_path"] for item in mounts.values())
        assert service["environment"]["MAXWELL_ENV_FILE"] == "/config/bot.env"
        assert "env_file" not in service
        assert "ports" not in service
        assert "container_name" not in service
        assert "replicas" not in service.get("deploy", {})


def test_private_socket_and_no_host_privilege():
    for service in deployment()["services"].values():
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert not service.get("privileged")
        assert service.get("network_mode") != "host"
        for mount in service.get("volumes", []):
            assert mount["source"] != "/"
            assert mount["source"] != "/var/run/docker.sock"
    socket_mount = deployment()["services"]["bot"]["volumes"][-1]
    assert socket_mount["source"].startswith("${ENGINE_SOCKET:?")


def test_web_only_mounts_public_sites_and_binds_loopback():
    web = deployment()["services"]["web"]
    assert len(web["volumes"]) == 1
    assert web["volumes"][0]["source"] == "${INSTANCE_DIR}/sites"
    assert web["volumes"][0]["read_only"] is True
    assert web["ports"][0].startswith("127.0.0.1:")
    caddy = (ROOT / "docker/Caddyfile").read_text()
    assert "reverse_proxy api:8765" in caddy
    assert "/bot/*/api /bot/*/api/*" in caddy
    assert "/state/data" not in caddy


def test_image_uses_allowlisted_source_and_locked_dependencies():
    dockerfile = (ROOT / "docker/app.Dockerfile").read_text()
    assert "python:3.14.4-slim-trixie" in dockerfile
    assert "COPY . " not in dockerfile
    assert "COPY *.py" not in dockerfile
    assert "--no-deps -r /opt/maxwell/requirements.lock" in dockerfile
    lines = (ROOT / "docker/app.Dockerfile.dockerignore").read_text().splitlines()
    assert lines[0] == "**"
    allowed = [line[1:] for line in lines if line.startswith("!")]
    assert not any("*" in path for path in allowed)
    assert not any(path.startswith(("data/", ".venv/", "shelldocker/")) for path in allowed)
    assert not any(path.endswith((".env", ".db", ".key", ".pem")) for path in allowed)
    dependencies = (ROOT / "docker/requirements.lock").read_text().splitlines()
    assert all("==" in line and ">" not in line for line in dependencies)
    assert "discord.py-self==2.1.0" in dependencies
    assert not any(line.startswith("discord.py==") for line in dependencies)
    assert "provider_telemetry.py" in dockerfile.split()
    assert "provider_telemetry.py" in allowed
    assert "response_observability.py" in dockerfile.split()
    assert "response_observability.py" in allowed
    assert "COPY assets/tokenizers/ ./assets/tokenizers/" in dockerfile
    assert {
        "assets/tokenizers/cl100k_base.tiktoken",
        "assets/tokenizers/LICENSE",
        "assets/tokenizers/README.md",
    } <= set(allowed)


def test_bot_template_keeps_operational_paths_consistent():
    settings = dict(
        line.split("=", 1)
        for line in (ROOT / "docker/bot.env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert settings["DATA_DIR"] == "/state/data"
    assert settings["MAXWELL_SITE_DIR"] == "/state/sites"
    assert settings["MAXWELL_PROMPTS_DIR"] == "/config/prompts"
    assert settings["MAXWELL_SHELL_FULL_HOST"] == "false"
    assert settings["MAXWELL_API_PORT"] == "8765"
    assert settings["DISCORD_TOKEN"] == ""
    assert settings["OLLAMA_API_KEY"] == ""
    assert settings["MAXWELL_ADMIN_PASSWORD"] == ""
