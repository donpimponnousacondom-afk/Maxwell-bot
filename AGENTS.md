# Agent Guide

## Scope and identity

This repository is `dame_curie`, a Maxwell side project. Keep existing Maxwell names in paths, classes, environment variables, APIs, and upstream-facing code unless root explicitly requests a rename.

The root `AGENTS.md` applies to the whole checkout.

## Operating rules

- Preserve root's work. Inspect `git status`, the current branch, and recent commits before changing anything.
- Never read, print, commit, or paste `.env`, Discord tokens, provider keys, cookies, `data/`, PM2 dumps, or generated credentials.
- Do not treat old audit documents as current architecture. Verify claims against source and tests.
- Make targeted changes. Do not mix cleanup, refactors, generated sites, and bug fixes in one patch.
- The repository targets Python 3.11 in `pyproject.toml`; the current checkout and venv use Python 3.13.5. Keep upstream-facing code compatible with the declared project target unless root changes it.
- Run the narrow relevant tests first, then the full suite before declaring a subsystem finished.
- Do not contact live model, embedding, Discord, email, X, or CAPTCHA endpoints unless the task requires it. `doctor.py --probe` performs network requests; plain `doctor.py` does not probe model endpoints.

## Commit discipline — repository-wide instruction

**Commit often.** Every coherent, verified slice should become its own commit rather than accumulating a giant mixed diff.

For every commit:

1. Inspect the complete staged diff and confirm no secrets/runtime data are included.
2. Use a specific subject naming the subsystem and intent.
3. Put a detailed changelog in the commit body: behavior changed, files/subsystems touched, tests run, result, and known remaining work.
4. Update the working-state/changelog section in this file when the project state, active risk, or next step changes materially.
5. Keep unrelated generated HTML/site output out of runtime fixes.

Do not amend, squash, rebase, or rewrite another agent's or root's commits without explicit approval. Do not create a fake empty commit merely to satisfy cadence.

## Current Git baseline

State recorded on 2026-09-06 before this guide's documentation commit:

- Branch: `dev/dame_curie`
- Baseline HEAD: `125aa9ed3d25363914fbce1c84c1a3668ac6d7df` (`Initial dev commit`)
- Baseline worktree/index: clean
- Relation to the locally stored `origin/main`: one commit ahead, zero behind; merge-base `d2ef19a486fbf0740ad1acb94688876044420787`
- The branch has no configured upstream. Fetch before claiming it is current with upstream and configure the upstream on first push.
- The baseline commit spans 30 files and roughly `+1334/-205`: bot/autonomy/provider/config/tooling/tests/docs plus `axon-bodycam/index.html` and `hello-world/index.html`.
- Before preparing an upstream PR, review whether the standalone HTML assets belong with runtime changes and split future work by subsystem.

### Baseline commit audit

The initial branch commit is not ready to send upstream as one PR. Its actual directions and unresolved edges are:

- Identity/persona: deploy Dame Curie/.normal.man while retaining Maxwell code/upstream names. One `bot.py` fallback still restores the old Maxwell account ID, default voice wake words still contain only `maxwell`, and several prompt/transcript labels bypass configurable `BOT_NAME`.
- Invite text: the new Discord invite literal is joined directly to the following em dash without whitespace, likely breaking autolinking/copying.
- Provider policy: primary reasoning now defaults on, temperature is 0.6, and top-p/top-k are forwarded. `top_k` is sent unconditionally although strict OpenAI Chat Completions endpoints may reject it. OpenRouter-specific reasoning handling uses exact hostname detection, so proxies may receive the wrong payload shape.
- Cost/latency: enabling reasoning by default is a behavioral and budget change. Verify against every configured primary/fallback/vision endpoint rather than treating it as cosmetic tuning.
- REM tests: the new True/False reasoning parametrization does not actually pass or assert the parameter, so the intended forwarding behavior is not covered.
- Installer: optional-extras installation now force-reinstalls unpinned `discord.py-self>=2.0.0 --no-deps`; this is unrelated to persona/provider work and needs separate justification or removal.
- `axon-bodycam/index.html`: generated prototype with duplicate `updateRain` definitions causing recursion, nonfunctional scene/rain/recording controls, expensive frame processing, and no matching dedicated backend route.
- `hello-world/index.html`: standalone generated smoke artifact with no runtime integration.

Before PR work, separate identity/fork policy, provider behavior, REM/context wiring, installer changes, and generated assets. Fix or deliberately reject each issue above and give every resulting commit a reviewable subject/body.

## Architecture map

- `bot.py`: Discord self-bot entry point, Telegram adapter, message ingestion, prompt construction, tool loop, background loops, command queue, and shutdown.
- `providers.py`: OpenAI-compatible chat/streaming transport, native/custom tool-call parsing, endpoint fallback, retries, and usage.
- `bot_tools.py`, `tool_schemas.py`, `tool_registry.py`, `tools.py`: tool implementations, model schemas, reasoning traces, and contracts.
- `message_pipeline.py`, `concurrency_safety.py`: inbound deduplication, per-channel reply queues, reconnect watermarks, fair LLM slots, and tool concurrency.
- `rag_memory.py`: SQLite storage plus optional vector embeddings for messages, bot output, LTM, entities, shared context, and web results.
- `autonomy.py`, `autonomy_social.py`: observe → plan → policy gate → execute background agency and turn-taking controls.
- `rem.py`: optional memory consolidation/audit pass.
- `jobs.py`: detached long-running model/tool jobs with extended budgets.
- `api/`, `web/`: admin API and dashboard.
- `site_backend.py`, `site_server.py`, `docker/site-runtime/`: generated-site storage and per-site backend containers.
- `plugin_manager.py`, `plugins/`: reloadable tools/events/jobs; checkers is the current bundled plugin.
- `control_defaults.py`: shared bot/API runtime-control defaults.
- `.env.example`, `config.py`: deployment configuration contract.

## Documentation authority and drift

Use this order when documentation disagrees:

1. Current source and tests.
2. `.env.example`, `docs/OVERVIEW.md`, `docs/INSTALL.md`, `docs/CONFIGURATION.md`, and current README sections.
3. Historical audits only as leads.

Known stale documents:

- `CONTEXT_MEMORY_ANALYSIS.md` describes the pre-SQLite/pre-RAG memory system and incorrectly says the repository has no embeddings or RAG.
- `RELIABILITY_RESEARCH.md` describes an older, much smaller XML-first tool architecture. Several listed fixes are already implemented.

## Docker shell sandbox: actual behavior

### Current machine state

- Docker 26.1.5 is installed and the daemon is rootful with built-in AppArmor, seccomp, and cgroup namespaces.
- `/var/run/docker.sock` is `root:docker` mode `0660`.
- `codexy` is listed in the `docker` group, but the current login process has not acquired that supplementary group. Unsudoed Docker commands fail until a fresh login/session.
- No `maxwell-shell` image, container, or `shelldocker/` workspace existed at audit time.
- `.env` resolves `ENABLE_SHELL=true` and `MAXWELL_SHELL_FULL_HOST=false`; the feature is configured on but cannot work from the current stale login session.

Docker-group membership on a rootful daemon is effectively host-root authority. Treat compromise of the bot's host process as host compromise even when commands launched by `ShellTool` enter a container.

### Common container behavior

`ShellTool` lazily builds `docker/Dockerfile` as image `maxwell-shell` and reuses one global named container:

- Commands run as container root through `docker exec --user root bash -lc`.
- The container is persistent, writable, and shared across every user/channel.
- The only intended default host bind is `<repo>/shelldocker` → `/home/maxwell:rw`.
- `/tmp` is a 256 MiB executable tmpfs.
- Limits: 4 GiB RAM, 2 CPUs, 1024 PIDs, command timeout/output limits from `.env`.
- The image uses unpinned `ubuntu:26.04`; an existing image with the expected name is trusted without checking a Dockerfile hash.
- Root filesystem changes, installed packages, and shell startup files survive between calls.

### Default mode

Default mode is container-isolated from the host filesystem, not network-isolated:

- Docker bridge network with unrestricted outbound NAT; it may reach the Internet, LAN, Docker bridge peers, and host services depending on firewall/routing.
- `no-new-privileges`.
- Drop all capabilities, then add CHOWN, SETUID, SETGID, DAC_OVERRIDE, FOWNER, NET_RAW, and NET_BIND_SERVICE.
- No explicit host root or Docker socket mount and no published ports.

### Full-host mode

`MAXWELL_SHELL_FULL_HOST=true` adds host networking and `/:/host:rw`, while omitting the default mode's capability and no-new-privileges restrictions. On this rootful daemon, container root plus `/host` is host-filesystem root-equivalent. It is not Docker `--privileged`, but it must still be treated as host RCE.

Full-host shell calls are not owner/admin-only. The shell implementation explicitly permits any user in an allowed channel, and taint confirmation is prompt-injection friction rather than authorization.

### Known critical shell issues — not fixed yet

- `SendFileTool` can `docker cp` any absolute path from the fixed `maxwell-shell` container. In full-host mode this includes `/host/...` secrets.
- `send_file` is always registered, non-admin, and not taint-gated.
- Disabling `ENABLE_SHELL` does not remove an existing container; `send_file` still falls back to the fixed container name. A stale full-host container can therefore remain an exfiltration path after shell is disabled.
- The fixed global container/workspace leaks state across users/channels and can collide across checkouts.
- The command regex blocklist is defense-in-depth only and is bypassable with multi-step execution.
- Existing tests do not assert Docker run flags, mode transitions, container reconciliation, image freshness, or docker-copy confinement.
- `doctor.py` uses formatted `docker info`; Docker 26 can return exit code 0, blank stdout, and a permission error on stderr. That produced a false green check on this machine.
- Installer logic can enable shell after a root-only Docker check even though the runtime user cannot yet access the daemon.

Do not describe this shell as fully isolated. Do not enable full-host mode until authorization and `send_file` confinement are fixed.

## RAG and embedding model: actual behavior

Chat generation and embeddings are separate services despite the legacy `OLLAMA_*` chat variable names.

Current resolved embedding configuration:

- `ENABLE_RAG=true`
- `MAXWELL_EMBED_BASE_URL=http://localhost:11434`
- `MAXWELL_EMBED_MODEL=qwen3-embedding:0.6b`
- `MAXWELL_EMBED_DIM=1024`
- no embedding API key

No Ollama binary/process/listener existed at audit time. Therefore the localhost warning is correct and unrelated to the working hosted chat provider.

### Failure behavior

- Raw messages and facts are inserted into `data/maxwell_rag.db` with `embedding=NULL` before embedding is attempted.
- Recent channel history, newest-LTM fallback, scoped shared context, entity fallbacks, knowledge graph, chat, tools, and API remain functional.
- Semantic `rag_search` returns no results when it cannot embed the query.
- Failed background embeddings remain NULL. Connection/HTTP failures open a 30-second breaker, so the warning can recur after each cooldown when traffic retries.
- Interactive query embedding has a 1.5-second deadline and a 15-second query cooldown.
- At audit time the database held about 1,260 vector rows and zero populated embeddings: semantic recall had never become operational.

### Supported embedding backends

The default requires local Ollama only because the default URL/model point there. Alternatives are supported:

- Ollama base host becomes `/api/embed`.
- A base ending in `/v1` becomes `/v1/embeddings`.
- A full `/embeddings` or `/api/embed` URL is used as-is.
- Hosted auth must use `MAXWELL_EMBED_API_KEY`; it does not inherit the chat API key.
- `MAXWELL_EMBED_DIM` must exactly match returned vectors. The client currently does not send an OpenAI `dimensions` request parameter.

Do not switch models casually. Row vectors do not store backend/model identity, and the persistent cache key is text hash plus dimension. A same-dimension model change silently mixes vector spaces; a dimension change leaves old non-NULL rows skipped and not automatically re-embedded.

### Existing pending rows

Pending rows are not automatically backfilled during normal startup. Bulk catch-up only runs when the undocumented `MAXWELL_EMBED_PENDING_ON_BOOT=true` environment flag is set. Fix and verify the endpoint before enabling it; then monitor embedded/pending counts.

### Recommended deployment choice

For this machine, local Ollama is viable: 12 CPU threads, 31 GiB RAM, roughly 423 GiB disk free, no NVIDIA GPU. The `qwen3-embedding:0.6b` Ollama artifact is roughly 639 MB and can run CPU-only.

Use one service manager. Prefer the official systemd Ollama service here. `ecosystem.config.js` may also add `ollama serve` whenever the binary is visible, which can conflict with systemd; do not let PM2 and systemd own the same listener.

If semantic recall is unwanted, set `ENABLE_RAG=false` and restart. Do not leave it enabled against a nonexistent endpoint.

## Priority repair plan

1. Shell P0: confine shell-container file copies to `/home/maxwell`; require a registered shell tool and expected mode label; reconcile/remove stale containers when shell is disabled.
2. Shell P0: make full-host mode owner-only or remove it. Treat confirmation and blocklists as secondary controls.
3. Shell P1: fix Docker doctor/installer checks, namespace containers per checkout, verify complete HostConfig/image identity, add network policy, and add lifecycle/security tests.
4. RAG P0 operational: choose local Ollama, a verified hosted embedding endpoint, or explicitly disable RAG.
5. RAG P1: add installer choices and accurate doctor output; validate response shape/dimension; make `auto` semantics honest.
6. RAG P1: persist embedding backend identity and implement safe invalidation/re-embedding without deleting raw memories.
7. Documentation: correct shell authorization/isolation language, pending-vector startup claims, PM2/systemd ownership, and stale dashboard descriptions.

## Validation commands

```bash
git status --short --branch
.venv/bin/python3 -m pytest -q
.venv/bin/python3 doctor.py
.venv/bin/python3 doctor.py --probe  # networked: only when explicitly intended
docker info                          # must succeed as the bot runtime user
ss -ltnp 'sport = :11434'
```

For RAG counts, inspect only counts/NULL status; never dump stored message content.

## Working changelog

### Multi-instance deployment — implementation in progress

- Approved direction: disposable Python 3.14 application images, one Compose project and rootless engine per Linux service user/identity, private host config/data/sites/shell directories, writable external prompt files.
- Added instance-scoped Docker resource ownership and confined daemon-host bind translation; generated backends use an explicit private network and derived DNS targets in container mode. Legacy loopback mode remains supported.
- Container site registries use a version-2 instance envelope. Nonempty legacy registries require explicit migration; copying them into container mode is not sufficient.
- Focused Docker-runtime/site tests pass (88 offline mocked cases). No live daemon verification: the current rootful socket denied access, Compose/rootless setup tools are not installed, and no approval escalation is available. Rootless UID10001 ACL provisioning remains required.
- Added reusable app/web Docker build targets, explicit source-only build context, pinned full optional Python dependency set, Compose bot/API/web services, and sanitized per-instance config templates. Five offline packaging checks pass; clean Python 3.14 dependency installation and optional imports pass. The intentional voice-recv/discord.py-self metadata substitution is documented; base tags/apt are not digest/snapshot pinned.
- Shared external prompt storage now backs bot/API/RAG reads and edits with locked atomic writes, reload-on-use, and last-valid runtime fallback. GF configuration honors explicit DATA_DIR. API control writes run off the event loop. Container API uses verified backend targets, disables PM2 controls, and reports recent Discord snapshots; dashboard describes the snapshot delay.
- Integrated focused suite: 226 passed; full regression: 1499 passed, two skipped, one deliberately deselected secret-reading live-provider test. One pre-existing object-ID site-turn-cache collision failed in the full run and passes independently. Existing bot.py Ruff findings (unused import/local and untracked task) were verified against HEAD and left untouched.
- Shell/container image names and labels are now instance-scoped, with rootless checks, source-hash/image validation and verified-ID lifecycle operations. Shell exports use confined bind-workspace reads with no-follow directory walking; arbitrary docker cp and disabled-tool fallback are removed. Full-host mode is rejected in container mode. Forty-three focused mocked shell/export tests pass. Workspace remains shared within each instance; disable does not automatically remove old containers (use stop/down).
- Operational tooling and migration/restore review are still being integrated. No production cutover or credential/runtime-data reads were performed.
- Audit correction: `DEFAULT_CONTROL` already contains `base_personality`; the initial deployment audit's missing-key claim was incorrect. Prompt cache coherence is a real issue and is being addressed separately.

### 2026-09-06 — architecture and operations audit

- Confirmed branch baseline and clean state after root's `Initial dev commit`.
- Mapped current architecture and marked historical docs as stale.
- Audited shell container modes, authorization, persistence, networking, capabilities, Docker access, and file-export escape paths.
- Audited embedding configuration, failure degradation, database population, backfill behavior, backend switching hazards, and service-manager conflict.
- Reviewed every file in root's baseline commit and recorded the unresolved identity, provider, REM-test, installer, and generated-asset issues that must be split before an upstream PR.
- Confirmed the full test suite passed before this guide was created; one Chromium-dependent test was skipped.
- No runtime/security fixes have been applied yet. The priority repair plan above is the handoff state.
