# NEXT ROUND: FINISH THIS ITERATION, PUSH THE BRANCH, OPEN THE PR

**LOCAL COMMITS EXIST. THIS BRANCH HAS NOT BEEN PUSHED AND HAS NO PR. DO NOT LOSE OR REWRITE THIS HISTORY.**

## Resume here (root's handoff, 2026-09-13)

- Working branch: `fix/console-navigation-noise-time`, based on merged main `84935df` (PR#11). PR#10 and PR#11 are already merged; do not reopen their work.
- Local hotfix commits: `abd895f` (console arrows, Ollama toggle/default hiding, local clock display), then `1b96027` (nested API routing, source re-reads, non-silent site-task ending, backend-aware URLs). Preserve this order. A notes-only handoff commit may follow.
- Last verified deployment: `maxwell-app:1b96027` and `maxwell-web:1b96027`; fresh Discord login, zero startup errors, healthy API/web/Ollama, publisher active. Generated site code/images were not rewritten. The console-only patch is also live.
- Root is taking a break and manually testing. Collect that feedback before expanding scope. No new runtime work or Netlify integration during the handoff.
- Next round: finish the agreed fixes and deferred validation/documentation below, inspect the complete accumulated diff, push the feature branch and open its PR. Root merges manually. No force-push, rebase, squash, reset or direct main writes. Fetch and inspect current main/PR state before deciding how to integrate newer upstream work; preserve the local commits.
- `docs/STATUS.md` is behind these explicitly deferred hotfixes. Do not mistake its previous image/behavior descriptions for current runtime proof.

## HOSTING SCOPE — STATIC DREAMHOST IS INTENTIONAL, NOT AN UNFINISHED FASTAPI DEPLOYMENT

- Root already understood DreamHost shared-hosting limitations and accepts static-only mirroring. Do not turn the next round into a remote FastAPI hosting/proxy project.
- Curie may build and test FastAPI/Python locally. A copied remote page may lack its backend; root accepts this and can ask Curie to package the project for Discord/download and deploy it elsewhere himself.
- Preserve local Python tooling: the automatic image cutter is useful behavior, not a mistake to prohibit or rewrite.
- Netlify MCP/API deployment is a possible FUTURE integration, not work authorized now. React/static frontends plus Netlify-compatible JavaScript/TypeScript functions are a practical target; an unchanged persistent Python/FastAPI server is not the same deployment model. References: https://docs.netlify.com/build/functions/overview/ and https://docs.netlify.com/build/build-with-ai/netlify-mcp-server/ .
- Root may explicitly ask for another target-compatible framework/runtime later. The current DreamHost mirror's `static.htaccess` deliberately serves source files statically, including PHP; enabling PHP/CGI execution would require an explicit serving-policy change, not merely copying a different extension.
- Revisit the last hotfix's backend-aware URL wording with root's clarified intent; do not impose new restrictions on creating, mirroring, or packaging local backend projects.

## Deferred validation and polish

Deferred at root's request: ship the hotfixes for manual verification first. No suite runs or broad documentation rewrite in the hotfix round.

- [ ] Add real Caddy → API → generated-backend coverage for nested tile/download routes, query strings, uploads and unchanged static/dashboard routing; inspect adapted route order.
- [ ] Cover repeated site reads and different slices after tool-history trimming/compaction. Remove obsolete read-cache/limit machinery and outdated refusal instructions afterward.
- [ ] Cover empty-text site-loop termination: exhausted iterations/time, repeated site-test stop, a visible incomplete-status reply, and an unverified site link when available. Preserve explicit no_response and already-delivered message/media behavior.
- [ ] Verify create/edit/list backend-aware advertised URLs and server activation after static-site creation, respecting root's accepted static-mirror/local-backend/package workflow. Remote backend hosting is NOT required to finish this iteration.
- [ ] Confirm Curie's emote task manually: gallery, eight tile images, downloads, previews, re-cut/upload/reset, and a final Discord reply. Existing generated code/state was not rewritten by this hotfix.
- [ ] Add console coverage for split CSI/SS3 arrow sequences, chronological scrolling, Ollama hidden by default, o toggle, retained errors and local-time rendering. Full dates/colours remain phase two.
- [ ] Update obsolete private-network rejection tests and cover local/private HTTP fetches and redirects; retain HTTP(S), transfer-size and redirect limits.
- [ ] Reconcile STATUS/SCREEN/DOCKER/tool guidance with the accepted runtime behavior, then run focused regressions and the approved isolated full suite (keep the mandatory unsafe-test exclusion).
- [ ] Review and publish the local hotfix commits after root's manual verification; no automatic merge.
