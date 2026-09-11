# Dame Curie — shared Screen and container operations

Read [STATUS.md](STATUS.md) for verified runtime state and [DOCKER.md](DOCKER.md) for the isolation boundary. Root authorized the host-native → private-rootless cutover. The existing `152732.dame_curie` session/window 0 is retained; no display was detached and no replacement session was created.

## Current process ownership

- Exactly one real identity: Compose project `maxwell-curie`, service user `maxwell-curie`, private engine `/run/user/1003/docker.sock`.
- The source-only operational checkout is `/opt/maxwell`. The development checkout remains `/home/codexy/Dame_Curie/Maxwell-bot`; do not run its legacy `./run.sh` alongside Compose.
- Screen runs the startup command and then follows Compose logs under the existing advisory `/tmp/dame-curie-maxwell.lock`. The bot itself runs in its rootless container, not as a host Python child of Screen.
- The lock discourages the old wrapped launch but is not a universal supervisor. Direct host Python execution bypasses it. Never delete the lock file or launch a second copy of these credentials/state.
- Rootless Docker uses its per-user systemd unit and lingering. Container restart policy, not Screen, owns recovery. Documentation-only changes do not require a reconnect.

The launched Screen command is:

```sh
flock -n /tmp/dame-curie-maxwell.lock bash -c 'sudo -n /usr/local/bin/python3.14 /opt/maxwell/scripts/instance.py curie up && exec sudo -n /usr/local/bin/python3.14 /opt/maxwell/scripts/instance.py curie logs'
```

`up` waits for configured service health; independently verify Discord/provider startup and the dashboard's fresh Discord snapshot. A successful `screen -X stuff` only proves input delivery.

## Join without displacing root

```sh
screen -ls
screen -x dame_curie
screen -S dame_curie -Q windows
```

| Keys | Effect |
| --- | --- |
| Ctrl-a d | Detach your display; containers and log follower continue |
| Ctrl-a [ | Enter scrollback; Esc exits |
| Ctrl-a 0 | Select existing window 0 |
| Ctrl-c | Stop the foreground log follower, **not the containerized bot** |

Do not use `screen -d -r`, kill the window/session, or type concurrently with another operator. Logs can contain private conversations; do not dump scrollback into chat/Git.

## Stop, start, restart

Use another terminal, or stop the log follower with Ctrl-c before typing in Screen:

```sh
sudo -n /usr/local/bin/python3.14 /opt/maxwell/scripts/instance.py curie stop
sudo -n /usr/local/bin/python3.14 /opt/maxwell/scripts/instance.py curie start
sudo -n /usr/local/bin/python3.14 /opt/maxwell/scripts/instance.py curie restart
```

- `stop` quiesces bot/API before owned shell/sites/web/Ollama; state and containers remain.
- `start` and `up` are exact aliases: same full Compose startup, including Ollama, same ownership/operation-lock checks, same health wait. Either works after `stop` or when dependencies are not running.
- `restart` reconnects **only bot/API** to reload private configuration; it does not start stopped Ollama/web dependencies. Do not use it to recover a fully stopped stack—use `up`. Coordinate it; autonomous work can resume.
- `down` also removes owned containers/networks, not persistent state or the model volume. Shell packages outside its mounted workspace are disposable.
- `logs` first replays the last 100 Compose log lines, including earlier process failures, then follows new output. Compare failures with current container start times and actual embedding probes before concluding a recovered service is still broken. Restore the wrapped log command above when appropriate; do not start another bot to restore visibility.

No host PM2 commands, rootful Docker fallback, direct host `python bot.py`, or duplicate deployments writing the same state. The wrapper verifies identity, private socket, source-path ownership labels and a per-instance operations lock. Do not mix it with concurrent direct Docker lifecycle commands.

## Dashboard and private files

Dashboard: `http://localhost:8081/admin/`, using the original dashboard username/password. Only loopback is published. For a remote host, forward it with `ssh -L 8081:127.0.0.1:8081 codexy@YOUR_HOST`.

- Private runtime configuration: `/srv/maxwell/curie/config/bot.env`.
- Live personality/server prompts: `/srv/maxwell/curie/config/prompts/`.
- Memory and runtime state: `/srv/maxwell/curie/data/`.
- Source-frozen application/web images: `maxwell-app:36e5eab`, `maxwell-web:01e8cbb`.
- Edit `/srv/maxwell/curie/config/bot.env`, not the development checkout `.env`, for live credentials/provider settings. Bot/API restart is required while dependencies are running; after a full stop use `start`/`up`. Rollouts preserve root's current settings; historical provider snapshots are not configuration authority. Save and close root-owned editors before state backup: unreadable swap files in this directory intentionally make the rootless backup fail; do not delete recovery files or weaken permissions to bypass this.
- Live `!reasoning`/`!effort` changes do not require restart. Current image profiles use the local proxy's private bridge address, not container loopback; see [image configuration and proxy recreation](CONFIGURATION.md#independent-normal-and-hd-image-configuration). No dashboard UI changes were part of this rollout.

Do not paste credentials, process environments, raw memory, or container environment arrays into diagnostics. Generated-site public URLs remain loopback-only until root configures an approved TLS origin.

## Rollback and history

The tested same-identity restore procedure is in [DOCKER.md](DOCKER.md#backup-and-restore). It requires all owned containers removed and four **empty** target state directories; never overwrite a running/nonempty target. Reapply mapped-site ACLs and verify health after restoration.

The deferred incident rollout exposed one existing external interpreter symlink. Its raw `/srv/maxwell-backups/curie/pre-incidents-e306a22.tar` is preserved but **does not pass the standard restorer's validation**; the old build was restarted without restoring any data. For a compatibility snapshot, retain raw archive, strict derived tar, companion metadata and tested adapter together. Follow the [exact interpreter-link procedure](DOCKER.md#exact-interpreter-link-compatibility), including pair validation and link reconstruction only after complete extraction. Never treat the derived tar alone as a full backup, delete the live link, or restore an older snapshot over current state. See STATUS for the actual latest cutover and fresh backup evidence.

- Latest pre-formatting-rollout state: `/srv/maxwell-backups/curie/pre-formatting-36e5eab.tar`; private prior config/control/source: `/srv/maxwell-rollback/curie/formatting-36e5eab/`. Prior working app `36122a4` is retained. This rollout changed no private settings; preserve the currently authorized settings and credentials during any rollback.
- Earlier pre-capability-rollout state: `/srv/maxwell-backups/curie/pre-capabilities-36122a4.tar`; private prior config/control/source: `/srv/maxwell-rollback/curie/capabilities-36122a4/`. Prior app `677d2e4` is retained. Keep `usage` disabled when reverting to that old implementation: it sends the chat key to an unrelated gateway. Never restore a superseded key after root rotates credentials; use the current ledger and an explicitly reviewed rollback.
- Earlier image-repair state: `/srv/maxwell-backups/curie/pre-images-677d2e4.tar`, with private `/srv/maxwell-rollback/curie/images-677d2e4/`. The older `99fd7fa` image additionally requires HD disabled because of its unsafe image routing/retry behavior.
- Historical pre-login state: `/srv/maxwell-backups/curie/pre-login-01e8cbb.tar` (mode 0600, credentials included).
- Original private state/config and starting source: `/srv/maxwell-rollback/curie/pre-cutover/` (root-only). Deployment image/settings are recorded separately there because normal state backups exclude `deploy.env`.
- Original host data, configuration and Python 3.13.5 venv remain in place. Do **not** run the new Python 3.14 source with that old venv. A host-native rollback requires deliberately restoring the matching archived source after stopping Compose; it is not an automatic fallback.
- The complete previous Screen contract and dated PIDs remain in Git at `96b4803:docs/SCREEN_WORKFLOW.md`. Those PIDs are historical, never stop targets.

Development and application tests stay in source-only isolated checkouts with private-read/network barriers. Always exclude the credential-reading live progress test. No test Discord/email/X/CAPTCHA actions were sent during this rollout.
