# DriveWise AI

DriveWise is a driving education app with a React/Vite frontend, a Django RAG backend, and an interactive Three.js town intersection. Questions are answered only from the driver's manuals in the knowledge base, with numbered citations; if nothing relevant is found, the coach says so instead of guessing.

## Requirements

- Node.js 20.19+ or 22.12+
- npm
- Python 3.10+

## Setup

The React/Vite project lives in `frontend/`. From the project directory, install its dependencies and run the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

In a second terminal, start the Django API:

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # then paste your GEMINI_API_KEY into .env
python manage.py migrate
python manage.py ingest_documents --state Georgia --edition 2026   # loads data/manuals/
python manage.py runserver
```

## RAG chatbot (backend)

1. Get a free Gemini API key at https://aistudio.google.com/apikey and put it in `backend/.env` (never commit `.env`).
2. Put the Georgia Driver's Manual PDF (from https://dds.georgia.gov) in `backend/data/manuals/`.
3. Run `python manage.py ingest_documents --state Georgia --edition 2026`. Re-running replaces the same files. Changing the embedding model requires re-ingesting.

Pipeline (`backend/apps/`):

| Step | File |
| --- | --- |
| Read PDF, save chunks | `knowledge/services/document_ingestion.py` |
| Split into chunks | `knowledge/services/preprocessing.py` |
| Embed (`RAG_EMBEDDER=gemini`, or `hashing` offline) | `knowledge/services/embedding_generation.py` |
| Retrieve (cosine search, `RAG_TOP_K`, `RAG_MIN_SCORE`) | `knowledge/services/vector_retrieval.py` |
| Build prompt | `chat/services/prompts.py` |
| Generate (Gemini, `RAG_CHAT_MODEL`) | `chat/services/inference.py` |
| Check the answer cites a retrieved passage | `chat/services/response_validation.py` |
| Run the steps above | `chat/services/rag.py` |

`POST /api/v1/chat/` with `{"message": "..."}` returns `{"answer": "...", "grounded": true}`. `grounded: false` means no relevant passage was found (or the model's answer didn't cite one) and `answer` is the "couldn't find that" message. Errors: 400 bad input, 503 missing API key, 502 provider failure.

## Usage

- Choose a suggested question or enter a driving-rule question and select **Ask coach**. Answers come only from the manuals in the knowledge base.
- Use **Play demo** to watch the vehicles approach, stop, highlight the scripted first-to-stop vehicle, and proceed through the intersection.
- Drag the 3D scene to orbit the view and scroll/pinch to zoom.

`GET /api/v1/health/` checks the backend. `POST /api/v1/chat/` answers questions (see above). The predefined frontend scenario and its 3D demonstration remain in place; chat responses do not control scenario selection or animation.

Future scenario controls should be selected from the predefined frontend scenario set rather than supplied as arbitrary IDs or animation instructions.

For local development, Django uses SQLite and a development-only secret key. Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` appropriately before any non-local deployment. Production deployments should collect and serve static files from `backend/staticfiles/` or configure a static-file host.

The `.azure/` directory contains project-planning and integration handoff documents from the original Azure planning workflow. Django and Vite do not read it at runtime, so it can be removed if those planning records are no longer useful.

## Performance monitoring (story 4)

Monitoring runs locally in Django. After installing the backend requirements:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Sign in at `http://127.0.0.1:8000/admin/`, then select **Open chatbot performance dashboard**,
or visit `/admin/performance/`. Only active staff accounts can access it. The dashboard
supports 15-minute and one-hour windows, refreshes every 30 seconds while visible,
and lets you pause automatic refresh.

It displays average, maximum, and estimated p95 latency, system failure rate, failure
categories, and timings for question embedding, passage retrieval, and answer generation.
The p95 value is the upper bound of the histogram bucket containing the 95th percentile,
not an exact percentile. Values above the largest bucket display `> 300 s`.

Latency covers completed backend chat requests, including provider retries, up to when
the response is ready and before storing metrics. It excludes browser/network time and
in-flight requests. Stage measurements include failed attempts; skipped stages are absent.
Failure rate is server failures divided by completed valid requests (successes + server
failures). Invalid input and wrong HTTP methods are excluded from that denominator and
latency summaries. A normal ungrounded/no-answer response counts as successful.

No targets are assumed. Set these optional values in `backend/.env`, then restart Django:

```dotenv
# Example targets only; use the targets agreed for your project. Zero disables a threshold.
PERFORMANCE_LATENCY_WARNING_MS=10000
PERFORMANCE_FAILURE_WARNING_PERCENT=5
```

Warnings flag a p95 bucket above the latency target or an error rate at/above its threshold.
Unset targets show baseline mode; missing samples show **No data**. Read failures show
**Metrics unavailable**. A metric-write failure emits a diagnostic warning without changing
the chat response; lost measurements are not retried/reconstructed. These metrics are not
an external uptime monitor and cannot observe requests lost when the process exits.

Only minute-level aggregates (stage, outcome, duration bucket, sample count, total and
maximum duration) are persisted. No prompts, answers, individual request timestamps,
identities, query history, or usage-reporting interface are added. Story 5 remains separate.
Database-side counter increments support concurrent workers sharing the same database;
SQLite is intended for local development. Keep metric storage and cleanup in the hosting
plan when choosing a production database.

To remove aggregates older than seven days, run this locally as needed (schedule after hosting):

```powershell
.\.venv\Scripts\python.exe manage.py prune_performance_metrics --days 7
```

## Verification

```bash
cd frontend
npm test
npm run build
```

The backend tests can be run from `backend/`:

```bash
python manage.py test
```

The frontend tests cover the Django API client and existing scripted 3D/right-of-way behavior.

## Project layout

```text
frontend/
  src/
    components/ Coach chat, learning workspace, and reusable 3D scene
    data/       Prepared driving scenarios and suggested questions
    logic/      Deterministic right-of-way and animation logic with tests
    services/   Django API client with tests
  index.html    Vite application document
  package.json  Frontend dependencies and scripts
  vite.config.js Development API proxy and build configuration
backend/
  config/       Django settings and project entry points
  apps/api/     Versioned health and chat routes
  apps/frontend/ Serves the built SPA from Django
  apps/chat/    RAG pipeline, prompt, LLM inference, answer validation
  apps/knowledge/ Documents/chunks, PDF ingestion, chunking, embeddings, retrieval
  data/manuals/ Source PDFs for the knowledge base
```
