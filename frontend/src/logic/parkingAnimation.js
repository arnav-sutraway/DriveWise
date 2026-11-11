import { getParkingScenario } from '../data/parkingScenarios.js';

export function getParkingDuration(scenarioId) {
  const scenario = getParkingScenario(scenarioId);
  return scenario.steps.reduce((total, step) => total + step.durationMs, 0);
}

export function getParkingStepIndex(scenarioId, elapsedMs) {
  const scenario = getParkingScenario(scenarioId);
  let end = 0;
  for (let index = 0; index < scenario.steps.length; index += 1) {
    end += scenario.steps[index].durationMs;
    if (elapsedMs < end || index === scenario.steps.length - 1) return index;
  }
  return scenario.steps.length - 1;
}

export function getParkingStepStart(scenarioId, stepIndex) {
  const scenario = getParkingScenario(scenarioId);
  return scenario.steps
    .slice(0, Math.max(0, Math.min(stepIndex, scenario.steps.length)))
    .reduce((total, step) => total + step.durationMs, 0);
}

function cubicBezier(motion, progress) {
  const t = Math.max(0, Math.min(1, progress));
  const inverse = 1 - t;
  const weights = [inverse ** 3, 3 * inverse ** 2 * t, 3 * inverse * t ** 2, t ** 3];
  const points = [motion.from, motion.control1, motion.control2, motion.to];
  const position = [0, 0];
  for (let index = 0; index < points.length; index += 1) {
    position[0] += points[index][0] * weights[index];
    position[1] += points[index][1] * weights[index];
  }

  const derivative = [
    3 * inverse ** 2 * (points[1][0] - points[0][0])
      + 6 * inverse * t * (points[2][0] - points[1][0])
      + 3 * t ** 2 * (points[3][0] - points[2][0]),
    3 * inverse ** 2 * (points[1][1] - points[0][1])
      + 6 * inverse * t * (points[2][1] - points[1][1])
      + 3 * t ** 2 * (points[3][1] - points[2][1]),
  ];

  const movementYaw = Math.atan2(derivative[0], derivative[1]);
  const yaw = motion.direction === 'reverse' ? movementYaw + Math.PI : movementYaw;
  return { position, yaw, direction: motion.direction };
}

export function getParkingFrame(scenarioId, elapsedMs) {
  const scenario = getParkingScenario(scenarioId);
  let cursor = 0;
  const startPosition = scenario.layout.startPosition ?? scenario.steps.find((step) => step.motion)?.motion.from;
  let pose = {
    position: startPosition,
    yaw: scenario.layout.startYaw ?? 0,
    direction: 'stopped',
  };

  for (const step of scenario.steps) {
    const end = cursor + step.durationMs;
    if (elapsedMs < end) {
      if (!step.motion) return { ...pose, step };
      return {
        ...cubicBezier(step.motion, (elapsedMs - cursor) / step.durationMs),
        step,
      };
    }
    if (step.motion) pose = cubicBezier(step.motion, 1);
    cursor = end;
  }

  return { ...pose, step: scenario.steps[scenario.steps.length - 1] };
}

export function sampleParkingPath(motion, sampleCount = 24) {
  return Array.from({ length: sampleCount + 1 }, (_, index) => (
    cubicBezier(motion, index / sampleCount).position
  ));
}
