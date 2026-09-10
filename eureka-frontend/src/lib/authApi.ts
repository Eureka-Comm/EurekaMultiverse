// EUREKA Identity & Access — frontend API client (thin, contract-accurate).
// It only calls the backend's server-side authority; it NEVER sends role/status/permissions, and
// it never stores the session token in localStorage (it lives in the HttpOnly cookie). The CSRF
// token is held in transient memory and sent on state-changing requests.
import { getApiBase } from './apiBase';

const BASE = `${getApiBase()}/api/auth`;
const ADMIN_BASE = `${getApiBase()}/api/admin`;

let csrfToken = '';
export function setCsrfToken(t: string) { csrfToken = t; }
export function getCsrfToken() { return csrfToken; }

export interface SafeUser {
  user_id: string; name: string; phone: string; email: string; company: string;
  role: string; status: string; email_verified: boolean; phone_verified: boolean;
  created_at: string; last_login_at?: string | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

async function req<T>(method: string, path: string, body?: unknown, base: string = BASE): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (csrfToken && method.toUpperCase() !== 'GET') headers['X-CSRF-Token'] = csrfToken;
  const res = await fetch(`${base}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = typeof j?.detail === 'string' ? j.detail : (typeof j?.detail === 'object' ? JSON.stringify(j.detail) : JSON.stringify(j));
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function register(data: { name: string; phone: string; email: string; company: string; password: string }) {
  return req<{ ok: boolean; user: SafeUser; verification_token: string }>('POST', '/register', data);
}
export function verifyEmail(token: string) {
  return req<{ ok: boolean; user: SafeUser }>('POST', '/verify-email', { token });
}
export async function login(email: string, password: string) {
  const r = await req<{ ok: boolean; mfa_required: boolean; mfa_challenge_id?: string;
    session_token?: string; csrf_token?: string; expires_at?: string; user: SafeUser }>('POST', '/login', { email, password });
  if (r.csrf_token) setCsrfToken(r.csrf_token);
  return r;
}
export async function mfaVerify(challenge_id: string, code: string) {
  const r = await req<{ ok: boolean; csrf_token: string; user: SafeUser }>('POST', '/mfa/verify', { challenge_id, code });
  if (r.csrf_token) setCsrfToken(r.csrf_token);
  return r;
}
export function forgotPassword(email: string) {
  return req<{ ok: boolean; message: string }>('POST', '/forgot-password', { email });
}
export function resetPassword(token: string, password: string) {
  return req<{ ok: boolean; user: SafeUser }>('POST', '/reset-password', { token, password });
}
export async function me(): Promise<SafeUser> {
  const r = await req<{ ok: boolean; user: SafeUser }>('GET', '/me');
  return r.user;
}
export async function logout() {
  const r = await req<{ ok: boolean }>('POST', '/logout', {});
  setCsrfToken('');
  return r;
}
export async function refresh() {
  const r = await req<{ ok: boolean; csrf_token: string }>('POST', '/refresh', {});
  setCsrfToken(r.csrf_token);
  return r;
}

// ---- admin ------------------------------------------------------------------ //
export function adminListUsers(params: { search?: string; role?: string; status?: string; limit?: number; offset?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  if (params.role) qs.set('role', params.role);
  if (params.status) qs.set('status', params.status);
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.offset) qs.set('offset', String(params.offset));
  return req<{ total: number; offset: number; limit: number; users: SafeUser[] }>('GET', `/users?${qs}`, undefined, ADMIN_BASE);
}
export function adminUserActivity(userId: string) {
  return req<any>('GET', `/users/${encodeURIComponent(userId)}/activity`, undefined, ADMIN_BASE);
}
export function adminChangeRole(userId: string, role: string) {
  return req<{ ok: boolean; user: SafeUser }>('POST', `/users/${encodeURIComponent(userId)}/role`, { role }, ADMIN_BASE);
}
export function adminSetStatus(userId: string, status: string) {
  return req<{ ok: boolean; user: SafeUser }>('POST', `/users/${encodeURIComponent(userId)}/status`, { status }, ADMIN_BASE);
}
export function adminReportLogins(params: { aggregation?: string; from?: string; to?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.aggregation) qs.set('aggregation', params.aggregation);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  return req<any>('GET', `/reports/logins?${qs}`, undefined, ADMIN_BASE);
}
export function adminAudit(limit = 200) {
  return req<{ total: number; events: any[] }>('GET', `/audit?limit=${limit}`, undefined, ADMIN_BASE);
}
export function adminDashboard() {
  return req<any>('GET', '/dashboard', undefined, ADMIN_BASE);
}

/** Real .xlsx export (server-built via openpyxl, admin-gated). Returns a Blob for download. */
export async function adminExportUsers(): Promise<void> {
  const res = await fetch(`${ADMIN_BASE}/users/export`, { credentials: 'same-origin' });
  if (!res.ok) throw new ApiError(res.status, 'EXPORT_FAILED');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const d = new Date();
  const stamp = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  a.href = url;
  a.download = `eureka_users_${stamp}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
