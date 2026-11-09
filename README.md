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
