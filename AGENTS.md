# Agent Guide

## Scope and identity

This repository is `dame_curie`, a Maxwell side project. Keep existing Maxwell names in paths, classes, environment variables, APIs, and upstream-facing code unless root explicitly requests a rename.

The root `AGENTS.md` applies to the whole checkout.

For root's existing host-native deployment, read [the shared Screen workflow and handoff](docs/SCREEN_WORKFLOW.md) before touching runtime. Share `dame_curie` with `screen -x`; keep exactly one foreground bot under `flock -n /tmp/dame-curie-maxwell.lock ./run.sh`. Do not switch to PM2/Compose or restart for documentation-only changes.

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
.venv/bin/python3 -m pytest -q --deselect=tests/test_tool_progress.py::test_streaming_tick_inserts_space_between_glued_deltas
.venv/bin/python3 doctor.py
.venv/bin/python3 doctor.py --probe  # networked: only when explicitly intended
docker info                          # must succeed as the bot runtime user
ss -ltnp 'sport = :11434'
```

For RAG counts, inspect only counts/NULL status; never dump stored message content.

## Working changelog

### 2026-09-09 — reconcile live retry override/docs and restart shared Screen

- Root's follow-up caught two missed references: README still advertised three attempts, and the deployment's exact OLLAMA_RETRY_ATTEMPTS override was still 3. On explicit direction, inspected that one non-secret setting and changed it to 5. The ignored deployment file is not staged; no other configuration keys were inspected or changed.
- Corrected README's default, transient waits, empty-content recovery and fallback descriptions. Updated the standalone tool-budget HTML's provider table, replay/ceiling findings and evidence references to 5e9b5be while preserving the broader audit's historical 57d5b8c scope. The consistency regression now checks README, CONFIGURATION.md and the portable audit alongside code/template defaults, so the previous stale references fail it.
- Coordinated restart used the existing attached 152732.dame_curie window 0. Verified old bot 2232199 and flock 2232197 exited, confirmed the foreground shell and cleared pending input, then sent one flock-wrapped run.sh command. Replacement bot 2321644 / flock 2321643 started at 08:47:58 +0200 in this checkout. Sanitized startup logs confirm Discord login/guild connection and natural provider requests at attempt=1/5. No extra live model probe, duplicate bot, detached display or supervisor change; private raw Screen snapshots were deleted after extracting operational fields.
- Updated docs/SCREEN_WORKFLOW.md with the verified rollout and labeled its older snapshot historical. Validation: 137 provider tests passed under the existing isolated Python 3.14.4 environment; Ruff lint/format and diff whitespace pass. Portable HTML has unique IDs, resolving fragment links, no external assets and unchanged styles/scripts. No application-source change or repeat of the full suite in this docs/configuration follow-up; the previous unrelated site-cache failure remains recorded below.

### 2026-09-09 — provider response diagnostics and paced fixed-budget retries

- `providers.py`, `config.py` and `.env.example` now default to five total attempts with linear 10/20/30/40-second transient waits, including endpoint switches, HTTP 429/500/502/503/504 and empty-content recovery. Explicit retry settings and fast-fallback limits still apply. Deterministic corrections/failover consume remaining attempts without a delay; native-tool correction no longer starts another whole request budget. Empty-content, media and temperature recovery cannot extend the total ceiling.
- HTTP 200 decoding honors recognized JSON/+json/SSE response types and retains requested-format parsing for other/missing types. Explicit upstream errors, including errors after partial output, raise typed failures with allowlisted code/type, message-derived category and numeric framing diagnostics. Malformed JSON/Unicode decoding is reported without raw exception chaining. Nullable error fields preserve valid responses; non-null error objects and explicit error events/types fail. Unterminated SSE tails fail; preexisting skippable malformed frames and acceptance without DONE remain, with numeric diagnostics. Historical non-200 special-case free-text logging is not globally rewritten.
- Added `tests/test_provider_resilience.py`, updated provider fixtures/budget tests, and documented policy in `docs/CONFIGURATION.md`. Provider focused suite: 137 passed. Integrated mention/provider tests plus the two isolated site checks: 160 passed under Python 3.14.4. Ruff passes on provider/config/new and updated tests; the three preexisting `bot.py` findings are identical to baseline ad222dc. New test-file formatting and staged diff whitespace checks pass. Independent source review found no remaining blocking issue in this scope.
- Full offline verification: first run had 1642 passed, one failure caused by the test scratch DATA_DIR being under /tmp, one skipped browser test and one deliberately deselected credential-reading live-provider test. Rerun with isolated non-/tmp paths had 1642 passed, one known preexisting failure in `test_site_guards_work_on_slotted_discord_messages`, one browser skip and one live-test deselection. Both site checks pass alone. Unchanged baseline site-guard code reproduces stale read-loop state under simulated Python object-ID reuse; this is the existing site-turn cache issue recorded below, not repaired by this slice. Standalone live streaming scripts were excluded; no production endpoint probes were run.
- Test setup uses `/tmp/maxwell-docker-tests/bin/python` with application dependencies from `/tmp/maxwell-image-deps/lib/python3.14/site-packages`, an empty inherited environment, disabled dotenv, MAXWELL_ENV_FILE=/dev/null and isolated home/data/site roots. Browser-profile tests require the data root outside /tmp. Production .venv remains Python 3.13.5; it was not upgraded or used for verification.
- Runtime/configuration untouched during implementation: existing Screen bot PID 2232199 and flock parent 2232197 remain from the 06:48:45 start. Source changes need a coordinated shared-Screen restart. An explicit deployment OLLAMA_RETRY_ATTEMPTS still overrides the new default; private deployment configuration was not inspected or changed. Caller timeouts (including 60-second extraction) remain unchanged and may cancel before all retries. Isolation/split-brain and the unrelated site-cache repair remain separate work.

### 2026-09-09 — raw numeric self-mention reply detection

- `bot.py` now recognizes exact `<@SELF_ID>` and `<@!SELF_ID>` tokens in the incoming message content when Discord's parsed mentions omit the user. Display names, role/channel tokens, other user IDs and forwarded snapshot text do not acquire direct-reply status.
- Existing ingress controls remain authoritative: bot enable/reply toggles, ignored users, blacklist, allowed/blocked channels, per-guild solo channel and self-message protection. No changes to autonomy policy, parsed memory metadata or the existing APP-message console-log exclusion.
- Added `tests/test_bot_mentions.py`: five dispatch regressions failed against the previous implementation; all 21 cases pass with the fix. Combined mention/watch/forwarding/queue/solo/identity verification: 134 passed under isolated Python 3.14.4 with temporary runtime paths, disabled dotenv and no live endpoint requests. Full offline results and the unrelated preexisting site-cache failure are recorded in the provider-resilience entry above.
- No production restart, runtime configuration edit or credential access during this implementation. Core source fixes are separate from the planned isolation/split-brain work; coordinate the existing shared Screen restart after verification.

### 2026-09-09 — shared Screen workflow handoff

- Added docs/SCREEN_WORKFLOW.md: attach/detach/scrollback cheat sheet, single foreground bot and flock contract, coordinated stop/verify/start, agent collaboration and secret-safe testing, identity reminders, current-state snapshot and paste-ready next-agent instructions.
- Linked the runbook here and from README. Updated the validation command to exclude the existing credential-reading live-provider test; other historical architecture/audit claims remain dated and must be rechecked.
- Sanity check: branch pr/fixing_number_max_tool_calls at 34f6580 before this slice, clean worktree, attached dame_curie window 0, one Python bot with a flock parent and this checkout as cwd. No runtime changes, restart, credential/data reads or live probes. Documentation shell syntax, relative links and diff whitespace checked; application suite not run for this docs-only change.
- Next agent: re-check Git and runtime before choosing work; newer commits supersede interrupted chat TODOs. Continue only root's next assigned task, using the existing shared Screen deployment unless a cutover is explicitly approved.

### Portable tool-budget audit and repair handoff

- Added doc/html/maxwell-tool-budgets.html, matching the portable instance guide's visual style. Self-contained team handoff with current configuration semantics, confirmed findings, cross-platform execution inventory, proposed budget/outcome contract, illustrative profiles, rollout slices, acceptance tests and source references at 57d5b8c. No runtime fix is included.
- Confirmed foreground limits count batches (default 50, cap 100), not calls; Discord's deadline is soft and Telegram ignores that loop-time control. Isolated production-loop reproductions showed two rounds executing eight calls and discarding a subsequent tool-only response; a synthetic expired Discord deadline still allowed another generation. Background terminal-only send_message also reproduced repeated delivery across two rounds.
- Expanded source-only audit to X/email/voice/REM/extraction/embeddings/autonomy/plugins/manual/API paths, including child-policy propagation, HTML-salvage global-disable gap, X/SMTP ambiguous-write retries and cancellation settlement. Findings are development-source claims, not inspected production behavior. Runtime and secret files were not read; no live endpoints were contacted.
- Static validation and Playwright passed on a renamed HTML copy alone in a temporary directory, offline at 1280px and 390px: all internal links resolve, no external assets/sidecar requests/page errors or horizontal overflow, chapter/navigation controls work, no-JavaScript reading works, and print/PDF generation succeeds. The audit's narrow Python 3.14 reproductions ran without project imports; the full application suite was not run for this documentation-only slice.
- Next step: agree the shared operation-budget, inherited-policy, finalization and side-effect settlement contract, then add regression tests and implement small verified runtime slices. Do not treat lower iteration settings as a complete repair.

### Portable single-file deployment guide

- Added doc/html/maxwell-instances.html as the shareable edition: complete screenshot tour plus all docs/DOCKER.md setup/reference chapters, sanitized deployment/bot templates, first-start instructions and troubleshooting.
- All three PNG screenshots are embedded as base64; styles, image zoom and chapter navigation are inline, with internal-anchor links only. No credentials, runtime data or external assets are included. Existing source docs remain unchanged.
- Playwright verified a renamed copy placed alone in a temporary directory with networking disabled at 1280px/390px: three decoded image hashes match the reviewed demo screenshots, all eight setup code blocks and both templates present, internal links resolve, zoom/close and chapter expansion work, no horizontal overflow, page errors or network/sidecar requests.

### Visual instance tour

- Added docs/instance-tour.html with three Playwright screenshots of the actual dashboard against intercepted synthetic responses; no real credentials or runtime data were used.
- Clarifies per-instance Discord/provider credentials in host bot.env, live personality edits, server-specific prompt files, and lifecycle/backup commands. Deployment prerequisites remain explicit.
- Verified local HTML at 1280px and 390px: all three images load, local links resolve, no horizontal overflow or page errors. Mock login and personality Save section interactions pass; these are UI demonstrations, not live backend acceptance tests.

### Multi-instance deployment — implementation in progress

- Approved direction: disposable Python 3.14 application images, one Compose project and rootless engine per Linux service user/identity, private host config/data/sites/shell directories, writable external prompt files.
- Added instance-scoped Docker resource ownership and confined daemon-host bind translation; generated backends use an explicit private network and derived DNS targets in container mode. Legacy loopback mode remains supported.
- Container site registries use a version-2 instance envelope. Nonempty legacy registries require explicit migration; copying them into container mode is not sufficient.
- Focused Docker-runtime/site tests pass (88 offline mocked cases). No live daemon verification: the current rootful socket denied access, Compose/rootless setup tools are not installed, and no approval escalation is available. Rootless UID10001 ACL provisioning remains required.
- Added reusable app/web Docker build targets, explicit source-only build context, pinned full optional Python dependency set, Compose bot/API/web services, and sanitized per-instance config templates. Five offline packaging checks pass; clean Python 3.14 dependency installation and optional imports pass. The intentional voice-recv/discord.py-self metadata substitution is documented; base tags/apt are not digest/snapshot pinned.
- Shared external prompt storage now backs bot/API/RAG reads and edits with locked atomic writes, reload-on-use, and last-valid runtime fallback. GF configuration honors explicit DATA_DIR. API control writes run off the event loop. Container API uses verified backend targets, disables PM2 controls, and reports recent Discord snapshots; dashboard describes the snapshot delay.
- Integrated focused suite: 226 passed; full regression: 1499 passed, two skipped, one deliberately deselected secret-reading live-provider test. One pre-existing object-ID site-turn-cache collision failed in the full run and passes independently. Existing bot.py Ruff findings (unused import/local and untracked task) were verified against HEAD and left untouched.
- Shell/container image names and labels are now instance-scoped, with rootless checks, source-hash/image validation and verified-ID lifecycle operations. Shell exports use confined bind-workspace reads with no-follow directory walking; arbitrary docker cp and disabled-tool fallback are removed. Full-host mode is rejected in container mode. Forty-three focused mocked shell/export tests pass. Workspace remains shared within each instance; disable does not automatically remove old containers (use stop/down).
- Added host lifecycle wrapper with fixed service-user/rootless-socket selection, literal deployment parsing, ownership checks, writer quiescence, and same-identity backup/restore. Offline legacy migration validates empty destinations, preserves source, separates prompts, converts registry metadata and retains desired backend state; startup recreates missing desired containers. Operations tests: 44 passed, including real temporary SQLite/archive subprocess roundtrip; migration tests: 23 passed.
- Latest complete offline suite: 1527 passed, two skipped, one deliberately deselected secret-reading live-provider test. Dashboard JavaScript syntax and full locked app/API imports pass. Actual Docker image builds, rootless resource/ACL/network behavior, and two-engine restore acceptance remain unverified until host prerequisites are provisioned. See docs/DOCKER.md. No production cutover or credential/runtime-data reads were performed.
- Audit correction: `DEFAULT_CONTROL` already contains `base_personality`; the initial deployment audit's missing-key claim was incorrect. Prompt cache coherence is a real issue and is being addressed separately.

### 2026-09-06 — architecture and operations audit

- Confirmed branch baseline and clean state after root's `Initial dev commit`.
- Mapped current architecture and marked historical docs as stale.
- Audited shell container modes, authorization, persistence, networking, capabilities, Docker access, and file-export escape paths.
- Audited embedding configuration, failure degradation, database population, backfill behavior, backend switching hazards, and service-manager conflict.
- Reviewed every file in root's baseline commit and recorded the unresolved identity, provider, REM-test, installer, and generated-asset issues that must be split before an upstream PR.
- Confirmed the full test suite passed before this guide was created; one Chromium-dependent test was skipped.
- No runtime/security fixes have been applied yet. The priority repair plan above is the handoff state.
