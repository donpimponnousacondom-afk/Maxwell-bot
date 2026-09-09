# Dame Curie — shared Screen workflow and agent handoff

This is the operating contract for root's **existing host-native deployment**, not the multi-instance Compose deployment described in [DOCKER.md](DOCKER.md). Read [AGENTS.md](../AGENTS.md) first. Do not migrate process managers as part of an unrelated fix.

## Non-negotiables

- Worktree: `/home/codexy/Dame_Curie/Maxwell-bot`. Run `pwd`; do not confuse the repository with the DSH harness checkout.
- Share **one GNU Screen session**, `dame_curie`, with root. Keep the bot in its foreground, visible to everyone attached.
- Run **exactly one bot for this deployment**, always through `flock -n /tmp/dame-curie-maxwell.lock ./run.sh`.
- The lock is advisory: an unwrapped `python bot.py` bypasses it. Never launch a second copy from a tool shell, background job, PM2, systemd, Compose, or another Screen window.
- Only one person/agent types into the shared terminal at a time. Announce stop/start operations first. Other agents can inspect source or run isolated tests; the coordinating agent owns bot lifecycle.
- No restart for documentation-only changes. A restart reconnects to Discord and may resume autonomous actions.

## Screen cheat sheet

Run these from a normal terminal as the same OS user (`codexy`):

```bash
screen -ls                          # discover sessions; IDs change
screen -x dame_curie                 # join WITHOUT detaching root
screen -S dame_curie -Q windows      # list windows; verify the bot window
```

Inside Screen, press **Ctrl-a**, release, then the second key:

| Keys | Effect |
| --- | --- |
| Ctrl-a d | Detach your display; bot keeps running |
| Ctrl-a [ | Enter scrollback/copy mode; arrows/PgUp/PgDn navigate; Esc exits |
| Ctrl-a 0 | Select window 0 (verify it is the bot window first) |
| Ctrl-a w | Show windows |
| Ctrl-a a | Send a literal Ctrl-a to the foreground program |
| Ctrl-c | Interrupt the foreground program: this STOPS the bot, not a detach |

Avoid `screen -d -r`: it detaches someone else's display. Avoid `exit`, Ctrl-d at the shell prompt, `screen -X quit`, and Ctrl-a k: they can destroy the shared shell/window/session. Do not create extra bot windows.

If the session is missing, first inspect processes and check with root. Only after confirming there is no existing bot/session to recover, create it with `screen -S dame_curie`. Do not silently replace a missing session or bypass a held lock.

## Re-check state before acting

```bash
cd /home/codexy/Dame_Curie/Maxwell-bot
pwd
git status --short --branch
git log -3 --oneline
screen -ls
screen -S dame_curie -Q windows
pgrep -af '[p]ython(3([.][0-9]+)?)? .*bot[.]py'
```

`pgrep` exit 1 means no match; inspect it rather than hiding all failures with `|| true`. A process-name match alone is not proof of ownership. For each candidate PID inspect `ps -o pid,ppid,tty,lstart,args -p PID` and `readlink /proc/PID/cwd`; inspect its parents too. Expect `SCREEN → bash → flock → python3 bot.py` for this checkout. Do not signal unrelated deployments. Never inspect `/proc/PID/environ` or print secrets to establish identity.

## Stop → verify → start (only when requested/needed)

**Human at the shared terminal:** Ctrl-c once, then wait for shutdown and the shell prompt. Verify the old Python process has exited before doing anything else.

**Agent through tools:** after confirming window 0 is the bot window, send only the interrupt:

```bash
screen -S dame_curie -p 0 -X stuff $'\003'
```

Re-check the known PID and parent `flock`. If shutdown hangs, investigate and report it; do not immediately send SIGKILL or queue another launch. Do not remove the lock file: deleting it can defeat locking through separate inodes.

After the bot exits, confirm the shell is ready and has no pending input. Then send **one complete command**, with an explicit directory and newline:

```bash
screen -S dame_curie -p 0 -X stuff $'cd /home/codexy/Dame_Curie/Maxwell-bot && flock -n /tmp/dame-curie-maxwell.lock ./run.sh\n'
```

Or type the command directly in the shared terminal:

```bash
cd /home/codexy/Dame_Curie/Maxwell-bot && flock -n /tmp/dame-curie-maxwell.lock ./run.sh
```

Do not send interrupt and launch as one blind batch. We previously concatenated two launches into `./run.shflock`, which failed. `screen -X stuff` returning success means input was delivered, **not** that startup succeeded.

Verify one matching bot, its checkout and lock-owning parent, plus successful startup/connection in the shared terminal. A PID alone does not prove Discord/provider health. A held lock is a reason to find the existing owner, not change the lock path. Screen is a persistent terminal, not a crash-restarting supervisor.

## How root and agents work together

1. State what is known, inspect what is not. Keep updates short; ask when scope or a consequential choice is unclear.
2. Read the relevant source/tests and current diff before editing. Root may change models, branches, or configuration between turns. Preserve those choices; do not restore an earlier chat value.
3. Agree the narrow fix. Do not add unrelated refactors, broad exception handling, dependencies, logging, or compatibility changes.
4. Keep runtime/secret files private under the repository rules. Do not dump `.env`, `data/`, tokens, cookies, prompts from real conversations, or full terminal scrollback into chat or Git. Use sanitized templates, synthetic test data, and narrowly scoped non-secret status. Configuration changes needing otherwise forbidden access require root's explicit direction.
5. Test the smallest affected subsystem, then broader offline regressions. Read tests before running them: one existing pytest test contacts the live provider and reads credentials. Exclude it unless explicitly authorized:

   ```bash
   .venv/bin/python -m pytest -q --deselect=tests/test_tool_progress.py::test_streaming_tick_inserts_space_between_glued_deltas
   ```

   Re-audit test selection as the suite evolves; this exclusion is not a universal network sandbox. Do not run `doctor.py --probe` or standalone live streaming harnesses casually. Verify the intended interpreter/environment, and report version mismatches instead of silently upgrading the live venv.
6. For runtime changes, coordinate the stop/edit/test/restart window. Stop before editing files the running bot could reload; avoid an unannounced long outage. Tests and code edits may run outside Screen; the production bot must stay inside it.
7. Follow AGENTS.md commit discipline: review the staged diff, stage only the coherent slice, include behavior/tests/remaining work in the commit body. No blanket `git add .`, resets, rebases, force pushes, or deployment changes to clean up someone else's work.
8. End with files/commit, exact tests and exceptions, runtime running/stopped status, and the next concrete step. Distinguish source inspection, synthetic payload validation, and actual upstream acceptance.

Subagents get bounded tasks with explicit file ownership. Track their IDs and collect results; a failed child is not a completed task. Check its partial edits before resuming. Do not let multiple agents edit the same files or control Screen concurrently.

## Identity and scope reminders

Session-agreed identity: Dame Curie (`1545541390392369165`), owner `.normal.man` / `root` (`1482143139828596916`), command prefix `!`. These are the agreed deployment identity, not freshly read runtime configuration.

Retain technical Maxwell module/class/env names. Preserve genuine Discord history, Z3ki's identity in historical records, and technical `z3ki.dev`/GitHub URLs. Do not blanket-replace names or IDs in stored data.

Root changed the model manually during the conversation; do not pin a slug from chat memory. The sampling work requested `temperature=0.6`, `top_p=0.95`, `top_k=20`, native reasoning for main/autonomy, and explicit non-thinking auxiliary calls. Inspect current implementation and regression coverage before declaring that work complete or changing it again.

The host bot and its Docker-backed tools are different layers. Docker-group access can differ between the shared Screen shell and an agent's login; re-check the relevant execution context rather than claiming a daemon failure from one terminal. Do not launch a replacement Docker/Compose deployment to fix a host-native issue.

“This GUI” in this chat means the DeepSeek Harness Web GUI, not the repository's bot dashboard. No implicit browser context is available. Do not change the harness or start a second web server unless that is the requested task.

## Sanity-check snapshot for this handoff

Observed on 2026-09-09, before this documentation change:

- Branch `pr/fixing_number_max_tool_calls`, HEAD `34f6580`; worktree clean.
- Attached session `152732.dame_curie`, window `0` named `bash`.
- Bot PID `2032244`, parent lock process `2032243`, cwd this checkout; one matching bot observed. These PIDs are observations, never reusable stop targets.
- `run.sh` activates `.venv` and execs `python3 bot.py`; observed executable `/usr/bin/python3.13`, venv reports 3.13.5. The newer documented container direction is Python 3.14; do not confuse it with an already completed host cutover.
- `AGENTS.md`, README and deployment docs exist, but lacked this shared-Screen workflow. README still reports temperature 0.7; AGENTS.md combines older baseline findings with newer repairs. Treat dated claims as historical and verify against current source.
- Newer commits supersede the interrupted provider-patch transcript. Do not resume its pending edits blindly. Consult the current tool-budget handoff and working changelog for active development.
- This documentation check did not read credentials/runtime data, contact live services, run application tests, or stop/restart the bot. Connection/provider health was not freshly tested.

### Paste into the next agent's chat

> Read AGENTS.md and docs/SCREEN_WORKFLOW.md in /home/codexy/Dame_Curie/Maxwell-bot. Re-check branch/diff and the existing dame_curie Screen session before acting. Root shares that terminal: join with screen -x, never detach root. Exactly one host bot, foreground under flock -n /tmp/dame-curie-maxwell.lock ./run.sh. Preserve current model/config and other agents' work; no secrets, live probes, or process-manager migration. Coordinate any restart, run scoped offline tests, commit the verified slice per AGENTS.md, and report exact runtime state and remaining work. Continue only the task root assigns next; old chat TODOs are not current authority.
