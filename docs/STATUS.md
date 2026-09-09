# Current implementation and deployment status

This is the current-state ledger, not an architectural proposal. Historical details are retained in Git. Update this page after each verified milestone; never equate documentation, mocks, live acceptance and deployment.

## Active rollout — 2026-09-09

Root authorized completion of isolated Docker/Ollama/dashboard deployment without follow-up questions, including safe cutover after tests. Starting source: `96b4803` on `pr/fixing_number_max_tool_calls`, clean. Recent telemetry, footers, debug/version, mention and retry fixes must remain intact.

Preflight: existing `152732.dame_curie` Screen window 0 is a shell; no bot Python process matched; dashboard/API/Ollama ports 8081/8082/8765/11434 have no listeners. Host has systemd and passwordless administrative access. Rootless/Compose prerequisites are not yet provisioned. The legacy bot must remain stopped during migration.

## Target boundary

One Linux service user and private rootless engine/Compose project per identity. Bot, API/dashboard and its Ollama embedder belong to that identity. Private host directories contain configuration, prompts, raw/vector memory, generated sites, shell output and model storage. Models can use the same algorithm/image without sharing memory databases. A second synthetic instance tests the boundary; no second real Discord identity is invented.

The dashboard stays loopback-only with backend authentication. Screen is retained as the operator's shared terminal; no parallel legacy bot or PM2 supervisor.

## Evidence matrix

| Component | Implemented | Offline validation | Live validation | Deployment |
| --- | --- | --- | --- | --- |
| Rootless Compose bot/API/web packaging | Yes, `826257a` plus newer telemetry assets | Historical static/package tests | Pending actual builds/startup | Not cut over |
| Instance paths and generated backends | Yes, `b2ad6a0` | Historical mocked/path tests | Pending two-engine network/ACL checks | Not cut over |
| Confined shell exports/lifecycle | Yes, plus resource/process/network drift checks | 56 current focused shell/export tests pass | Actual rootless lazy build, exec, immutable-ID verification and symlink export rejection pass; 4GiB/2CPU/1024PIDs/no ports verified | Synthetic Curie shell only; real bot stopped |
| Migration/backup/restore | Yes, `1b4d6a1` | Real temporary archives plus mocked engine operations | Pending rootless ownership/restore checks | Not used for this rollout |
| External live prompts | Yes, `b0ec543` | Historical prompt/API tests | Pending dashboard edits/reload | Legacy source includes changes |
| Dashboard | Existing frontend/API and Caddy service | Synthetic UI/packaging tests | Pending authenticated backend acceptance | Not listening at preflight |
| Ollama provisioning in Compose | No at starting source | Pending | Pending local model/latency test | No listener at preflight |
| RAG embedding client | Predates baseline | Historical mock tests | Pending synthetic write/embed/search/recovery | No current counts claimed |
| Safe backend-change invalidation/backfill | In progress | Pending | Pending | Not deployed |
| Provider telemetry/footers/debug/version | Yes, through `0385794` | Historical 1,846-pass report, one browser skip, one live-test deselection | Prior Screen rollout recorded in history | Legacy bot now stopped |

Historical full-suite counts are not current-HEAD acceptance evidence. The new final suite must use a source-only snapshot and exclude the credential-reading live progress test.

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

- Two private rootless engines and host prerequisites are now provisioned and live-checked. Application image/service acceptance remains in progress; the first actual build exposed the nonexistent `docker:26.1.5-cli` image tag, now being corrected to a verified pinned upstream tag/digest.
- Existing `doctor.py`/installer checks and embedding cache identity have known gaps; work is underway rather than claimed complete.
- Legacy full-host shell mode remains a separate host-native risk; container mode rejects it.
- The shell workspace is intentionally shared within an identity, not per Discord user. Networked tools retain outbound access; no claim of universal network isolation.
- The broad tool-budget redesign and unrelated persona/demo-artifact repairs are outside this rollout.

## Milestones

- `9659a61` — documentation reconciliation: replaced the mixed historical `AGENTS.md` with a concise operating contract and this explicit status ledger. Historical evidence is retained at `96b4803:AGENTS.md`. No runtime/configuration change in that slice.
- Rootless prerequisites: installed seven Debian dependency packages without replacing Docker or restarting the existing rootful proxy. Installed checksum-verified Compose v2.39.4. Created private `maxwell-curie`/`maxwell-acceptance` users (1003/1004), distinct subordinate UID/GID ranges, private state roots and lingering per-user engines. Both report rootless security and systemd cgroups. Actual hello-world ran with memory/CPU/PID limits; peer socket/state access was denied. Fixed initial unit installation directory ownership before engines started. No credentials or real memory migrated.
- `152bda5` — operations integration: allowlisted only the two new owned embedding services, stopping bot/API before Ollama and preserving the existing foreign-owner refusal. 48 isolated Python 3.14 operations cases passed from a source-only snapshot with private-read/network barriers. The first runner command used the wrong cwd and ran no tests; the corrected command above passed. Live stack lifecycle/restore remains next.
- Shell acceptance: added rejection of changed memory/CPU/PID limits, published ports, extra scratch/device/security options, changed entrypoint/user/workdir and extra networks. 56 current focused cases pass. An actual rootless application-container driver lazily built/created the owned shell, executed a synthetic command, exported its bounded workspace file, rejected an escaping symlink and reverified immutable identity. The first driver lacked permission to read the synthetic script; fixed its source-only mode before the successful run. No real credentials, messages or bot login were used. This validates the selected explicit contract, not every possible Docker field.
