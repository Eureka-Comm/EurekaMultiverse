import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';

/**
 * The auth store is mocked on purpose: zustand v5 hands React `getInitialState()` as the SSR
 * snapshot, so `renderToString` would always render the INITIAL (anonymous) state and a real store
 * could never be observed here. The mock keeps the real component JSX under test while controlling
 * the role — and `isAdmin` mirrors the real implementation.
 */
const mocks = vi.hoisted(() => ({ user: null as { email: string; role: string } | null }));
vi.mock('../../store/authStore', () => ({
  useAuthStore: (selector?: (s: unknown) => unknown) => {
    const state = { status: 'authenticated', user: mocks.user, logout: () => {}, setUser: () => {}, bootstrap: async () => {} };
    return selector ? selector(state) : state;
  },
  isAdmin: (role?: string | null) => role === 'ADMIN' || role === 'SUPER_ADMIN',
  isSuperAdmin: (role?: string | null) => role === 'SUPER_ADMIN',
}));

import EurekaSidebar from './EurekaSidebar';

/** Render the real sidebar as a given role (SSR, no network). */
function renderAs(role: string | null) {
  mocks.user = role ? { email: 'someone@example.com', role } : null;
  return renderToString(createElement(MemoryRouter, null, createElement(EurekaSidebar)));
}

describe('EurekaSidebar — Settings removed, Administration kept', () => {
  beforeEach(() => { mocks.user = null; });

  it('shows Administration and no longer shows Settings (SUPER_ADMIN)', () => {
    const html = renderAs('SUPER_ADMIN');
    expect(html).toContain('Administration');
    expect(html).not.toContain('Settings');
  });

  it('also holds for a plain ADMIN', () => {
    const html = renderAs('ADMIN');
    expect(html).toContain('Administration');
    expect(html).not.toContain('Settings');
  });

  it('hides Administration from a non-admin — and still no Settings anywhere', () => {
    const html = renderAs('USER');
    expect(html).not.toContain('Administration');
    expect(html).not.toContain('Settings');
  });

  it('keeps the account block and Logout for everyone', () => {
    const html = renderAs('USER');
    expect(html).toContain('Logout');
    expect(html).toContain('someone@example.com');
  });
});
