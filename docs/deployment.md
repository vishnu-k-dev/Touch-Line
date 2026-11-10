# Deployment: Render (API + database) and Vercel (web)

Everything here has been exercised locally in Docker. The hosted steps need your own Render, Vercel and OpenAI accounts, so
they have **not been run from this repository**; the files they use (`render.yaml`, `apps/web/vercel.json`, both Dockerfiles)
are the ones the local Docker stack runs.

## 0. Before you start

- Push the repository to GitHub (both services deploy from it).
- Have an OpenAI API key ready.
- Render plans and prices change; the plan ids in `render.yaml` come from Render's blueprint docs. Check current prices before
  you apply it.

## 1. Render: database and API

1. Render dashboard → **New → Blueprint** → select the repository. Render reads `render.yaml` and proposes:
   - a Postgres database `touchline-db` (pgvector is supported on Postgres 13+; the API runs `CREATE EXTENSION vector` itself), and
   - a Docker web service `touchline-api` (build context = repo root, Dockerfile `apps/api/Dockerfile`).
2. When asked for the values marked `sync: false`:
   - `LLM_API_KEY`: your OpenAI key.
   - `CORS_ORIGINS`: leave a placeholder for now (you will set it in step 3).
3. Apply. The first start takes a few minutes: the container waits for the database, runs the Alembic migrations, downloads
   the StatsBomb files, loads the five matches and builds the search index. After that, restarts skip all of it. Render's
   health check (`/health/ready`) turns green when it is done.
4. Note the API URL, e.g. `https://touchline-api.onrender.com`.

**Memory.** The first boot builds the search index (156 documents). Measured in Docker with a hard 512 MB limit: peak
about 401 MiB (sampled every 3 s) and about 105 MiB once serving, 278 MiB after 40 concurrent requests; no OOM kill. That
fits Render's 512 MB free plan but with thin headroom (the first boot took about 4 minutes on a laptop, and the free plan
sleeps when idle). If a deploy still reports "Out of memory", use the `1c-2g` plan in `render.yaml`. The first version of
the index build ran out of memory on 512 MB; it now loads light event rows, fetches raw JSON only for shots, and embeds in
batches of 16.

`DATABASE_URL` is wired from the database automatically. Render hands out `postgresql://` URLs; the API rewrites them to
`postgresql+psycopg://` (tested), so nothing to edit.

## 2. Vercel: the web app

1. Vercel → **Add New → Project** → import the same repository.
2. **Root Directory: `apps/web`**. The framework is detected as Next.js (`vercel.json` pins the commands).
3. Environment variable (Production **and** Preview): `NEXT_PUBLIC_API_URL = https://<your-api>.onrender.com`.
   It is compiled into the browser bundle, so redeploy after changing it.
4. Deploy and note the site URL, e.g. `https://touchline-ai.vercel.app`.

## 3. Close the loop (CORS)

In Render → `touchline-api` → Environment, set `CORS_ORIGINS` to the Vercel URL (comma-separate several). For Vercel
preview deployments, optionally set `CORS_ORIGIN_REGEX`, e.g. `https://touchline-ai-.*[.]vercel[.]app`. Saving redeploys the API.

## 4. Check it works

| Check | Expect |
|---|---|
| `https://<api>/health/ready` | `{"status":"ready","matches":5,"documents":156,...}` |
| `https://<api>/api/v1/analyst/status` | `"configured": true, "provider": "openai", "model": "gpt-5.6-luna"` |
| The Vercel site | tickets with xG badges; the header shows "VAR room open" |
| Ask the analyst a question, then **reload** | The question and answer are still there ("Picked up where you left off") |

## Chat history (it persists)

Each question and its full answer are stored in Postgres (`chat_turns`), keyed by a random anonymous id the browser keeps in
`localStorage` and sends as `X-Visitor-Id`. It is not an account and holds no personal data. Consequences:

- History survives reloads, switching matches, deploys and restarts, because it lives in the database.
- It follows the browser, not the person: clearing site data or using another browser starts a fresh history (the old rows
  stay in the database until their owner's cap trims them: 100 per visitor).
- "Clear history" on the analyst tab deletes that visitor's rows for the match.

## API environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (set by Render from the database) |
| `LLM_API_KEY` (or `OPENAI_API_KEY`) | OpenAI key for the analyst. Unset = the dashboards work, the analyst answers 503 |
| `LLM_PROVIDER` | `openai` (default) or `anthropic` |
| `LLM_MODEL` | Default `gpt-5.6-luna` ($0.20 / $1.20 per million input / output tokens). `gpt-5.6-terra` is the quality upgrade at about 10x the price. Compare with the eval |
| `LLM_EFFORT` | Reasoning effort. Empty = provider default (`none` for OpenAI: its Chat Completions endpoint rejects reasoning together with function tools) |
| `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | Browser origins allowed to call the API |
| `TRUST_PROXY` | `true` behind a proxy so rate limits see the real client address (set in `render.yaml`) |
| `ANALYST_DAILY_BUDGET_USD` | Global daily spend cap for the analyst (`render.yaml` sets 5). At the cap the endpoint answers 503 until the next UTC day |
| `ANALYST_RATE_PER_MINUTE`, `ANALYST_DAILY_PER_CLIENT`, `ANALYST_MAX_CONCURRENT` | Per-visitor and concurrency limits (defaults 6, 40, 3) |

## Before you share a public link

1. Keep `ANALYST_DAILY_BUDGET_USD` low. The limiter keeps its counters in the API process, which is right for one instance;
   run one instance, or move the counters to Postgres/Redis (noted in `app/core/limits.py`).
2. Ask the analyst two or three questions yourself, then run the eval with the same key:
   `cd apps/api && python -m app.evals.agent_eval --out eval.json` (compare with `--model gpt-5.6-terra`).
3. Put the numbers in `apps/web/src/content/facts.ts` (`ANALYST_EVAL`) so the About page shows them, and in the README.
   The first live run (`gpt-5.6-luna`) is already recorded in `docs/evals/`: 8 of 9, then 9 of 9 after the counting fix.

## Operations

- Analytics results are cached in the API process for 10 minutes (match data is static). After re-ingesting, restart the API
  or wait out the cache.
- Every request gets an `X-Request-ID` header and one JSON log line; the analyst logs one line per tool call and one per answer
  (steps, tokens, cost, latency).
- Schema changes go through Alembic: `cd apps/api && alembic revision --autogenerate -m "..."`, review the file, commit it.
  The API applies migrations on start, and CI runs `alembic check` so models and migrations cannot drift.
- Adding matches: add ids to `data/samples/selected_matches.json`, run `python -m app.services.ingest`, then
  `python -m app.services.rag` to refresh the index.
- Local Docker, whole stack: `docker compose -f infra/docker-compose.yml --profile full up --build` (set `OPENAI_API_KEY` first).
