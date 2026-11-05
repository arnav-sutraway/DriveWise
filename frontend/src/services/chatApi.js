const CHAT_ENDPOINT = '/api/v1/chat/';

export async function askCoach(message) {
  const response = await fetch(CHAT_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ message }),
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }

  return payload;
}
