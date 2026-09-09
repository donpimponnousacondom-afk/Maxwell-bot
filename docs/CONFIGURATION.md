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

## Provider retries

`OLLAMA_RETRY_ATTEMPTS` defaults to **5 total attempts** (range 1–10), not five retries. Explicit environment values override this default. Transient failures wait **10, 20, 30, 40 seconds** before attempts 2–5; the delay is linear and also applies when switching endpoints. Deterministic request rejection/failover and corrected-payload retries do not use this backoff, but still consume the fixed attempt budget.

With a fallback configured, ordinary routing uses the primary for attempts 1–2 and the fallback for later attempts; endpoint cooldown and caller-requested fast/preferred fallback still apply. Fast fallback retains its shorter two-attempt budget. `OLLAMA_EMPTY_RESPONSE_RETRIES` (default 2) reserves up to that many remaining attempts for non-streaming empty-content recovery; it never increases the total budget. Caller-specific deadlines remain unchanged and may cancel a request before all attempts and the default 100 seconds of backoff finish.

Recognized JSON/+json and SSE response Content-Types determine HTTP 200 decoding; missing or other types retain requested-format parsing for gateway compatibility. Explicit JSON/SSE error envelopes fail even after partial output; diagnostics contain allowlisted error code/type, a message-derived category, and numeric framing information, never raw error bodies or message previews. Unknown error labels are reported as unknown. Unterminated SSE tails fail instead of silently losing output. Malformed JSON frames remain skippable with numeric diagnostics; this is not a full SSE framing rewrite.

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
