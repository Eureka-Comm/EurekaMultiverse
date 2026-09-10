import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { register, login, setCsrfToken } from '../../lib/authApi';
import { useAuthStore } from '../../store/authStore';
import { LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage } from '../../pages/auth/AuthPages';

function mockFetch(json: unknown, ok = true, status = 200) {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok, status, json: async () => json })) as unknown as typeof fetch);
}
afterEach(() => { vi.unstubAllGlobals(); setCsrfToken(''); });
beforeEach(() => useAuthStore.setState({ status: 'loading', user: null }));

describe('authApi — contract-accurate, no client authority', () => {
  it('register targets /api/auth/register and never sends role/is_admin', async () => {
    mockFetch({ ok: true, user: {}, verification_token: 't' });
    await register({ name: 'A', phone: '', email: 'a@x.com', company: 'E', password: 'GoodPass1!' });
    const [url, opts]: [string, any] = (fetch as any).mock.calls[0];
    expect(url).toBe('/api/auth/register');
    const body = JSON.parse(opts.body);
    expect(body.role).toBeUndefined();
    expect(body.is_admin).toBeUndefined();
    expect(body.permissions).toBeUndefined();
  });

  it('login targets /api/auth/login and sends the transient CSRF header on mutations', async () => {
    setCsrfToken('csrf123');
    mockFetch({ ok: true, mfa_required: false, csrf_token: 'x', user: {} });
    await login('a@x.com', 'pw');
    const [url, opts]: [string, any] = (fetch as any).mock.calls[0];
    expect(url).toBe('/api/auth/login');
    expect(opts.headers['X-CSRF-Token']).toBe('csrf123');
  });
});

describe('authStore — session resolution from /me (server-authoritative)', () => {
  it('bootstrap resolves an authenticated user', async () => {
    mockFetch({ ok: true, user: { user_id: 'u1', role: 'USER', email: 'a@x.com' } });
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(useAuthStore.getState().user?.role).toBe('USER');
  });

  it('bootstrap -> unauthenticated on a 401 (no user fabricated)', async () => {
    mockFetch({ detail: 'UNAUTHORIZED' }, false, 401);
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('unauthenticated');
    expect(useAuthStore.getState().user).toBeNull();
  });
});

describe('AuthPages — render in a Router context', () => {
  it('LoginPage renders the sign-in form', () => {
    const html = renderToString(createElement(MemoryRouter, null, createElement(LoginPage)));
    expect(html).toContain('Sign in');
    expect(html.toLowerCase()).toContain('email');
    expect(html.toLowerCase()).toContain('password');
  });

  it('RegisterPage renders the registration form', () => {
    const html = renderToString(createElement(MemoryRouter, null, createElement(RegisterPage)));
    expect(html).toContain('Create your account');
    expect(html.toLowerCase()).toContain('create account');
  });

  it('auth family reuses the EUREKA branding + glass panel + visible labels (no invented design system)', () => {
    const login = renderToString(createElement(MemoryRouter, null, createElement(LoginPage)));
    expect(login).toContain('EUREKA');
    expect(login).toContain('Cognitive Intelligence Platform');
    expect(login).toContain('ci-panel');            // reuses the existing EUREKA glass panel class
    expect(login).toContain('Email');
    expect(login).toContain('Password');
    expect(login).toContain('forgot-password');

    const forgot = renderToString(createElement(MemoryRouter, null, createElement(ForgotPasswordPage)));
    expect(forgot).toContain('Reset your password');
    expect(forgot).toContain('ci-panel');
    expect(forgot).toContain('Request reset');

    const reset = renderToString(createElement(MemoryRouter, null, createElement(ResetPasswordPage)));
    expect(reset).toContain('Set a new password');
  });
});
