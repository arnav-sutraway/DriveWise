import { afterEach, describe, expect, it, vi } from 'vitest';
import { askMockCoach } from './mockChatApi.js';

afterEach(() => {
  vi.useRealTimers();
});

describe('mock chat API', () => {
  it('returns a structured four-way-stop answer and visualization', async () => {
    vi.useFakeTimers();
    const responsePromise = askMockCoach('How does a four-way stop work?');
    await vi.advanceTimersByTimeAsync(350);
    await expect(responsePromise).resolves.toMatchObject({
      answer: expect.stringContaining('E-1'),
      visualization: {
        scenario_id: 'four_way_stop',
        animation: 'demonstrate_right_of_way',
      },
    });
  });

  it('answers supported non-intersection questions without switching the scene', async () => {
    vi.useFakeTimers();
    const questions = [
      'How do I parallel park?',
      'How do I safely change lanes?',
      'What should I do at a yellow traffic light?',
      'A pedestrian is in the crosswalk.',
      'I am turning left and an oncoming car is going straight.',
    ];

    for (const question of questions) {
      const responsePromise = askMockCoach(question);
      await vi.advanceTimersByTimeAsync(350);
      await expect(responsePromise).resolves.toMatchObject({
        answer: expect.not.stringContaining('Try one of the suggested questions'),
        visualization: null,
      });
    }
  });

  it('does not silently assign a driving scenario to an unknown question', async () => {
    vi.useFakeTimers();
    const responsePromise = askMockCoach('Tell me about driving.');
    await vi.advanceTimersByTimeAsync(350);
    await expect(responsePromise).resolves.toMatchObject({
      visualization: null,
      reminder: expect.stringContaining('not an AI model'),
    });
  });
});
