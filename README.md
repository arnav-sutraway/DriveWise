# DriveWise AI

DriveWise is a frontend-only driving education practice app. It combines a local mock-response coach with an interactive Three.js town intersection. It does not use a backend, datastore, authentication, hosted AI/LLM, or Azure resources.

## Requirements

- Node.js 20.19+ or 22.12+
- npm

## Setup

From the project directory:

```bash
npm install
npm run dev
```

Open the localhost URL printed by Vite. The app is designed to work in a normal desktop or mobile browser.

## Usage

- Choose a suggested question or enter a driving-rule question and select **Ask coach**. The chat keeps the conversation history and uses prepared local responses.
- Four-way-stop questions select the predefined intersection scenario. Left-turn, pedestrian, parking, lane-change, and yellow-light questions return mock guidance without changing the scene.
- Use **Play demo** to watch the vehicles approach, stop, highlight the scripted first-to-stop vehicle, and proceed through the intersection.
- Drag the 3D scene to orbit the view and scroll/pinch to zoom.

The predefined scenario content is in `src/data/drivingScenarios.js`, the replaceable mock API is in `src/services/mockChatApi.js`, and deterministic right-of-way decisions and animation phases are in `src/logic/rightOfWay.js`. The four-way demo explicitly uses an authored arrival order; it does not attempt to infer traffic-law decisions at runtime. Other suggested answers do not trigger unimplemented visualizations. Practice guidance is illustrative—follow local traffic laws.

## Verification

```bash
npm test
npm run build
```

The Vitest suite checks the mock API response shape and prepared answers, the scripted first-to-stop decision, animation phases, and invalid-scenario handling.

## Project layout

```text
src/
  components/   Coach chat, learning workspace, and reusable 3D scene
  data/         Prepared driving scenarios and suggested questions
  logic/        Deterministic right-of-way and animation logic with tests
  services/     Replaceable mock chat API with tests
```
