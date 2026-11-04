# Frontend verification hand-off

This approved project is frontend-only. Do not add a backend, database, seed data, authentication, real LLM integration, Azure resources, or deployment.

## Frontend

- Project folder: workspace root (`DriveWise/`)
- Install: `npm install`
- Development: `npm run dev`
- Build: `npm run build`
- Tests: `npm test`
- UI entry: `src/main.jsx`
- Mock chat/scenarios: `src/data/drivingScenarios.js`
- Deterministic right-of-way seam: `src/logic/rightOfWay.js`
- Tests: `src/logic/rightOfWay.test.js`
- No live API client or external data source; retain mock responses.

## Routes

- `GET /` — serve the Vite single-page application.

## Data and services

- Database: none; no migrations or seed data.
- Backend/API service: none.
- Azure services: none.
- Essential services: static React/Vite frontend only.
- Enhancement services: none.

## Verification checklist

- [x] `npm test` passes the predefined right-of-way and animation tests (6 tests).
- [x] `npm run build` succeeds.
- [x] Verify prompt selection updates the answer and scene; verify orbit controls and demo playback in a browser.
