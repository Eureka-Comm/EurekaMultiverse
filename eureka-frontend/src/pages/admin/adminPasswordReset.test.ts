import { describe, it, expect } from 'vitest';
import { passwordIssues, confirmIssue, canResetPassword, resetBlockedReason, PASSWORD_MIN_LENGTH } from './adminPasswordReset';

describe('admin password reset — client pre-validation (server stays authoritative)', () => {
  it('accepts a policy-compliant password', () => {
    expect(passwordIssues('BrandNew123!', 'victim@example.com')).toEqual([]);
  });

  it('reports each policy violation', () => {
    expect(passwordIssues('short', '')).toContain(`At least ${PASSWORD_MIN_LENGTH} characters.`);
    expect(passwordIssues('abcdefghijkl', '')).toContain('At least one digit.');
    expect(passwordIssues('123456789012', '')).toContain('At least one letter.');
    expect(passwordIssues('Password12345', 'Password12345')).toContain('Must not be the account email.');
    expect(passwordIssues('password123', '')).toContain('Must not be a common password.');
  });

  it('mirrors the server minimum length of 12', () => {
    expect(PASSWORD_MIN_LENGTH).toBe(12);
    expect(passwordIssues('12345678901', '')).not.toEqual([]);   // 11 chars
    expect(passwordIssues('123456789012', '').filter((i) => i.includes('characters'))).toEqual([]);
  });

  it('flags a confirmation mismatch only once typing started', () => {
    expect(confirmIssue('BrandNew123!', '')).toBeNull();
    expect(confirmIssue('BrandNew123!', 'BrandNew123!')).toBeNull();
    expect(confirmIssue('BrandNew123!', 'BrandNew124!')).toMatch(/do not match/);
  });

  it('ADMIN may reset a USER but not another ADMIN or a SUPER_ADMIN (mirrors the server rule)', () => {
    expect(canResetPassword('ADMIN', 'admin@example.com', { role: 'USER', email: 'u@example.com' })).toBe(true);
    expect(canResetPassword('ADMIN', 'admin@example.com', { role: 'ADMIN', email: 'a2@example.com' })).toBe(false);
    expect(canResetPassword('ADMIN', 'admin@example.com', { role: 'SUPER_ADMIN', email: 's@example.com' })).toBe(false);
  });

  it('ADMIN may reset their own account; SUPER_ADMIN may reset anyone', () => {
    expect(canResetPassword('ADMIN', 'admin@example.com', { role: 'ADMIN', email: 'admin@example.com' })).toBe(true);
    expect(canResetPassword('SUPER_ADMIN', 'root@example.com', { role: 'SUPER_ADMIN', email: 's@example.com' })).toBe(true);
    expect(canResetPassword('SUPER_ADMIN', 'root@example.com', { role: 'ADMIN', email: 'a@example.com' })).toBe(true);
  });

  it('a USER (or an unknown/absent role) can never reset anybody', () => {
    expect(canResetPassword('USER', 'u@example.com', { role: 'USER', email: 'x@example.com' })).toBe(false);
    expect(canResetPassword(undefined, undefined, { role: 'USER', email: 'x@example.com' })).toBe(false);
  });

  it('warns when the target cannot sign in yet — the INVITED trap must be visible', () => {
    expect(resetBlockedReason({ status: 'ACTIVE' })).toBeNull();
    expect(resetBlockedReason({ status: 'INVITED' })).toMatch(/INVITED/);
    expect(resetBlockedReason({ status: 'DISABLED' })).toMatch(/DISABLED/);
    expect(resetBlockedReason({ status: 'PENDING_VERIFICATION' })).toMatch(/PENDING_VERIFICATION/);
  });
});
