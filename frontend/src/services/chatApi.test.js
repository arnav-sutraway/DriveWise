import { afterEach, describe, expect, it, vi } from 'vitest';
import { askCoach } from './chatApi.js';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('chat API client', () => {
  it('sends chat messages to the Django API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ answer: 'A response', reminder: null, visualization: null }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(askCoach('How does a four-way stop work?')).resolves.toEqual({
      answer: 'A response',
      reminder: null,
      visualization: null,
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ message: 'How does a four-way stop work?' }),
    });
  });

  it('surfaces the backend not-implemented response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 501,
      json: async () => ({ detail: 'Chat responses are not implemented yet.' }),
    }));

    await expect(askCoach('Hello')).rejects.toThrow('Chat responses are not implemented yet.');
  });
});
