import { describe, expect, it } from 'vitest';
import { getParkingScenario, parkingScenarios } from '../data/parkingScenarios.js';
import {
  getParkingDuration,
  getParkingFrame,
  getParkingStepIndex,
  getParkingStepStart,
  sampleParkingPath,
} from './parkingAnimation.js';

function angleDifference(first, second) {
  return ((first - second + Math.PI / 2) % Math.PI + Math.PI) % Math.PI - Math.PI / 2;
}

function rectangleAxes(yaw) {
  return [
    [Math.cos(yaw), -Math.sin(yaw)],
    [Math.sin(yaw), Math.cos(yaw)],
  ];
}

function projectedRadius(axis, yaw) {
  const [widthAxis, lengthAxis] = rectangleAxes(yaw);
  return (1.18 / 2) * Math.abs(axis[0] * widthAxis[0] + axis[1] * widthAxis[1])
    + (2.3 / 2) * Math.abs(axis[0] * lengthAxis[0] + axis[1] * lengthAxis[1]);
}

function vehiclesOverlap(first, second) {
  const dx = second.position[0] - first.position[0];
  const dz = second.position[1] - first.position[1];
  const axes = [...rectangleAxes(first.yaw), ...rectangleAxes(second.yaw)];
  return axes.every((axis) => (
    Math.abs(dx * axis[0] + dz * axis[1])
      < projectedRadius(axis, first.yaw) + projectedRadius(axis, second.yaw) - 0.015
  ));
}

function worldPosition(position, angle) {
  return [
    Math.cos(angle) * position[0] + Math.sin(angle) * position[1],
    -Math.sin(angle) * position[0] + Math.cos(angle) * position[1],
  ];
}

describe('parking lesson paths', () => {
  it('defines all four lessons with steps, safety checks, mistakes, and sourced finish criteria', () => {
    expect(parkingScenarios.map(({ id }) => id)).toEqual([
      'parallel',
      'perpendicular',
      'reverse',
      'angle',
    ]);

    for (const scenario of parkingScenarios) {
      expect(scenario.steps.length).toBeGreaterThanOrEqual(3);
      expect(scenario.steps.every((step) => step.title && step.instruction)).toBe(true);
      expect(scenario.safety).toBeTruthy();
      expect(scenario.mistakes.length).toBeGreaterThan(0);
      expect(scenario.recognition).toBeTruthy();
      expect(scenario.source).toContain('Georgia DDS');
    }

    expect(getParkingScenario('reverse').sourceNote).toContain('does not prescribe');
    expect(() => getParkingScenario('unlisted')).toThrow(RangeError);
  });

  it.each(['parallel', 'perpendicular', 'reverse', 'angle'])(
    'keeps the %s path continuous and ends aligned inside its marked bay',
    (scenarioId) => {
      const scenario = getParkingScenario(scenarioId);
      const motions = scenario.steps.filter((step) => step.motion).map((step) => step.motion);
      let previousEnd = scenario.layout.startPosition ?? motions[0].from;

      for (const motion of motions) {
        expect(motion.from).toEqual(previousEnd);
        const samples = sampleParkingPath(motion, 40);
        expect(samples).toHaveLength(41);
        expect(samples[0]).toEqual(motion.from);
        expect(samples[samples.length - 1]).toEqual(motion.to);
        expect(samples.flat().every(Number.isFinite)).toBe(true);
        previousEnd = motion.to;
      }

      const frame = getParkingFrame(scenarioId, getParkingDuration(scenarioId));
      expect(frame.position[0]).toBeCloseTo(scenario.layout.targetCenter[0], 5);
      expect(frame.position[1]).toBeCloseTo(scenario.layout.targetCenter[1], 5);
      expect(Math.abs(angleDifference(frame.yaw, scenario.layout.targetYaw))).toBeLessThan(0.02);
    },
  );

  it.each(['parallel', 'perpendicular', 'reverse', 'angle'])(
    'keeps the %s animated vehicle clear of surrounding parked vehicles',
    (scenarioId) => {
      const scenario = getParkingScenario(scenarioId);
      const duration = getParkingDuration(scenarioId);
      const bayAngle = scenario.layout.bayAngle ?? 0;
      const parked = scenario.layout.parkedCars.map((vehicle) => ({
        position: worldPosition(vehicle.position, bayAngle),
        yaw: vehicle.rotation + bayAngle,
      }));

      for (let elapsed = 0; elapsed <= duration; elapsed += 80) {
        const frame = getParkingFrame(scenarioId, elapsed);
        const moving = { position: frame.position, yaw: frame.yaw };
        const collision = parked.find((vehicle) => vehiclesOverlap(moving, vehicle));
        expect(collision, `${scenarioId} at ${elapsed}ms: ${JSON.stringify(moving)}`).toBeUndefined();
      }
    },
  );

  it('supports direct step selection and a stable reverse-parking starting pose', () => {
    expect(getParkingStepIndex('parallel', 0)).toBe(0);
    expect(getParkingStepIndex('parallel', getParkingStepStart('parallel', 1))).toBe(1);
    expect(getParkingStepIndex('parallel', getParkingDuration('parallel'))).toBe(3);
    expect(getParkingStepStart('parallel', 1)).toBe(3800);

    const reverse = getParkingScenario('reverse');
    const start = getParkingFrame('reverse', 0);
    expect(start.position).toEqual(reverse.layout.startPosition);
    expect(start.yaw).toBe(reverse.layout.startYaw);
    expect(start.direction).toBe('stopped');
  });
});
