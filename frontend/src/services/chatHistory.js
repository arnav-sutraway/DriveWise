// Persists the active conversation in this browser so it survives page reloads.
// There are no user accounts, so "my chat history" means "this browser's history".

export const STORAGE_KEY = 'drivewise.chatHistory.v1';

// Keep storage bounded; older messages are dropped first.
export const MAX_STORED_MESSAGES = 100;

const ROLES = new Set(['user', 'assistant']);

function isValidMessage(message) {
  return (
    message !== null
    && typeof message === 'object'
    && ROLES.has(message.role)
    && typeof message.content === 'string'
  );
}

// localStorage can be missing or throw (e.g. disabled storage, private browsing,
// quota exceeded). History is a convenience, so failures fall back to an empty chat.
function getStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function loadChatHistory() {
  const storage = getStorage();
  if (!storage) return [];
  try {
    const parsed = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    return Array.isArray(parsed) ? parsed.filter(isValidMessage) : [];
  } catch {
    return [];
  }
}

export function saveChatHistory(messages) {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (messages.length === 0) {
      storage.removeItem(STORAGE_KEY);
    } else {
      storage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)));
    }
  } catch {
    // Ignore write failures; the chat keeps working for this page view.
  }
}

export function clearChatHistory() {
  saveChatHistory([]);
}
