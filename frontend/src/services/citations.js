// Helpers for showing a coach answer's "[n]" citations as links to the cited sources.

const CITATION = /\[(\d+)\]/g;

/** Split answer text into plain-text parts and citation markers, in order. */
export function splitCitations(text) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    if (match.index > last) parts.push({ type: 'text', value: text.slice(last, match.index) });
    parts.push({ type: 'citation', number: Number(match[1]) });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ type: 'text', value: text.slice(last) });
  return parts;
}

/** Allow same-site paths and http(s) links only; drops javascript:, data:, and malformed URLs. */
export function safeSourceUrl(url) {
  if (typeof url !== 'string' || !url) return null;
  if (url.startsWith('/') && !url.startsWith('//')) return url;
  try {
    const { protocol } = new URL(url);
    return protocol === 'https:' || protocol === 'http:' ? url : null;
  } catch {
    return null;
  }
}

/**
 * Keep well-formed source entries from the API (or from saved history) with safe links:
 * [{ number, title, page, url, officialUrl }].
 */
export function normalizeSources(sources) {
  if (!Array.isArray(sources)) return [];
  return sources
    .filter((source) => (
      source !== null
      && typeof source === 'object'
      && Number.isInteger(source.number)
      && typeof source.title === 'string'
    ))
    .map((source) => ({
      number: source.number,
      title: source.title,
      page: Number.isInteger(source.page) ? source.page : null,
      url: safeSourceUrl(source.url),
      officialUrl: safeSourceUrl(source.official_url ?? source.officialUrl),
    }));
}

export function sourceLabel(source) {
  return source.page ? `${source.title}, p. ${source.page}` : source.title;
}
