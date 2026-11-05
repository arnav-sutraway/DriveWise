# DriveWise AI

DriveWise is a driving education practice app with a React/Vite frontend, a Django API scaffold, and an interactive Three.js town intersection. The backend currently provides a health endpoint and a deliberately unimplemented chat endpoint. It does not include chatbot, dataset, embedding, retrieval, model, authentication, or admin-story functionality.

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
python manage.py migrate
python manage.py runserver
```

Open the localhost URL printed by Vite. Vite proxies `/api/` requests to Django at `http://127.0.0.1:8000`; the frontend API uses a relative URL so the API path stays the same in development and production.

To serve the built frontend from Django instead, build it first, then open the Django server root:

```bash
# In frontend/
npm run build

# In backend/
python manage.py runserver
```

Django resolves the frontend and build directories from `backend/config/settings.py`, not from the shell's current directory. The Vite build uses `/static/frontend/` asset URLs, and Django's static-files configuration maps that prefix to `frontend/dist/`.

## Usage

- Choose a suggested question or enter a driving-rule question and select **Ask coach**. The frontend sends the message to Django, which currently returns HTTP 501 because chat behavior is intentionally not implemented.
- Use **Play demo** to watch the vehicles approach, stop, highlight the scripted first-to-stop vehicle, and proceed through the intersection.
- Drag the 3D scene to orbit the view and scroll/pinch to zoom.

`GET /api/v1/health/` checks the backend. `POST /api/v1/chat/` is only a placeholder and returns 501. The predefined frontend scenario and its 3D demonstration remain in place; chat responses do not control scenario selection or animation.

The backend service boundaries are separated under `backend/apps/`: API routing, document ingestion, embedding generation, vector retrieval, LLM inference, and response validation. These are interfaces only. No paid API or external vector database is configured. Future scenario controls should be selected from the predefined frontend scenario set rather than supplied as arbitrary IDs or animation instructions.

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
  apps/chat/    Inference and response-validation interfaces
  apps/knowledge/ Document-ingestion, embedding, and retrieval interfaces
```
