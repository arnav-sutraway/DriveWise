import { scenarios } from '../data/drivingScenarios.js';

/**
 * Return the deterministic, pre-authored right-of-way decision for a practice
 * scenario. No traffic, timing, or AI service is consulted at runtime.
 */
export function resolveRightOfWay(scenarioId) {
  const scenario = scenarios.find(({ id }) => id === scenarioId);
  if (!scenario) throw new RangeError(`Unknown driving scenario: ${scenarioId}`);

  return {
    scenarioId,
    firstVehicle: scenario.firstVehicle,
    firstApproach: scenario.firstApproach,
    order: [...scenario.order],
    explanation: scenario.response,
  };
}

export function getAnimationPhase(scenarioId, elapsedMs) {
  resolveRightOfWay(scenarioId);
  if (elapsedMs < 1600) return 'approaching';
  if (elapsedMs < 2600) return 'stopped';
  if (elapsedMs < 3800) return 'right-of-way';
  if (elapsedMs < 7600) return 'proceeding';
  return 'complete';
}
