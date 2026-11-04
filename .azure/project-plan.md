# Project Plan

**Status**: Approved
**Created**: 2026-11-04
**Mode**: NEW

---

## 1. Project Overview

**Goal**: Build DriveWise AI, a frontend-only driving education MVP with a mock-response chat and an interactive Three.js town intersection scene. The four-way-stop demonstration is a deterministic, predefined animation whose right-of-way behavior is verified; no backend, persistence, authentication, deployment, or real LLM integration is in scope. The project is designed so that every module is independently testable.

**App Type**: Static frontend (SPA)

**API Login**: No

**Mode**: NEW

**Deployment Plan**: No deployment plan found

---

## 2. Frontend — Web App

| Component | Technology |
|-----------|-----------|
| **Language** | JavaScript |
| **Framework** | React + Vite |
| **Package Manager** | npm |
| **Test Runner** | vitest |
| **Mocking Library** | vi.mock |
| **Test Command** | npm test |

---

## 3. Services Required

| Azure Service | Role in App | Environment Variable | Default Value (Local) | Classification |
|---------------|------------|---------------------|----------------------|----------------|
| None | Frontend-only local application; no Azure resources or service dependencies | — | — | Essential |

---

## 4. Prerequisites

### Run

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Node.js | frontend | ✅ | v22.14.0 |
| npm | frontend | ✅ | 10.9.2 |

### Debug

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Google Chrome | frontend | ✅ | 156.0.8078.80 |

---

## 5. Design System & UI

**Component Library**: Native HTML controls with Tailwind CSS utilities
**Style Direction**: A calm, trustworthy driving-coach workspace: deep navy structure, sky-blue learning actions, warm road-sign accents, rounded but restrained surfaces, and clear separation between the conversation and the 3D intersection. Keep the scene readable and uncluttered on desktop and stack the workspace regions on narrow screens.
**Typography**: Inter, system-ui, -apple-system, "Segoe UI", sans-serif

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | `#173B5E` | DriveWise brand, primary learning actions, selected navigation |
| `accent` | `#E9A23B` | Road-sign cues, turn highlights, and secondary emphasis |
| `surface` | `#F4F7FA` | Main driving-coach workspace background |
| `text` | `#172B3A` | Scenario prompts, guidance, and scene labels |
| `muted` | `#637789` | Conversation timestamps, helper text, and scene annotations |
| `border` | `#D6E0E8` | Chat cards, controls, and workspace separators |

### Pages

| Page | Route | Purpose | Layout |
|------|-------|---------|--------|
| Learning Studio | `/` | Practice driving rules through a mock-response coach and a deterministic four-way-stop animation in one responsive workspace. | `header + nav + hero + two-column(main+sidebar) + footer` |

### Sample Content

Learning Studio — primary four-way-stop learning scenario:
| Scenario | Learner prompt | Coach response / right-of-way result | State |
|-----------|----------------|--------------------------------------|-------|
| First to stop | “How does a four-way stop work?” | The scripted eastbound vehicle E-1 stopped first and proceeds when the intersection and crosswalk are clear. | Verified |

Chat empty state: “Ask DriveWise about a driving rule” · four suggested questions are shown.
Loading state: three coach-message skeleton lines while a mock response is generated.
Error state: an explicit coach response explains the mock API failure.
Intersection scene: four labeled approach lanes (North, East, South, West); vehicles N-1, E-1, S-1, W-1; stop lines, sidewalks, buildings, and trees. The animation uses scripted arrival order and deterministic right-of-way decisions—no external traffic or AI service.

---

## 6. Project Structure

```
DriveWise/
├── .azure/
│   ├── requirements.json
│   └── project-plan.md
├── public/
├── src/
│   ├── components/
│   │   ├── CoachChat.jsx
│   │   ├── IntersectionScene.jsx
│   │   └── LearningWorkspace.jsx
│   ├── data/
│   │   └── drivingScenarios.js
│   ├── logic/
│   │   └── rightOfWay.js
│   ├── services/
│   │   └── mockChatApi.js
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

---

## 7. Route Definitions

| # | Method | Path | Description | Request Body | Response Body | Status Codes |
|---|--------|------|-------------|-------------|--------------|-------------|
| 1 | GET | `/` | Serve the single-page Learning Studio; client-side chat uses predefined mock responses and the scene uses scripted four-way-stop scenarios. | — | React application shell | 200 |

---

## 8. Next Steps

1. Scaffold the approved React + Vite frontend, mock-response chat, and interactive Three.js / React Three Fiber town intersection.
2. Verify deterministic four-way-stop right-of-way rules with automated tests; keep all chat replies local and predefined.
3. Run the frontend locally and document setup and usage in `README.md`.
4. Do not add a backend, datastore, authentication, real LLM integration, or Azure deployment.
