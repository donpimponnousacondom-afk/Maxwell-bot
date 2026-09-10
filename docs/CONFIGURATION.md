# Maxwell configuration quick reference

The installer writes `.env` from `.env.example` and updates only the keys it asks about. Keep `.env` private; it is ignored by git.

## Values set by the wizard

| Variable | Required? | Purpose |
|---|---:|---|
| `DISCORD_TOKEN` | Yes | Discord **user** token for the self-bot account. Treat it like a password. |
| `OLLAMA_BASE_URL` | Yes | OpenAI-compatible base URL. A bare host such as `http://localhost:11434` gets `/v1` appended by the provider code. |
| `OLLAMA_MODEL` | Yes | Chat model name served by that endpoint. |
| `OLLAMA_API_KEY` | Sometimes | ****** for hosted providers such as OpenRouter or OpenAI; blank is normal for local Ollama/LM Studio. |
| `MAXWELL_OWNER_IDS` | Strongly recommended | Comma-separated Discord user IDs allowed to run admin commands. Blank means admin commands are denied to everyone. |
| `MAXWELL_ADMIN_USER` | Optional | Admin username for dashboard/API auth (defaults to `admin`). |
| `MAXWELL_ADMIN_PASSWORD` | Strongly recommended | Password for the admin API/dashboard. Blank makes the API return 503. |
| `ENABLE_AUTONOMY` | Optional | Timed self-directed background actions; off by default to avoid surprise token spend. |
| `ENABLE_REM` | Optional | Timed memory consolidation (also accepted as `REM_ENABLED`); off by default to avoid surprise token spend. |
| `ENABLE_SHELL` | Optional | Shell tool. Requires Docker; the installer disables it when Docker is unavailable. |

See [`.env.example`](../.env.example) for the full set of advanced knobs, including embeddings, dashboard host/port, TTS, X/Twitter, email, captcha solving, and tool-specific limits.

## Compartmentalized deployment and RAG

The host-native installer above is not the rootless deployment manager. See [DOCKER.md](DOCKER.md) for private per-identity bot/API/web/Ollama services and [STATUS.md](STATUS.md) for current acceptance evidence. Container configuration lives in private `/srv/maxwell/<id>/config/bot.env`; environment changes require bot/API restart, whereas supported external prompt edits reload live.

Chat and embedding configuration are independent. Keep the existing chat `OLLAMA_BASE_URL`, model and API key when enabling the private embedder:

```ini
ENABLE_RAG=true
MAXWELL_EMBED_BASE_URL=http://ollama:11434
MAXWELL_EMBED_MODEL=qwen3-embedding:0.6b
MAXWELL_EMBED_DIM=1024
MAXWELL_EMBED_API_KEY=
```

Those DNS names apply inside the instance, not to host-native Python. Ollama has no published host port; only the instance bot/API network can reach its runtime. The separate initialization container downloads the model, then exits. The persistent model volume survives normal `down`, but is a re-downloadable cache, not a memory backup.

Vectors and the durable embedding cache are tagged by endpoint/model/dimension/input-derivation identity. Legacy untagged vectors, other backends and malformed vectors are excluded from semantic retrieval, **without deleting raw memory**. Changing the model or endpoint requires explicit re-embedding; never label existing vectors as if they came from the new model. Merely renaming a model does not prove its weights are unchanged.

`rag_maintenance.py status --db /state/data/maxwell_rag.db` reports counts only. `backfill --db /state/data/maxwell_rag.db --limit 100 --batch-size 4 --max-seconds 60` performs a bounded resumable pass using the same validated client. Invoke these inside the matching configured application image, not an unrelated host venv. `eligible_pending == 0` means all eligible rows are complete; raw `pending` also includes intentionally excluded empty/low-signal events. `ENABLE_RAG=false` sends no embedding requests. The legacy `MAXWELL_EMBED_PENDING_ON_BOOT=true` hook performs one bounded pass, not an unlimited startup migration.

Run `doctor.py --probe` only when live provider requests are intended: it probes chat as well as embeddings. Its embedding check requires a correctly sized finite nonzero vector, not merely HTTP 200. For embedding-only acceptance use the explicit maintenance path or deployment readiness check instead.

## Common provider snippets

```ini
# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_API_KEY=
```

```ini
# OpenRouter
OLLAMA_BASE_URL=https://openrouter.ai/api/v1
OLLAMA_MODEL=moonshotai/kimi-k2.6:free
OLLAMA_API_KEY=your-openrouter-key
```

```ini
# OpenAI
OLLAMA_BASE_URL=https://api.openai.com/v1
OLLAMA_MODEL=gpt-4.1-mini
OLLAMA_API_KEY=your-openai-key
```

```ini
# LM Studio
OLLAMA_BASE_URL=http://localhost:1234/v1
OLLAMA_MODEL=the-loaded-model-name
OLLAMA_API_KEY=
```

## Custom request options and OpenRouter routing

`OLLAMA_EXTRA_BODY` and `OLLAMA_EXTRA_HEADERS` accept JSON objects, defaulting to `{}`. Header values must be strings. Invalid JSON/non-object values stop startup rather than silently dropping routing restrictions. These options require an application image built from the updated source and a bot restart; changing only the production `.env` does not update an older image.

For per-request DeepInfra routing without account/workspace-wide provider changes:

```ini
OLLAMA_BASE_URL=https://openrouter.ai/api/v1
OLLAMA_MODEL=openai/gpt-oss-120b:nitro
OLLAMA_DISABLE_REASONING=false
OLLAMA_EXTRA_BODY='{"provider":{"only":["deepinfra"]}}'
OLLAMA_EXTRA_HEADERS={}
```

Keep the existing OpenRouter key in `OLLAMA_API_KEY`. Provider selection is a **body** field, not a header. Availability and account-level restrictions still apply; `only` does not override them. See [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection). The base slug `deepinfra` allows its variants; use `deepinfra/turbo` to target that endpoint specifically. `:nitro` prioritizes throughput among eligible endpoints; it is not itself a provider pin.

To request an explicit reasoning effort, add it to the same object, for example `OLLAMA_EXTRA_BODY='{"provider":{"only":["deepinfra"]},"reasoning":{"effort":"high"}}'`. This is opt-in: `OLLAMA_DISABLE_REASONING=false` alone sends no effort level and leaves the model/provider default unchanged. Explicit per-call disabling (including auxiliary calls) takes precedence over custom reasoning fields. Supported effort levels depend on the selected model/provider; see [OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

For OpenRouter app attribution, set HTTP **headers**, not body fields:

```ini
OLLAMA_EXTRA_HEADERS='{"HTTP-Referer":"https://council.zombiedawn.net/","X-OpenRouter-Title":"Dame Curie: Always Teasing"}'
```

`HTTP-Referer` is the app's URL/unique identifier; `X-OpenRouter-Title` sets its display name. OpenRouter still accepts `X-Title`, but the title alone does not create an app entry. Attribution opts the app into public rankings/analytics; see [OpenRouter app attribution](https://openrouter.ai/docs/app-attribution). Use your own app URL/title for another identity.

Merge these into any existing `OLLAMA_EXTRA_HEADERS` object; leave `OLLAMA_EXTRA_BODY`, routing, model and credentials unchanged. The configured API key takes precedence over any case variant of `Authorization`. For the current Curie deployment, edit private `/srv/maxwell/curie/config/bot.env`, not the development checkout `.env`, then coordinate a bot/API `restart` through the [instance operator](SCREEN_WORKFLOW.md#stop-start-restart). The deployed image already supports these options; no image rebuild is needed.

Scope and precedence:

- Options apply only to the main client's **primary endpoint**, including background/auxiliary calls that reuse that client and primary model overrides. They are not inherited by fallback, vision, or separately constructed autonomy/auxiliary clients—even on the same host. OpenRouter's `provider.only` does not disable Maxwell's separately configured fallback endpoint.
- Runtime-owned `model`, `messages`, `temperature`, `top_p`, `top_k`, `max_tokens`, `stream`, `stream_options`, `tools` and `tool_choice` take precedence. Use their existing configuration/call arguments rather than extra-body overrides.
- Each request gets its own copy of the extra body, preserving configured routing through retries without sharing mutable nested state. Existing retry/streaming/telemetry behavior remains authoritative.
- Headers can contain credentials: keep them in private instance configuration, never source control or public files. Clear endpoint-specific options when changing the main endpoint.

## Independent HD image configuration

`hd_image` uses only `GEMINI_IMAGE_BASE_URL`, `GEMINI_IMAGE_API_KEY`, and `GEMINI_IMAGE_MODEL`. It never inherits `OLLAMA_*` chat configuration, credentials, routing options or model. A blank dedicated base URL returns a configuration error before fetching input images or making any generation request. A blank dedicated key sends no Authorization header, allowing explicitly configured keyless gateways. Merely adding a paid chat key must not enable paid HD image generation.

```ini
GEMINI_IMAGE_BASE_URL=
GEMINI_IMAGE_API_KEY=
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image
```

Set the base/key/model for the image provider you deliberately choose. The current adapter expects an OpenAI-compatible `/chat/completions` endpoint returning base64 `data:image` URIs in `message.content` (text or image-url parts) or `message.images[].image_url.url`; it does **not** implement native GPT Images `/images/generations` or `/images/edits`. Each tool invocation submits generation once: empty/unrecognized responses, timeouts and server errors do not trigger a second potentially billable request. This is not a cross-invocation deduplication policy. A compatible gateway is required for other image backends. The separate Pollinations `image_generator` is unchanged.

Both tools remain registered under `ENABLE_IMAGE_GEN`; dashboard Runtime controls → Tools can disable `hd_image` independently. The no-inheritance behavior requires the updated application image, not only an environment edit. See [STATUS.md](STATUS.md) for deployed versus source-only state.

## Provider retries

`OLLAMA_RETRY_ATTEMPTS` defaults to **5 total attempts** (range 1–10), not five retries. Explicit environment values override this default. Transient failures wait **10, 20, 30, 40 seconds** before attempts 2–5; the delay is linear and also applies when switching endpoints. Deterministic request rejection/failover and corrected-payload retries do not use this backoff, but still consume the fixed attempt budget.

With a fallback configured, ordinary routing uses the primary for attempts 1–2 and the fallback for later attempts; endpoint cooldown and caller-requested fast/preferred fallback still apply. Fast fallback retains its shorter two-attempt budget. `OLLAMA_EMPTY_RESPONSE_RETRIES` (default 2) reserves up to that many remaining attempts for non-streaming empty-content recovery; it never increases the total budget. Caller-specific deadlines remain unchanged and may cancel a request before all attempts and the default 100 seconds of backoff finish.

Recognized JSON/+json and SSE response Content-Types determine HTTP 200 decoding; missing or other types retain requested-format parsing for gateway compatibility. Explicit JSON/SSE error envelopes fail even after partial output; diagnostics contain allowlisted error code/type, a message-derived category, and numeric framing information, never raw error bodies or message previews. Unknown error labels are reported as unknown. Unterminated SSE tails fail instead of silently losing output. Malformed JSON frames remain skippable with numeric diagnostics; this is not a full SSE framing rewrite.

## Per-call provider measurements

`!debug` (or the configured command prefix) shows the running client's loaded primary/fallback model and provider hostname before its process-local measured-reply section. No completion or provider probe is needed to inspect the loaded configuration. This is not a reread of edited environment files or a guarantee of the next request's route: fallback and per-call overrides can differ. Measurements still belong to their original response and disappear when the process restarts. The debug report uses fenced code blocks without an unmeasured TTFT/TPS footer; endpoint credentials, paths, query strings and raw request options are not displayed. Requires the updated image; see [STATUS.md](STATUS.md).

Streaming requests send `stream_options: {"include_usage": true}`. An explicit unsupported-option HTTP 400/422 teaches that endpoint to omit the option for this process. A corrected request stays on that endpoint and consumes a remaining attempt; it never adds an attempt or overrides the five-attempt ceiling. Non-streaming requests omit the option.

Measurements travel with the returned response, not a shared provider's last-call record:

- **TPS** is generated output tokens, including reasoning, divided by the **successful HTTP attempt's full elapsed seconds**, consistently for SSE and JSON. This is end-to-end request throughput, not server-side decode speed or a short arrival-burst rate. Failed attempts, backoff, other tool-loop calls and unrelated requests are not accumulated into this sample; the successful attempt number is retained.
- **TTFT** starts when that request is sent and ends at its first observed generated text, reasoning, tool name or arguments. Roles, IDs, usage-only frames and opaque signatures do not start it. JSON/non-streaming cannot reveal first-token arrival: total response time is used as an explicitly estimated proxy. Parsing uses actual recognized response Content-Type rather than assuming the requested stream mode.
- **Reported counts win.** Canonical OpenAI completion/output totals already include their reasoning breakdown; it is not added twice. Known separately reported Gemini candidate/thought counts, Ollama count aliases and consistent reported total-minus-input counts are recognized. Partial SSE usage trailers preserve earlier valid fields; later valid corrections replace rather than accumulate counts. An output count of zero despite observed generated output is treated as an unavailable placeholder, not a fabricated zero-throughput measurement.
- **Missing counts use fixed CL100K estimates**, with pinned `tiktoken` and the verified local vocabulary in `assets/tokenizers/`. No tokenizer network download occurs during inference. Reasoning promoted into an answer and parsed custom-tool JSON are counted only once. If only reasoning is reported, visible output is estimated separately and provenance is marked mixed. Unreported hidden reasoning remains unknown.
- Estimated input uses compact JSON framing for textual messages and tool schemas. It is a comparable local approximation, not the model's exact chat template; structured media payloads and opaque signatures are excluded, so unreported media token costs remain unknown. Input counts mean tokens for this request, not context-window capacity.

Required tokenizer dependencies and vocabulary must be installed together. The local tokenizer is initialized before generation, so a missing or corrupt required asset fails before a paid request rather than retrying an otherwise successful completion.

## Reconfigure

From a cloned checkout:

```bash
./install.sh --local --reconfigure
```

Or, for an existing install made by the one-liner:

```bash
cd ~/maxwell
./install.sh --local --reconfigure
```
