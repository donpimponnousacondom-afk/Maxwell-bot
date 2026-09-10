# Current implementation and deployment status

## Current deployment — TTS repair (2026-09-10)

**Curie is running `maxwell-app:99fd7fa`**, frozen source `99fd7fa4bcd4083653cbd29402840edc7b4bc97f`, Python3.14.4. Web remains `maxwell-web:01e8cbb`; private engine, loopback dashboard and original identity are unchanged. This release also deploys the primary request options below, without changing chat model/routing/reasoning settings.

- `TtsTool.execute` owns a per-call `/tmp/tts_*` directory for WAV/OGG synthesis, conversion and delivery. The application filesystem stays read-only; success, provider/send failure and awaited cancellation clean scratch. Provider order, voices, languages and cooldown are unchanged.
- **60 focused isolated tests passed**, including 12 new lifecycle/path cases. Both read-only-write and partial-provider-cleanup regressions fail against the previous source. Exact `99fd7fa`: **2028 complete-suite tests passed, zero skipped, one mandatory deselection**, 95.02s, exit0, Python3.14.4 with source-only archive, isolated roots, disabled dotenv, private-read guard and loopback-only network namespace. Evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/99fd7fa4bcd4-zh4_rdh1/`. Scoped Ruff passes.
- Actual old image reproduced EROFS under read-only `/app`. Actual new image passed the same full TTS path using real local eSpeak PCM, then passed **real NVIDIA Riva synthesis**: 135168 PCM bytes converted to 6417-byte non-silent Opus, 1.539s. Both used absolute scratch and removed temporary directories. Delivery was intercepted: **no test Discord send**. Actual `MaxwellBot()` construction/closure also passed in a credential-free, networkless, read-only container.
- The key root added was in the development checkout `.env`, not the active private config. Only `NVIDIA_API_KEY` was transferred into `/srv/maxwell/curie/config/bot.env` (mode0600, service-user owned). All other parsed settings match the saved prior config; current chat model remains `google/gemini-3.7-flash`. Environment changes require bot/API restart; editing the development `.env` does not configure the container.
- Production was quiesced once, backed up, and recreated with the verified image. Same Discord ID, fresh post-restart snapshot, provider initialization, zero restarts and zero error-level startup lines verified. Dashboard original credentials authenticate; unauthenticated API401 and private config404 remain enforced. Screen is retained and its log-following lock remains held. Backup had 672 vectors; running instance subsequently had 683/683 embedded with zero pending—no baseline-count rollback occurred.
- Fresh validated state backup: `/srv/maxwell-backups/curie/pre-tts-99fd7fa.tar`, including the staged NVIDIA key. SQLite backup was read successfully with its WAL. Original pre-key `bot.env`, old `deploy.env` and source archive are under root-only `/srv/maxwell-rollback/curie/tts-99fd7fa/`; old app image `3229a84` remains available. No state migration/schema change was introduced. Diagnostics (redacted, synthetic audio metadata) are under `/home/codexy/.cache/maxwell-tts-fix.F9BDBX/`.

## Primary request options — included in current image

- Added `OLLAMA_EXTRA_BODY` and `OLLAMA_EXTRA_HEADERS` as strict JSON-object configuration for the main client's primary endpoint. Enables OpenRouter `provider.only` and explicit `reasoning.effort` without changing account/workspace-wide routing. Runtime fields and explicit reasoning-disable calls retain precedence; API-key Authorization wins case-insensitively.
- Primary options are not sent to fallback/vision or separately constructed background clients. Shared main-client background calls inherit them; nested request bodies are independently copied for each attempt. Malformed configuration fails closed without printing its contents; existing lenient X override parsing is unchanged.
- Verified source `ac5b3a668fc8e38d9b0cd11164d3ea6226afc743`: **327 focused provider/startup tests passed**, then **2016 complete-suite tests passed, zero skipped, one mandatory deselection**, 95.14s, exit0. Python3.14.4, source-only Git archives, disabled dotenv, clean synthetic roots, private-read guard and loopback-only network namespaces. Includes 43 new option/config/wiring regressions with mocked provider transports; scoped Ruff passes. Full evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/ac5b3a668fc8-ginqmo95/{revision.txt,pytest.log,results.xml}`. No paid chat completion was used as acceptance.
- This feature was source-only at its implementation checkpoint and is now deployed in `99fd7fa`. Main/autonomy reasoning remains not explicitly disabled with no requested effort; auxiliary calls request reasoning disabled. No provider pin or model switch was applied.
- Configuration examples and precedence: [configuration guide](CONFIGURATION.md#custom-request-options-and-openrouter-routing) and `.env.example`.

## Initial rootless deployment — 2026-09-09 (historical acceptance)

**Curie is running in her private rootless Docker stack.** Real Discord login matches the original identity; the existing chat provider initialized successfully. The authenticated dashboard reports online from a fresh Discord snapshot. First successful live check: 1174/1174 trusted embeddings, zero pending, zero container restarts and zero error-level startup log lines. Bot activation and memory storage remain enabled. Counts naturally change during operation.

- Application: `maxwell-app:3229a84`, frozen source `3229a846e001466e7ad8cbece7682a301a04f575`, Python **3.14.4**, clean build provenance verified inside the running container.
- Web: unchanged tested `maxwell-web:01e8cbb`. Later documentation-only commits do not alter either frozen artifact.
- Account/engine/project: `maxwell-curie` UID1003, `/run/user/1003/docker.sock`, `maxwell-curie`. Per-user Docker enabled with lingering.
- Operational source: root-owned `/opt/maxwell`; private configuration/state under `/srv/maxwell/curie`.
- Dashboard: **http://localhost:8081/admin/**, original administrator credentials retained. Only loopback is published; no host API/Ollama port. Forward 8081 over SSH when remote.
- Existing `152732.dame_curie` Screen/window 0 is retained, attached displays untouched. It follows Compose logs under the original advisory lock. **Ctrl-c stops the log follower, not the bot.** Use [the current Screen runbook](SCREEN_WORKFLOW.md) for lifecycle commands.
- The disposable `acceptance` stack was removed after successful acceptance; its engine is stopped and lingering disabled. Private test state, images and model cache remain for repeatability. Its shutdown left Curie's container IDs/start times/restart counts unchanged. Unrelated rootful `cli-proxy-api` remains running and was not modified.

## Verified evidence

| Area | Evidence |
| --- | --- |
| Complete regression | Exact `3229a84`: **1973 passed, zero skipped, one mandatory live-credential test deselected**, 94.99s, exit 0. Python 3.14.4, fresh source-only Git archive, isolated home/data, private-read barrier, fresh user/network namespace with only loopback. Actual Chromium/Caddy/API/dashboard cases ran. |
| Bot startup | First `01e8cbb` launch exposed `/app/data` EROFS in `PluginManager`, before any Discord login. Stopped rather than weakening the read-only filesystem. `3229a84` passes the configured data directory explicitly. Two real constructor regressions fail before/pass after; complete constructor/close also passed in both actual read-only, networkless engines with synthetic state and all 79 tools. Corrected production login then succeeded. |
| Packaging | Actual rootless app/web/shell/site builds, optional dependency imports, accurate frozen build metadata. Final app also synthesized/decoded local audio and rendered an 800×600 Chromium screenshot using writable scratch under read-only/no-capabilities/no-network restrictions. No voice-call side effect was tested. |
| Dashboard | Actual local Caddy/API/Chromium login, prompt save/reload and desktop/mobile layout pass. Both Docker dashboards returned HTML200, unauthenticated401, authenticated status200 and private config404. Production authentication and fresh online status pass with unchanged real credentials. |
| Private Ollama | Separate per-engine model volumes, one-shot registry downloader, private internal runtime network. Both pulled `qwen3-embedding:0.6b` using pinned Ollama 0.33.3 and returned real valid 1024-dimensional vectors. No host Ollama/API publishing. |
| Semantic recall and recovery | Both instances returned their own synthetic answer at top1; peer fact absent. Cold embedding 1051/1547ms, warm query 139/111ms. Physical Curie Ollama stop retained a raw NULL-vector fact; real cooldown/restart/backfill recovered it. Synthetic final counts Curie4/4, acceptance3/3 trusted, nothing pending. |
| Backend-change safety | Backend-tagged vectors/cache, strict validation, stale/legacy exclusion without raw-fact deletion, snapshot/CAS writes and bounded resumable backfill. 178 focused cases plus independent negative/entity/cache-deadline repros and full suite. |
| Generated backends | Actual UID10001 inherited-ACL writes, read-only source, private DNS and Caddy→API→backend routing. Source labels, immutable IDs and confined ownership paths checked. |
| Shell | 56 focused cases plus actual lazy build, exec, confined immutable-ID export and escaping-symlink denial. Verified 4GiB/2CPU/1024PIDs, no ports/devices, required tmpfs/caps/security/process/network contract. |
| Backup/restore and isolation | Real synthetic backup/down/empty-target restore: 12 files hash/owner-identical, including UID10001. Reapplied ACLs; restored dashboard/backend worked. Peer IDs/start times/health unchanged. Reverse peer shutdown later left production unchanged. Cross-user configuration/socket access denied. |
| Existing response features | Telemetry, retries, footers, debug/version and mention fixes retained and covered by the complete regression; actual frozen container build metadata verified. No test Discord message was sent to claim footer rendering. |

Full-suite evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/3229a846e001-avhup6un/{revision.txt,pytest.log,results.xml}`. Earlier exact `01e8cbb` passed1971 tests, but that is historical evidence, not a substitute for the final rerun.

Mandatory deselection: `tests/test_tool_progress.py::test_streaming_tick_inserts_space_between_glued_deltas` directly reads deployment credentials and can contact a real provider. No other tests were excluded or skipped. No test Discord/email/X/CAPTCHA side effects were sent. Production startup was the final rollout, not a credential-bearing test fixture; normal configured activity may resume after login.

## Migration and rollback

1. The legacy Screen bot was confirmed stopped with no source-tree Python process. Original configuration/state were archived privately before migration; original files and the Python 3.13.5 venv remain in place.
2. The explicitly **blank** old site setting resolved to the checkout, not a safe public root. Migration used the canonical `public/bot` subtree—seven files—not the checkout, `.env`, Git, venv or memory. No registered/running generated backend or existing shell source was present.
3. Private staging was inspected for symlinks, dotenv and special files. Target synthetic roots were preserved separately, then replaced only with the target engine stopped. Original Discord/chat/admin credentials, chat model, identity, feature controls and personality were retained. Only deployment paths, loopback origin and the private embedding backend were adjusted; duplicate infrastructure keys were replaced, not appended blindly.
4. **All 1171 original raw rows/columns, personality, controls, server prompts and public bytes were verified preserved.** Explicit private-Ollama backfill embedded1171/1171, zero failures/stale/invalid/pending; raw columns were rechecked after backfill. The bot subsequently reported1174/1174 at its first healthy check.

Retained private artifacts:

- `/srv/maxwell-rollback/curie/pre-cutover/legacy-state.tar`: original configuration/state, root-only (0600).
- `/srv/maxwell-rollback/curie/pre-cutover/source-96b4803.tar`: matching starting source, root-only.
- `/srv/maxwell-rollback/curie/pre-cutover/curie-deploy-fixed.env`: corrected image/deployment settings; normal state archives do not include `deploy.env`.
- `/srv/maxwell-backups/curie/pre-login-01e8cbb.tar`: ready 1171-row pre-login state, 0600, credentials included. The filename records when it was taken, **not** the image to relaunch; use the corrected application image `3229a84`.
- `/srv/maxwell-backups/curie/synthetic-final.tar`: tested synthetic restore archive. Original synthetic roots and private migration staging remain outside the production instance.

See [backup/restore instructions](DOCKER.md#backup-and-restore). Restore requires the same instance ID, no owned containers and empty config/data/sites/shell roots. It leaves the instance stopped. Reapply mapped UID ACLs before generated-backend startup; model weights are separate cache, not state-backup contents. No automatic or silently parallel host-native fallback is installed.

## Boundaries and remaining operator choices

- Public generated-site links remain loopback-only until root supplies an approved TLS origin/reverse proxy. Do not expose the dashboard or Ollama to make links convenient.
- Physical users/engines/state provide identity isolation. An unchanged model tag with changed upstream weights is **not** detected by endpoint/model/dimension/derivation fingerprints. The actual selected model and pinned server were live-tested; no unsupported minimum-version claim is inferred.
- The shell workspace is shared within one identity, not isolated per Discord user. Networked tools retain outbound access; this is not universal network isolation.
- Existing optional account/feature settings were preserved, not invented. Provider initialization is a successful `/models` probe; no synthetic paid chat completion or Discord/email/X/CAPTCHA action was used as acceptance.
- Scoped new-code checks pass. `bot.py` retains three unchanged baseline Ruff findings (unused import/local and an unretained plugin-dispatch task), independently reproduced on `01e8cbb`; no linter rule was relaxed and no unrelated refactor was added.
- Historical native scripts and portable HTML guides are reference/rollback material, not instructions to launch a second bot. Use the current [Screen runbook](SCREEN_WORKFLOW.md) and [rootless operating reference](DOCKER.md).

## Rollout commits

| Commit | Verified slice |
| --- | --- |
| `9659a61` | Replace stale audit with operating contract and current rollout ledger |
| `152bda5` | Provision private rootless engines and own embedding lifecycle |
| `112b438` | Reject shell resource/process/network drift before reuse/export |
| `55417f6` | Isolate vector spaces and add validated resumable backfill |
| `01e8cbb` | Package healthy dashboards, compatible pinned Ollama and frozen provenance |
| `2c0fccc` | Record complete regression and real restored-service acceptance |
| `3229a84` | Fix actual read-only bot startup; add real constructor regressions |

Starting source was `96b4803` on `pr/fixing_number_max_tool_calls`. Historical detail remains in Git. No push, amend, rebase or unrelated supervisor migration was performed.
