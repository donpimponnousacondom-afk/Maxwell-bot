# Current implementation and deployment status

This is the current-state ledger, not an architectural proposal. Historical details are retained in Git. Update this page after each verified milestone; never equate documentation, mocks, live acceptance and deployment.

## Active rollout — 2026-09-09

Root authorized completion of isolated Docker/Ollama/dashboard deployment without follow-up questions, including safe cutover after tests. Starting source: `96b4803` on `pr/fixing_number_max_tool_calls`, clean. Recent telemetry, footers, debug/version, mention and retry fixes must remain intact.

Initial preflight (before provisioning): `152732.dame_curie` Screen window 0 was an idle shell; no bot Python process matched and ports 8081/8082/8765/11434 had no listeners. Rootless/Compose were not yet provisioned. The Screen session remains available and the legacy bot remains stopped.

## Target boundary

One Linux service user and private rootless engine/Compose project per identity. Bot, API/dashboard and its Ollama embedder belong to that identity. Private host directories contain configuration, prompts, raw/vector memory, generated sites, shell output and model storage. Models can use the same algorithm/image without sharing memory databases. A second synthetic instance tests the boundary; no second real Discord identity is invented.

The dashboard stays loopback-only with backend authentication. Screen is retained as the operator's shared terminal; no parallel legacy bot or PM2 supervisor.

## Evidence matrix

| Component | Implemented | Offline validation | Live validation | Deployment |
| --- | --- | --- | --- | --- |
| Rootless Compose bot/API/web packaging | Implemented with readiness, provenance and corrected image pins | 164 initial focused checks; 40 final packaging/dashboard checks pass | Actual app/web/site/shell builds; 15 optional app imports in a networkless read-only image; two API/web stacks healthy | Source-frozen `maxwell-app:01e8cbb` / `maxwell-web:01e8cbb` on both synthetic stacks; real bot cutover pending |
| Instance paths and generated backends | Yes, `b2ad6a0` | Historical mocked/path tests | Actual UID10001 inherited ACL writes, read-only code, private DNS and Caddy→API→backend route pass | Synthetic Curie site only |
| Confined shell exports/lifecycle | Yes, plus resource/process/network drift checks | 56 current focused shell/export tests pass | Actual rootless lazy build, exec, immutable-ID verification and symlink export rejection pass; 4GiB/2CPU/1024PIDs/no ports verified | Synthetic Curie shell only; real bot stopped |
| Migration/backup/restore | Yes, `1b4d6a1` plus embedding lifecycle integration | 49 operations cases and full suite pass | Real backup/down/empty-target restore: 12 files hash/owner-identical, including UID10001; restored dashboard/backend work; peer IDs/start times unchanged | Synthetic rollback tested; private original-state/source archives and migration staging prepared |
| External live prompts | Yes, `b0ec543` | Full suite and actual Caddy/API/Chromium save/reload pass | Authenticated save/reload against real API, desktop/mobile rendering | Synthetic accepted; original nonempty personality preserved in private staging |
| Dashboard | Existing frontend/API now wired to healthy restricted Caddy | Actual local Caddy/API/Chromium login, prompt save/reload at 1280/390 pass | Both Docker dashboards return HTML200, unauthenticated401, authenticated status200 and config404 | Synthetic dashboards on loopback 8081/8082; real identity credentials not migrated yet |
| Ollama provisioning in Compose | Per-engine model cache, one-shot downloader and private runtime service | Final readiness/pin/disable/shape regressions pass | Both engines pulled model under Ollama 0.33.3 and passed actual 1024-vector startup readiness | Healthy private synthetic stacks; no host embedding/API ports |
| RAG embedding client | Hardened with backend identity, strict vectors and recovery | 178 focused cases, independent review and full suite pass | Both real instances retrieve their own synthetic answer at top1; cold 1051/1547ms, warm query 139/111ms; peer answer absent | Synthetic Curie 4/4 and acceptance 3/3 embedded; no invalid/stale/pending |
| Safe backend-change invalidation/backfill | Tagged vectors/cache, preserved raw facts, explicit-db maintenance | Cache/model/endpoint changes, invalid vectors and bounded resumption covered | Physical Curie Ollama stop retained a NULL-vector raw fact; after actual breaker cooldown restart/backfill recovered it | Tested on frozen image; production 1171-row backfill remains next |
| Provider telemetry/footers/debug/version | Yes, through `0385794` | Historical 1,846-pass report, one browser skip, one live-test deselection | Prior Screen rollout recorded in history | Legacy bot now stopped |

**Current implementation acceptance: exact `01e8cbb95b17ab6c960cd386b5b7fbe56ea50ecd` passed 1,971 tests, zero skips, one deliberately excluded credential-reading live progress test in 92.76 seconds.** Python 3.14.4, source-only Git archive with no overlays, private temporary home/data/profile roots, private-read barriers and a fresh user/network namespace with only loopback. Actual Chromium/site and Caddy/API/dashboard browser cases ran. Evidence: `/home/codexy/.cache/maxwell-full-20260909.XKjuHF/01e8cbb95b17-bgb9mtj4/results.xml`. Later documentation-only commits do not change the frozen image source.

## Ordered acceptance gates

1. Reconcile stale documentation and freeze the starting source/runtime boundary.
2. Provision two private rootless engines without altering unrelated rootful workloads.
3. Build actual app/web/site/shell images and verify optional imports inside the app image.
4. Start synthetic authenticated dashboards and isolated Ollama services. Validate vector shape, latency, failure recovery and distinct memory stores.
5. Validate shell export confinement, read-only source, resource ownership, generated-site writes/ACLs, networking and unaffected second identity.
6. Test stopped-writer backup/restore with UID10001 files and compare state/ownership.
7. Back up the stopped legacy deployment, migrate with secret-preserving tooling, explicitly backfill vectors and retain rollback.
8. Start exactly one real bot plus API/web/embedder, verify sanitized startup/authentication and record dashboard access instructions.
9. Run final isolated regression, commit acceptance evidence and publish remaining limitations honestly.

## Current limitations

- All synthetic acceptance gates and the complete frozen-source regression now pass. Production state/config migration, backfill and single-bot login remain next; no real Discord login has occurred during testing. Actual failures (CLI tag, Pillow compatibility, Ollama model mismatch, Caddy capability) were repaired, not waived.
- Original state passed SQLite quick-check: 1171 rows, nonempty stored personality, no registered/running site backends, no source shell directory. The explicitly blank legacy site setting resolved to the checkout; migration deliberately uses the canonical `public/bot` subtree (seven files), never republishes the checkout, `.env`, Git or memory. Raw legacy state and starting source are archived root-only under `/srv/maxwell-rollback/curie/pre-cutover`; source is retained in place. Staged copies are private under `/srv/maxwell-migration/curie`.
- The legacy host-native installer is not the new rootless provisioning path. Model weights are persistent per-engine cache, excluded from memory backups; backend fingerprints do not detect upstream weight changes under an unchanged model tag.
- Legacy full-host shell mode remains a separate host-native risk; container mode rejects it.
- The shell workspace is intentionally shared within an identity, not per Discord user. Networked tools retain outbound access; no claim of universal network isolation.
- The broad tool-budget redesign and unrelated persona/demo-artifact repairs are outside this rollout.

## Milestones

- `9659a61` — documentation reconciliation: replaced the mixed historical `AGENTS.md` with a concise operating contract and this explicit status ledger. Historical evidence is retained at `96b4803:AGENTS.md`. No runtime/configuration change in that slice.
- Rootless prerequisites: installed seven Debian dependency packages without replacing Docker or restarting the existing rootful proxy. Installed checksum-verified Compose v2.39.4. Created private `maxwell-curie`/`maxwell-acceptance` users (1003/1004), distinct subordinate UID/GID ranges, private state roots and lingering per-user engines. Both report rootless security and systemd cgroups. Actual hello-world ran with memory/CPU/PID limits; peer socket/state access was denied. Fixed initial unit installation directory ownership before engines started. No credentials or real memory migrated.
- `152bda5` — operations integration: allowlisted only the two new owned embedding services, stopping bot/API before Ollama and preserving the existing foreign-owner refusal. 48 isolated Python 3.14 operations cases passed from a source-only snapshot with private-read/network barriers. The first runner command used the wrong cwd and ran no tests; the corrected command above passed. Live stack lifecycle/restore remains next.
- `01e8cbb` — deployment integration: per-identity Ollama runtime is internal-network-only; the separate downloader has registry egress and exits after an idempotent model pull. Corrected pinned CLI base to official 26.1.4, site Pillow to 12.3.0, and Ollama to verified stable 0.33.3 after the initial 0.11.11 received a real model-registry HTTP412. Actual vector readiness and API health now pass on both engines. Caddy's upstream file capability caused real EPERM under cap-drop ALL; removed the unnecessary capability from the image, kept container restrictions, added HTTP health and made wrapper startup wait up to 300 seconds for health. 49 wrapper cases pass; 40 final packaging/readiness/dashboard checks pass (including actual Chromium). Both actual Docker dashboards now pass authenticated/unauthenticated checks and private-file denial; the generated-site route additionally requires published-site metadata, verified before allowing proxy access. All image/source tests used synthetic state, not the real identity. Default Ruff/mypy targets now reflect Python 3.14; default scoped Ruff passes without a command-line target override.
- `55417f6` — RAG safety slice: immutable per-manager backend/model/dimension/derivation fingerprint, trusted row tags and namespaced durable cache; stale/unknown/invalid vectors are quarantined without deleting facts. Responses are shape/count/index/finiteness/nonzero validated; disabled/paused work sends no requests. Explicit-db CLI provides counts and bounded resumable backfill with eligible/excluded totals. Doctor no longer reports blank/error Docker responses or malformed embedding responses as healthy. 178 focused isolated Python 3.14 cases pass. Independent review reproduced and verified repairs for long negative feedback, system-authored entity/negative backfill, and cache-hit work bypassing the deadline (3/3 final repros pass). Full merged suite/live model acceptance remains separate.
- Shell acceptance: added rejection of changed memory/CPU/PID limits, published ports, extra scratch/device/security options, changed entrypoint/user/workdir and extra networks. 56 current focused cases pass. An actual rootless application-container driver lazily built/created the owned shell, executed a synthetic command, exported its bounded workspace file, rejected an escaping symlink and reverified immutable identity. The first driver lacked permission to read the synthetic script; fixed its source-only mode before the successful run. No real credentials, messages or bot login were used. This validates the selected explicit contract, not every possible Docker field.
