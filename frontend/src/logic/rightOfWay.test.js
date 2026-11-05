import { describe, expect, it } from 'vitest';
import { getAnimationPhase, resolveRightOfWay } from './rightOfWay.js';

describe('four-way-stop right-of-way decisions', () => {
  it('lets the scripted first-to-stop vehicle proceed first', () => {
    expect(resolveRightOfWay('four_way_stop')).toMatchObject({
      firstVehicle: 'E-1',
      firstApproach: 'East',
    });
  });

  it('animates approach, stop, right-of-way, proceed, and completion phases', () => {
    expect(getAnimationPhase('four_way_stop', 0)).toBe('approaching');
    expect(getAnimationPhase('four_way_stop', 1800)).toBe('stopped');
    expect(getAnimationPhase('four_way_stop', 3000)).toBe('right-of-way');
    expect(getAnimationPhase('four_way_stop', 5000)).toBe('proceeding');
    expect(getAnimationPhase('four_way_stop', 8000)).toBe('complete');
  });

  it('rejects unknown scenarios rather than silently making a traffic decision', () => {
    expect(() => resolveRightOfWay('unlisted')).toThrow(RangeError);
  });
});
