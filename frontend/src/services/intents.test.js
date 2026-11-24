import { describe, expect, it } from 'vitest';
import { intentLabel } from './intents.js';

describe('intentLabel', () => {
  it('labels each question type the backend can return', () => {
    expect(intentLabel('factual')).toBe('Quick answer');
    expect(intentLabel('explanation')).toBe('Explanation');
    expect(intentLabel('procedure')).toBe('Step-by-step');
    expect(intentLabel('scenario')).toBe('Your situation');
    expect(intentLabel('creative')).toBe('Practice');
  });

  it('shows no label for general, unknown, or malformed types', () => {
    for (const value of ['general', 'made-up', 'toString', '', null, undefined, 3, {}]) {
      expect(intentLabel(value)).toBeNull();
    }
  });
});
