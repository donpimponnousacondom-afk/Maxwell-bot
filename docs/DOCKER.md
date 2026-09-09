# Per-instance rootless Docker deployment

## Boundary and current verification

See [STATUS.md](STATUS.md) for dated implementation, test and deployment evidence. This guide describes the target and commands; it does not by itself certify a deployed stack. Root has authorized the current rollout recorded there.

One Linux service user and **one private rootless Docker engine per bot identity**. Each engine runs bot, API, static web, the shell sandbox, and generated-site backends. Root in an application container is the service user's rootless identity, not host root. The private Docker socket still gives application code authority over that service user's files and containers: do not share an engine, account, supplementary groups, or writable paths between identities.

This deployment does not enable full-host shell access or runtime source mutation. Images are read-only; shell workspace, prompts, memory, and generated sites are writable. The shell container filesystem is disposable: `stop` preserves it; `down` removes it. Put durable shell output in `/home/maxwell`.

Offline tests are available. Private-daemon lifecycle, ACL inheritance, actual image builds, network reachability, and backup/restore against a live rootless engine still require host acceptance testing. Do not interpret Python dependency installation as a successful Docker build. Base image tags and apt repositories are not digest/snapshot pinned; builds are not fully reproducible.

## Layout

```text
/srv/maxwell/curie/                 owner maxwell-curie, mode 0700
  deploy.env                        operator deployment settings, mode 0600
  config/
    bot.env                         credentials/environment, mode 0600
    prompts/                        writable prompt overrides
  data/                             SQLite, JSON controls, plugin state, site registries/code/data
  sites/                            public generated pages and images
  shell/                            durable /home/maxwell workspace
```

`deploy.env` contains only `INSTANCE_ID`, `INSTANCE_DIR`, `ENGINE_SOCKET`, `APP_IMAGE`, `WEB_IMAGE`, and `WEB_PORT`. Use unquoted literal values. It is parsed, never sourced. `config/bot.env` is loaded by Python; the operations wrapper never reads it. Do not bake credentials or runtime files into images.

Bot and API share one private data directory: communication is SQLite WAL plus JSON controls and a command queue, not a network RPC. Never scale multiple bots against that directory. The whole directory must remain writable, including atomic-rename temporary files, lock files, SQLite WAL, and SHM. Do not bind individual database/JSON files.

The config directory is mounted read-only with the `config/prompts` subtree mounted writable. API/runtime controls remain in `data/bot_control.json`; API and tools can edit supported prompts. Writable prompts do not imply an API for editing environment secrets. Environment changes take effect on bot/API restart. The source defaults remain in the image; use the configured prompt override mechanism instead of bind-mounting source code.

Generated-site state and plugin/email/X state live under `data`; generated public pages and permanent images live under `sites`. Voice scratch uses tmpfs at `/app/temp`; other scratch uses `/tmp`. Container logs use Docker's bounded local log driver. Neither scratch nor logs are included in state backups.

## Host prerequisites and provisioning

The wrapper needs host Python 3.14, the Docker CLI with Compose v2, and a separately configured rootless Docker daemon for each account. It requires `docker info` to report rootless security options at the expected socket and rejects even exit-zero results with stderr diagnostics. It never falls back to `/var/run/docker.sock`.

For Debian-family hosts, after configuring Docker's official package repository for the host distribution, install the rootless/Compose dependencies as host root:

```sh
apt-get install docker-ce-cli docker-ce-rootless-extras docker-compose-plugin uidmap dbus-user-session slirp4netns fuse-overlayfs acl
useradd --create-home --shell /bin/bash maxwell-curie
loginctl enable-linger maxwell-curie
install -d -o root -g root -m 0755 /srv/maxwell
install -d -o maxwell-curie -g maxwell-curie -m 0700 /srv/maxwell/curie
install -d -o maxwell-curie -g maxwell-curie -m 0700 \
  /srv/maxwell/curie/config /srv/maxwell/curie/config/prompts \
  /srv/maxwell/curie/data /srv/maxwell/curie/sites /srv/maxwell/curie/shell
```

Check `/etc/subuid` and `/etc/subgid`: each account needs distinct, non-overlapping ranges sufficient to map container UID/GID 10001. Do not add these accounts to the host `docker` group. Give each account read access to the immutable deployment checkout and no write access to it; a checkout beneath another user's private home will not work.

Log in as `maxwell-curie` with its systemd user session (`XDG_RUNTIME_DIR=/run/user/$(id -u)`), then:

```sh
dockerd-rootless-setuptool.sh install
systemctl --user enable --now docker
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
docker info --format '{{json .}}'
docker compose version
```

Inspect stdout **and stderr**. Resolve rootless networking/cgroup warnings deliberately rather than switching to a rootful daemon. A user login is preferable to ad-hoc `sudo` environment inheritance; verify the lingering user service survives logout.

Copy `docker/deploy.env.example` and `docker/bot.env.example` into the indicated locations as that service user, using mode 0600. Set the actual UID in `ENGINE_SOCKET`, unique loopback `WEB_PORT`, versioned image names, distinct Discord credentials, public origin, and selected provider settings. Keep `MAXWELL_SHELL_FULL_HOST=false`. Localhost inside a container is not the host's embedding, SMTP, or IMAP service: configure reachable endpoints and firewall them deliberately. Separate Telegram polling tokens as well.

### Editable prompts

Before the first `up`, create a nonempty UTF-8 `config/prompts/personality.txt` as the instance service user. This is required when `MAXWELL_PROMPTS_DIR` is configured. Optionally create `config/prompts/servers.json` containing `{}`; server IDs (or `DM`) map to prompt strings. Edit these with your normal host editor, or use the existing dashboard/Discord prompt controls. Changes are read on subsequent prompt construction; no image rebuild is needed. Save host edits atomically and avoid simultaneous edits to the same prompt.

The external files override legacy personality/server-prompt fields in `data/`; legacy fields are not an alternative configuration source. Malformed edits are rejected by API writes, while a running bot retains its last valid prompt. Prompt-tool permissions are unchanged: existing non-admin-accessible personality tools can still edit writable prompts. This is not a new owner-only authorization boundary.

### Generated-site UID 10001

Site backends run as container UID/GID 10001, while application files originate from rootless UID 0. Host permissions must account for that mapping. For the standard mapping where container UID 0 maps to the service user and UIDs 1 onward map to the first subordinate range, container UID 10001 maps to `subuid_start + 10000`. Confirm the actual mapping first; do not apply that arithmetic to a custom mapping blindly.

As host root, set `SITE_UID` to that verified mapped host UID, then grant narrowly scoped ACLs:

```sh
# Substitute the verified numeric host UID, not literal container UID 10001.
SITE_UID=REPLACE_WITH_MAPPED_HOST_UID
setfacl -m "u:${SITE_UID}:--x" /srv/maxwell/curie /srv/maxwell/curie/data
install -d -o maxwell-curie -g maxwell-curie -m 0700 /srv/maxwell/curie/data/site_servers
setfacl -m "u:${SITE_UID}:rwx,d:u:${SITE_UID}:rwx,d:u::rwx,d:g::---,d:m::rwx,d:o::---" \
  /srv/maxwell/curie/data/site_servers
```

The inheritable `rwx` entry allows newly created `_data` directories to work without an application `chown`. Backend code mounts are **read-only**, so this host ACL does not make `/app` writable inside a backend. Do not grant access to config, the Docker socket, other identities, or the whole host. Existing migrated/restored directories need corresponding ACLs reapplied: tar backups preserve numeric ownership, not ACLs. Test a newly created backend can read code and write `/data` before enabling site creation. Do not solve failures with recursive world-writable chmod.

## Images and services

Build into each user's private engine, or pull reviewed versioned images from a registry. Run these from the immutable checkout as the service user with its explicit `DOCKER_HOST`:

```sh
docker build -f docker/app.Dockerfile --target app -t maxwell-app:RELEASE .
docker build -f docker/app.Dockerfile --target web -t maxwell-web:RELEASE .
```

The application target includes full optional packages and system dependencies: voice/audio, Riva, search, YouTube/JS support, Chromium/site rendering, Stockfish, and the Docker CLI. `docker/requirements.lock` is installed with `--no-deps` intentionally: voice-recv metadata requests `discord-py`, but this project uses the `discord.py-self` backend occupying the same imports. Installing the upstream dependency alongside it would overwrite that backend. Preserve the reviewed lock; do not resolve the metadata conflict by installing both distributions. A clean Python 3.14 optional-dependency install/import verification is a separate check from building/running this image.

`docker/Dockerfile` is the **shell sandbox image**, not the bot image. Generated-site runtime images are built separately by the running tool. First use therefore needs the private daemon, network access for builds, and available image dependencies.

The static dashboard is `web/admin/index.html`, with inline CSS/JS and same-origin API calls. It has no Node/Vite frontend build. Caddy serves it and the public `sites` subtree, proxies `/api/*` and allowlisted `/data/*` through authenticated API handlers, and routes site `/bot/<slug>/api/*` to the API proxy. Never expose the data/config directories through a generic static file server. The web container has neither the private Docker socket nor private data/config mounts.

A host TLS reverse proxy should forward each identity's domain to its own loopback `WEB_PORT`. Keep the bot API and generated backend ports unpublished; backends communicate through the instance-specific Docker network. Configure public URL, CORS origin, and OAuth callback for the correct instance. Do not expose an unauthenticated proxy path around the API.

## Operations

Run the wrapper as host root or as the corresponding service user. Root drops to `maxwell-<id>` before reading deployment settings or contacting Docker. Absolute Compose paths, a fixed project name, a clean environment, and `--env-file /dev/null` prevent accidental checkout `.env` loading.

```sh
./scripts/instance.sh curie up
./scripts/instance.sh curie logs
./scripts/instance.sh curie restart
./scripts/instance.sh curie stop
./scripts/instance.sh curie down
```

- `up`: create/start the Compose services; runtime reconciles owned backends.
- `restart`: restart bot and API to reload config, without replacing the images.
- `logs`: follow the last 100 lines of Compose logs; logs may contain private conversations.
- `stop`: stop bot/API first, then managed shell/site containers and web; retain containers and state.
- `down`: stop all writers, remove owned managed shell/site containers, then tear down Compose. Persistent directories survive. **Shell-installed packages outside `/home/maxwell` do not.**

Ownership checks require the expected Compose project/config-file labels or `maxwell.instance=<id>` plus `maxwell.kind=shell|site`. Foreign/mislabelled matching names fail closed. An abandoned backup helper likewise requires explicit operator inspection rather than automatic deletion. Do not run independent Docker lifecycle commands concurrently with the wrapper: its lock coordinates wrapper invocations, not external operators or daemon restart policies.

The dashboard's host PM2 management is not the container supervisor. Use this wrapper rather than exposing host PM2 control or giving the API a rootful Docker socket.

## Backup and restore

Create a private backup directory outside the instance root, owned by the service user. An archive contains credentials and private conversations; encrypt/store it accordingly. These commands are operator-invoked; development/test runs must not open real state.

```sh
./scripts/instance.sh curie backup /srv/maxwell-backups/curie-2026-09-06.tar
./scripts/instance.sh curie restore /srv/maxwell-backups/curie-2026-09-06.tar
```

Backup refuses existing archive paths, creates mode 0600, stops every previously running writer, streams only `config/`, `data/`, `sites/`, and `shell/`, then attempts to restart exactly the previously running containers even if archiving fails. Incomplete archives are removed. It excludes `deploy.env`, Docker image/container storage, logs, and tmpfs. Keep versioned image references and deployment settings separately. Stopped services remain stopped.

A helper in the **same rootless engine** creates/extracts the tar so numeric ownership is represented in container coordinates, not the host subordinate-ID range. Restore checks owners against the destination rootless mapping and uses Python's tarfile data filter while retaining those numeric owners. No broad host chown is needed. ACLs/xattrs are not archived and must be provisioned again.

Restore currently supports only a **fresh, stopped target with the same instance ID**, no owned containers, and all four state directories empty. `deploy.env` must already exist outside those directories, and the configured app image must be available in the destination engine. Archives carry an identity header; cross-identity clones require explicit registry/config migration and are rejected. Restore never starts services automatically and never overwrites nonempty state. Failed extraction may leave partial state; inspect it before deliberately recreating the empty target.

Restore rejects traversal, absolute paths, special files, duplicate names, escaping links, and entries beneath links. Confined links inside one state root are supported. A shell workspace containing external/absolute symlinks cannot be restored by this limited command; remove/recreate those links explicitly rather than weakening the filter. Stop all old-instance processes before restoring another copy of the same bot credentials.

### Offline migration from host/PM2

Stop the old bot, API, site backends, and shell writers yourself, and keep the target daemon stopped. As the target service user, prepare empty `data`, `sites`, `shell`, and `config/prompts` directories plus a separately configured `config/bot.env`, then run:

```sh
python3.14 scripts/migrate_instance.py curie \
  --data /absolute/old-data --sites /absolute/old-sites \
  --shell /absolute/old-shell --stopped
```

`--stopped` is your acknowledgement, not process detection. The command refuses overlapping paths, nonempty destinations, source symlinks/special files, environment files in the selected roots, and malformed prompt/registry JSON. It never reads or copies `bot.env` or source `.env`; supply the target token/provider configuration yourself. It copies the complete data directory consistently only because all source writers are stopped, separates legacy personality/server prompts into the external store, and converts legacy site registry names/network metadata to this identity. Previously running backends are recreated by startup reconciliation; deliberately stopped ones remain stopped. The source is untouched.

Migration creates files owned by the invoking service user, not raw source subordinate UIDs. **Reapply the site ACLs before starting**: grant the mapped UID traversal on instance/data, recursive `rwX` only under `data/site_servers`, and inheritable defaults on each directory there. Do not prepopulate `data/site_servers` before migration, because the destination must be empty. For inherited ACLs during the copy, temporarily establish defaults on the empty target `data` directory; remove those root defaults afterward and retain the narrower site-server defaults. Backends' code binds remain read-only.

Normal exceptions roll back published target files. A kill or power loss is not a transaction across all four roots: inspect and explicitly clear an incomplete destination before retrying. Do not migrate a live tree. This command accepts legacy unversioned registries, not arbitrary cloning of an existing version-2 deployment.

## Acceptance checklist

1. Offline tests pass; inspect the image source allowlist and verify no runtime/secret files enter build contexts.
2. Each service user sees only its own rootless engine; another user's socket/state is inaccessible.
3. Build/pull app and web images; record tags/digests and verify optional feature imports in the image.
4. Start one test identity; verify health, dashboard auth, prompt editing, model configuration reload, and voice scratch without real-channel side effects.
5. Create a test shell workspace and site backend; confirm source read-only, `/data` writable, per-instance networking, and ownership labels.
6. Verify `stop`, `restart`, and `down` semantics; verify a second identity is untouched.
7. Backup test state with a UID10001-owned file; restore into a fresh same-ID test target, reapply ACLs, and compare numeric ownership and contents before using real state.

No live-daemon acceptance result is implied by this checklist.
