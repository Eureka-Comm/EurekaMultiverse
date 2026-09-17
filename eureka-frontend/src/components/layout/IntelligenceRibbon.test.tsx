import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';

/** See EurekaSidebar.test.tsx: zustand v5's SSR snapshot is the INITIAL state, so a mocked store is
 *  the only way to observe role-gated navigation under renderToString. */
const mocks = vi.hoisted(() => ({ user: null as { email: string; role: string } | null }));
vi.mock('../../store/authStore', () => ({
  useAuthStore: (selector?: (s: unknown) => unknown) => {
    const state = { status: 'authenticated', user: mocks.user };
    return selector ? selector(state) : state;
  },
  isAdmin: (role?: string | null) => role === 'ADMIN' || role === 'SUPER_ADMIN',
  isSuperAdmin: (role?: string | null) => role === 'SUPER_ADMIN',
}));

import { IntelligenceRibbon } from './IntelligenceRibbon';

function renderAs(role: string | null) {
  mocks.user = role ? { email: 'someone@example.com', role } : null;
  return renderToString(createElement(MemoryRouter, null, createElement(IntelligenceRibbon)));
}

describe('IntelligenceRibbon — Settings replaced by Administration', () => {
  beforeEach(() => { mocks.user = null; });

  it('offers Administration to an admin and no Settings', () => {
    const html = renderAs('SUPER_ADMIN');
    expect(html).toContain('Administration');
    expect(html).not.toContain('Settings');
  });

  it('hides Administration from a non-admin', () => {
    const html = renderAs('USER');
    expect(html).not.toContain('Administration');
    expect(html).not.toContain('Settings');
  });

  it('keeps the rest of the navigation intact', () => {
    const html = renderAs('ADMIN');
    for (const label of ['Overview', 'Cases', 'Data', 'Sandbox', 'Authority', 'Actioner', 'Audit']) {
      expect(html).toContain(label);
    }
  });
});
