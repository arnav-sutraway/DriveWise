import { describe, expect, it } from 'vitest';
import { normalizeSources, safeSourceUrl, sourceLabel, splitCitations } from './citations.js';

describe('splitCitations', () => {
  it('separates citation markers from the surrounding text', () => {
    expect(splitCitations('Never ride on sidewalks [3]. Use bike lanes [1][2].')).toEqual([
      { type: 'text', value: 'Never ride on sidewalks ' },
      { type: 'citation', number: 3 },
      { type: 'text', value: '. Use bike lanes ' },
      { type: 'citation', number: 1 },
      { type: 'citation', number: 2 },
      { type: 'text', value: '.' },
    ]);
  });

  it('returns plain text unchanged when there are no citations', () => {
    expect(splitCitations('No citations here.')).toEqual([{ type: 'text', value: 'No citations here.' }]);
    expect(splitCitations('')).toEqual([]);
  });
});

describe('safeSourceUrl', () => {
  it('allows same-site paths and http(s) links', () => {
    expect(safeSourceUrl('/api/v1/documents/4/file/#page=21')).toBe('/api/v1/documents/4/file/#page=21');
    expect(safeSourceUrl('https://www.atlantaga.gov/home/showdocument?id=42502'))
      .toBe('https://www.atlantaga.gov/home/showdocument?id=42502');
  });

  it('rejects scripts, protocol-relative, and malformed links', () => {
    for (const url of ['javascript:alert(1)', 'data:text/html,hi', '//evil.example', 'not a url', '', null, 7]) {
      expect(safeSourceUrl(url)).toBeNull();
    }
  });
});

describe('normalizeSources', () => {
  it('keeps valid entries and sanitizes their links', () => {
    expect(normalizeSources([
      { number: 3, title: 'Atlanta rules', page: null, url: '/api/v1/documents/2/file/',
        official_url: 'https://www.atlantaga.gov/x' },
      { number: 1, title: 'Manual', page: 21, url: 'javascript:alert(1)', official_url: null },
      { number: 'x', title: 'bad' },
      null,
    ])).toEqual([
      { number: 3, title: 'Atlanta rules', page: null, url: '/api/v1/documents/2/file/',
        officialUrl: 'https://www.atlantaga.gov/x' },
      { number: 1, title: 'Manual', page: 21, url: null, officialUrl: null },
    ]);
  });

  it('accepts already-normalized entries from saved history', () => {
    const saved = [{ number: 2, title: 'Guide', page: 5, url: '/a', officialUrl: 'https://b.example' }];
    expect(normalizeSources(saved)).toEqual(saved);
    expect(normalizeSources(undefined)).toEqual([]);
  });
});

it('labels sources with their page when known', () => {
  expect(sourceLabel({ title: 'Manual', page: 21 })).toBe('Manual, p. 21');
  expect(sourceLabel({ title: 'Atlanta rules', page: null })).toBe('Atlanta rules');
});
