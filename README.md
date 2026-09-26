# Knowledge Desk

A private document question answering platform. Users upload text based PDFs, a worker extracts and embeds page level chunks, and answers cite the actual document excerpts. Workspaces isolate documents and search results. Administrators invite editors and viewers.

## What is included

- FastAPI, PostgreSQL 17 with pgvector, Alembic, Redis and RQ worker
- OpenAI `text-embedding-3-small` (1536 dimensions) and configurable chat model
- React client for documents, chat, citations, conversation history and invitations
- Cookie JWT sessions with CSRF protection, Argon2 password hashing, workspace scoped queries, roles, rate limits and per-workspace token usage records
- Docker Compose deployment with Caddy HTTPS, persistent volumes and health checks
- Unit/security checks and a labeled evaluation runner

The answer service returns a refusal if no relevant chunks are found, if the model omits citations, or if it cites an unknown source. Citation existence is validated against the retrieved chunks. It cannot automatically prove that every sentence is entailed by the excerpt; review the evaluation report before using results for important decisions. Scanned PDFs and OCR are not supported.

## Run locally

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 24, Docker Compose, an OpenAI API key.

1. Copy `.env.example` to `.env` in the project root. Set a long random alphanumeric database password (it is interpolated into a database URL), `JWT_SECRET` (at least 32 random characters), your API key, and a domain for deployment. Do not commit `.env`.
2. Start dependencies: `docker compose up -d db redis`.
3. Copy `backend/.env.example` to `backend/.env`, set the same database password and an API key, and set a local JWT secret. The local example uses `localhost` for PostgreSQL and Redis. The production compose injects separate container addresses.
4. In `backend/`, run `uv sync` then `uv run alembic -c src/app/alembic.ini upgrade head`.
5. Create the first administrator with `uv run python -m app.cli create-admin`. The CLI prompts for a workspace name, email and password; it does not echo the password.
6. Start the API with `uv run uvicorn app.main:app --reload --port 8000` and the worker in another terminal with `uv run python -m app.worker`.
7. In `frontend/`, run `npm ci` then `npm run dev`. Open `http://localhost:5173`. Vite proxies `/api` to the local backend. API docs are at `http://localhost:8000/docs`.

To run backend tests: `cd backend && uv run pytest -q`. To build the client: `cd frontend && npm ci && npm run build`.

## Deploy on a VPS

1. Point the domain's A/AAAA record to your server. Open ports 80 and 443, install Docker Engine with Compose, and secure access to the host.
2. Copy `.env.example` to `.env` and set `DOMAIN`, `POSTGRES_PASSWORD`, `OPENAI_API_KEY`, and `JWT_SECRET`. Keep the file readable only by the operator (`chmod 600 .env`). Use a secret manager for larger deployments.
3. Run `docker compose up -d --build`. The API applies migrations before serving traffic; the worker starts after the API health check. Caddy obtains and renews TLS certificates for the domain.
4. Create the administrator interactively: `docker compose exec api python -m app.cli create-admin`.
5. Visit `https://<your-domain>` and sign in. Upload a text PDF. Observe `docker compose logs -f api worker` until its status becomes `ready`, then ask a question and inspect its citations.

Keep PostgreSQL, Redis and the API private to the Compose network. Only Caddy publishes ports. Do not use the local development `.env` in production. The `.env.example` files contain placeholders only. Rotate a leaked OpenAI key or JWT secret immediately.

### Backup and restore

Back up both the PostgreSQL database and the `uploads` Docker volume together. A database record without its PDF cannot be reprocessed. Example database dump:

```sh
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > backup.dump
```

Keep the dump and a volume backup encrypted, outside the VPS, and periodically test a restore to a separate environment. Set a retention policy. Redis contains queued work; after a restore, retry any uploaded or failed documents. Run database migrations on a backup or staging copy before upgrading production.

### Operations

`GET /api/v1/health` is a liveness check; `GET /api/v1/health/database` verifies PostgreSQL. Each HTTP response includes `X-Request-ID`. Worker failures are logged and document status changes to `failed`; editors can retry. A job that was interrupted while processing can be retried after 15 minutes. Monitor API 5xx responses, queue depth, disk space, database storage, TLS renewal, OpenAI usage, and backup success. The example Compose stack does not install an external alerting or error reporting account.

## Access and data flow

The first admin is created through the CLI. An admin creates an invitation and securely shares the one time URL with the intended user; the app does not send email. The recipient sets a password. Admins and editors may upload, retry and delete documents; viewers may read and ask questions. Conversation history belongs to its creator. Retrieval filters the workspace in SQL before excerpts are sent to OpenAI. Extracted document text, questions and retrieved excerpts are sent to OpenAI for embeddings/answers as applicable; the original PDF file stays in the upload volume. Confirm the provider's data handling terms for your organization before uploading confidential documents.

The browser receives an HttpOnly signed session cookie and a separate CSRF cookie; writes require the matching `X-CSRF-Token` header. The production setting requires secure cookies and a strong signing secret. Server side logout clears the browser cookie; existing JWTs expire after the configured session interval and cannot be revoked individually. For stronger enterprise requirements, add an identity provider, session revocation and audit retention before deployment.

## Evaluation

Prepare a private JSONL file with 30–50 questions grounded in PDFs actually uploaded to a test workspace. Include answerable, unanswerable and ambiguous questions, and label `expected_document` and `expected_page` where known. `evaluation/example.jsonl` only demonstrates the format; its fictitious document is not an evaluation set.

```sh
cd backend
uv run python -m app.evaluate ../evaluation/your-dataset.jsonl --workspace-id <workspace-uuid> --output evaluation-report.json
```

The report calculates retrieval recall at K and refusal accuracy when labels exist. Citation support, answer faithfulness and relevance require human review against each excerpt. Do not claim quality metrics from the example file. Compare chunk sizes, retrieval thresholds and model choices on this labeled set before changing them.

## Known limits

- Selectable text PDFs only. Large files, scanned pages, complex tables and encrypted PDFs need dedicated extraction work.
- No external email delivery, SSO, per-document ACLs, individual JWT revocation, cost dashboard or telemetry export.
- Redis rate limits are per source IP, so users behind one proxy may share a limit. Keep the API private to the reverse proxy.
- The RAG output is informational. Validate accuracy and privacy with your own documents and keys before live use.
- The original database schema had no workspaces. The workspace migration refuses to run if legacy documents exist, to prevent silent cross-tenant exposure. Export and migrate legacy records into an explicit workspace first.
