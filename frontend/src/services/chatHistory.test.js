import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  MAX_STORED_MESSAGES,
  STORAGE_KEY,
  clearChatHistory,
  loadChatHistory,
  saveChatHistory,
} from './chatHistory.js';

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

const conversation = [
  { role: 'user', content: 'How does a four-way stop work?' },
  { role: 'assistant', content: 'Drivers proceed in arrival order [1].' },
];

describe('chat history storage', () => {
  it('starts empty when nothing has been saved', () => {
    expect(loadChatHistory()).toEqual([]);
  });

  it('round-trips a saved conversation', () => {
    saveChatHistory(conversation);
    expect(loadChatHistory()).toEqual(conversation);
  });

  it('removes the stored entry when the history is cleared', () => {
    saveChatHistory(conversation);
    clearChatHistory();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(loadChatHistory()).toEqual([]);
  });

  it('keeps only the most recent messages', () => {
    const many = Array.from({ length: MAX_STORED_MESSAGES + 5 }, (_, index) => ({
      role: 'user',
      content: `message ${index}`,
    }));
    saveChatHistory(many);
    const stored = loadChatHistory();
    expect(stored).toHaveLength(MAX_STORED_MESSAGES);
    expect(stored[0].content).toBe('message 5');
  });

  it('ignores corrupted or malformed stored data', () => {
    localStorage.setItem(STORAGE_KEY, '{not json');
    expect(loadChatHistory()).toEqual([]);

    localStorage.setItem(STORAGE_KEY, JSON.stringify({ role: 'user', content: 'not an array' }));
    expect(loadChatHistory()).toEqual([]);

    localStorage.setItem(STORAGE_KEY, JSON.stringify([
      conversation[0],
      { role: 'system', content: 'unknown role' },
      { role: 'assistant' },
      null,
    ]));
    expect(loadChatHistory()).toEqual([conversation[0]]);
  });

  it('does not throw when storage writes fail', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(() => saveChatHistory(conversation)).not.toThrow();
  });
});
