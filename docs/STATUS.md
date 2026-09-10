# Current implementation and deployment status

## Release acceptance before deployment (2026-09-10)

- Final application source **`677d2e49c555f5a64bf904ed74a6bfbba9f9bc67`** passed the complete isolated Python3.14.4 suite: **2,139 passed, zero failures/errors/skips**, 95.041s, mandatory unsafe test excluded. Evidence `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/677d2e49c555-wouibxq_/{pytest.log,results.xml}`.
- Built **`maxwell-app:677d2e4`**, image ID `sha256:4d718cad7e19f4ec84c4dbd3a7de71dbe09e8360221dee55ad58e20bf3d14b14`, from that Git archive only with frozen build metadata. Disposable acceptance used the actual image, no network/private mounts/real credentials, read-only application and private tmpfs state. Real bot construction/close passed; loaded debug worked before inference; mocked canonical image response uploaded once, empty response submitted once, keyless image config borrowed no chat key, and signed/queryless link suppression preserved labels/other previews. Evidence `/home/codexy/.cache/maxwell-image-repair.BcJpcl/{build.log,acceptance.py,acceptance.log}`.
- Root approved rollout after these checks. Fresh rollback capture and controlled maintenance are next; production is still `99fd7fa` until the rollout entry below is superseded.

## Duplicate image preview — implementation checkpoint (2026-09-10)

- Foreground Discord delivery now suppresses previews only for image links already delivered by successful image tools in that response's local `all_tool_results`. Inline/Markdown links remain clickable; other URLs, code spans, later turns and concurrent channels are unchanged. Discord attachment links match by host/path despite removed/changed signed queries; other resource URLs require exact matches. No second attachment existed in the final text path: this is targeted unfurl suppression, not message-wide `suppress_embeds` or a generation/delivery retry change.
- The existing visible-reply sanitizer also stripped Markdown labels. One bounded bracket-regex change now preserves inline labels while retaining protocol-marker/envelope removal; it cannot backtrack across an earlier closing bracket. Original response history/REM and response-owned measurement/footer handling remain separate from formatted delivery.
- **199 focused isolated tests passed**, including 43 new formatter, actual foreground-path and sanitizer cases; one mandatory unsafe test deselected. A baseline-bot negative control reproduces 10 failures. Python3.14.4, source-only/clean env/private-read/network barriers, no real Discord/provider calls. Evidence `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/preview-worktree-ko9b2h64/`; negative control `preview-worktree-amd3ar58/`. Scoped Ruff clean except the three unchanged `bot.py` baseline findings.
- Root **approved deployment after validation**, including a fresh rollback backup and brief maintenance pause; current credentials/configuration and restart semantics must remain unchanged. Final combined suite, image build/synthetic acceptance and deployment remain pending. The alias-only installation below is already live; the image/debug/preview repairs are not.

## Start alias installed; combined source suite passed (2026-09-10)

- Exact source **`9ca15323a6e59dcceef289b61368f7267e79b404`** passed the complete isolated suite: **2,096 passed, zero failures/errors/skips**, 95.864s; the mandatory live-credential test was excluded. Python3.14.4, Git-archive source only, clean environment/disabled dotenv, isolated writable roots, private-read audit and loopback-only network namespace. Evidence `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/9ca15323a6e5-uqrquzdz/{pytest.log,results.xml}`. Includes HD independence/one-request parser repair, loaded-runtime debug, and start alias; does not include the subsequent duplicate-preview fix in progress.
- Installed **only** the tested operator script at `/opt/maxwell/scripts/instance.py` under the instance operation lock, after confirming the existing script matched the expected two-line pre-alias baseline. Installed bytes match the tested snapshot; actual CLI help accepts `start`. All Compose container start epochs/restart counters stayed unchanged. Prior script: `/srv/maxwell-rollback/curie/start-alias-9ca1532/instance.py` (root-only).
- `start`/`up` are now interchangeable in the operational command. **Application image remains `99fd7fa`**; source fixes for image billing/debug are not yet deployed and `hd_image` remains temporarily disabled. No configuration, persona, credentials or private memory was changed by script installation.
- Artifact verification for the billed-image window found one retained 73,836-byte Pollinations image at 01:32:04.879 UTC and no HD persistence event. The HD tool retains no successful-but-unparsed response body, so the lost paid output cannot be recovered from its local storage. Root's two uploaded copies have identical SHA-256; the screenshot confirms attachment plus final-link preview. The final reply omitted the Discord URL's signed query, so preview suppression must recognize the same Discord attachment resource rather than rely on exact full-URL equality.

## Lifecycle start alias — implementation checkpoint (2026-09-10)

- Root requested systemctl-style spelling without changing restart scope. `scripts/instance.py <id> start` now takes the exact same path as `up`: ownership inventory and private operation lock, then `compose up -d --wait --wait-timeout 300`. The older spelling remains supported. `restart` is unchanged: bot/API only, not dependency recovery or a full stop/start cycle.
- **59 focused isolated operations tests passed**, including 10 new parameterized cases for CLI acceptance, identical health wait, lock handling, failed ownership, archive-argument rejection and unchanged restart command. Python3.14.4, synthetic/mocked operations only; Ruff clean. Evidence `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/start-worktree-llrr22pr/`.
- Source and runbooks updated. Full combined validation and installation of the operator script at `/opt/maxwell/scripts/instance.py` are pending; no actual lifecycle operation was invoked for these tests.

## Duplicate image billing — traced and fixed in source (2026-09-10)

- Root's OpenRouter CSV identified two pairs of billed Gemini image requests at 01:30:40/49 UTC and 01:31:44/53 UTC. Sanitized production logs show HD attempt 1/2 reporting empty parsed content at **01:30:49.568358** and **01:31:53.329785**, immediately before each second billed request. Persisted tool traces show **one HD invocation per pair**, not two model tool calls. Both invocations returned errors and posted no HD image.
- The parser ignored the supported OpenRouter `message.images[].image_url.url` response field; [OpenRouter's SDK schema/test](https://github.com/OpenRouterTeam/ai-sdk-provider/commit/ac62ee7d11f0ad491700186b678c0664d2eb5229) explicitly permits empty content alongside images. Retained logs prove internal retries, not the unrecorded raw response body. Source now handles those fields and equivalent content image-url parts, retains legacy inline data URIs, and permits **one generation POST per tool execution**, including ambiguous responses/timeouts/5xx. Errors warn about possible billing/no automatic repeat instead of inventing a safety refusal or encouraging another generation.
- **52 focused isolated tests passed** (49 HD, 3 Pollinations). Against `d02e67d`, 31 new-suite cases fail; 20 specifically reproduce a second POST. All HTTP/delivery/persistence mocked; Python3.14.4 and private-read/network barriers. Evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/hd-image-uncommitted-sxgdtd71/`; baseline `hd-image-uncommitted-e8bqp460/`. Scoped Ruff clean; complete combined suite pending.
- Separate display evidence: one successful Pollinations fallback completed at 01:32:05, then the final stored reply at **01:32:07.975223 UTC** reused that already-delivered image's URL. That can render the same asset again as a Discord preview; it is not evidence of another paid generation. No Discord message fetch or presentation changes were made. This patch does not deduplicate independently requested tool invocations.
- **Not deployed.** `hd_image` remains temporarily disabled in the running `99fd7fa` image. No paid generation, Discord test message, memory write or runtime restart was used for diagnosis or regression testing.

## Loaded-runtime debug — implementation checkpoint (2026-09-10)

- `!debug` now reports loaded primary/fallback model and secret-safe provider hostnames from the running provider object, before any completion is needed. Measured replies remain a separate response-owned section and may represent a different fallback/override model. The complete report uses fenced code blocks, without a meaningless unmeasured footer. No configuration reread or inference/probe is performed.
- **64 focused isolated tests passed**, including 9 new cases for no history, stale file config, different measured endpoints, credential-safe host labels, fencing/chunking and unchanged measured ownership. Python3.14.4, source-only/private-read/network isolation; evidence `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/debug-worktree-h3rzr1_l/`. Scoped observability/test Ruff passes; `bot.py` retains exactly its three pre-existing lint findings. Not deployed; combined full suite is pending.
- Runbook now explicitly distinguishes full-stack `up` after `stop` from bot/API-only `restart`, and explains historical log replay. No lifecycle semantics or running services changed by that documentation.

## HD image separation — implementation checkpoint (2026-09-10)

- Root requested that HD generation remain available but never borrow the main chat endpoint/key. `hd_image` now resolves only dedicated `GEMINI_IMAGE_*` settings; missing base returns a configuration error before downloads/HTTP. Blank dedicated key sends no Authorization header, preserving explicit keyless gateways. Pollinations and tool registration are unchanged. Native GPT Images routes are not implemented by the existing chat-completions adapter.
- **19 focused isolated tests passed** (16 new HD cases, 3 existing Pollinations); 10 new cases fail on the prior source. Mocked HTTP/delivery only, Python3.14.4, private-read/network barriers. Scoped Ruff passes. Evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/hd-image-uncommitted-5vp_fsqf/`. Full combined-suite verification and deployment remain pending.
- Immediate authorized containment: `hd_image` added to the persisted runtime disabled-tools list through the authenticated API; `image_generator` and every other control preserved. The earlier control file is backed up under `/srv/maxwell-rollback/curie/image-optout-*/`. This is temporary until safe source is deployed; the tool is not being removed.
- Current image remains `99fd7fa`. The reported `ollama` DNS failures were real but before the current bot/API startup (01:55:50 UTC); Ollama started at 01:50:51 UTC. Both containers now resolve its name and pass actual finite/nonzero 1024-dimensional embedding probes. No DNS or embedding-breaker errors in the current process epoch. Latest read-only counts: 872 total, 838 trusted embeddings, 34 eligible unembedded, zero stale/invalid; new embeddings progressed but historical backlog remains. No re-embedding, model switch, service restart or image generation was performed in this investigation.

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
