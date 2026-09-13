# Second-round follow-up

Deferred at root's request: ship the hotfixes for manual verification first. No suite runs or broad documentation rewrite in this round.

- [ ] Add real Caddy → API → generated-backend coverage for nested tile/download routes, query strings, uploads and unchanged static/dashboard routing; inspect adapted route order.
- [ ] Cover repeated site reads and different slices after tool-history trimming/compaction. Remove obsolete read-cache/limit machinery and outdated refusal instructions afterward.
- [ ] Cover empty-text site-loop termination: exhausted iterations/time, repeated site-test stop, a visible incomplete-status reply, and an unverified site link when available. Preserve explicit no_response and already-delivered message/media behavior.
- [ ] Verify create/edit/list backend-aware advertised URLs and server activation after static-site creation. Remote mirroring does NOT execute FastAPI or provide the local KV/API service. Agree on remote backend hosting/proxy separately before promising remote interactive functionality.
- [ ] Confirm Curie's emote task manually: gallery, eight tile images, downloads, previews, re-cut/upload/reset, and a final Discord reply. Existing generated code/state was not rewritten by this hotfix.
- [ ] Add console coverage for split CSI/SS3 arrow sequences, chronological scrolling, Ollama hidden by default, o toggle, retained errors and local-time rendering. Full dates/colours remain phase two.
- [ ] Update obsolete private-network rejection tests and cover local/private HTTP fetches and redirects; retain HTTP(S), transfer-size and redirect limits.
- [ ] Reconcile STATUS/SCREEN/DOCKER/tool guidance with the accepted runtime behavior, then run focused regressions and the approved isolated full suite (keep the mandatory unsafe-test exclusion).
- [ ] Review and publish the local hotfix commits after root's manual verification; no automatic merge.
