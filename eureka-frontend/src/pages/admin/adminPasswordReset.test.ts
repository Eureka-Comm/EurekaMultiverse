import { describe, it, expect } from 'vitest';
import { passwordIssues, confirmIssue, canResetPassword, resetBlockedReason, canGrantRole,
  grantableRoles, createUserIssues, PASSWORD_MIN_LENGTH } from './adminPasswordReset';

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

describe('user creation — client pre-validation and the role-grant mirror', () => {
  it('only a SUPER_ADMIN may grant ADMIN/SUPER_ADMIN (mirrors the server rule)', () => {
    expect(canGrantRole('SUPER_ADMIN', 'ADMIN')).toBe(true);
    expect(canGrantRole('SUPER_ADMIN', 'SUPER_ADMIN')).toBe(true);
    expect(canGrantRole('ADMIN', 'USER')).toBe(true);
    expect(canGrantRole('ADMIN', 'ADMIN')).toBe(false);
    expect(canGrantRole('ADMIN', 'SUPER_ADMIN')).toBe(false);
    expect(canGrantRole('USER', 'USER')).toBe(false);
    expect(canGrantRole(undefined, 'USER')).toBe(false);
  });

  it('the role select never offers what the server would refuse with 403', () => {
    expect(grantableRoles('SUPER_ADMIN')).toEqual(['USER', 'ADMIN', 'SUPER_ADMIN']);
    expect(grantableRoles('ADMIN')).toEqual(['USER']);
    expect(grantableRoles('USER')).toEqual(['USER']);
    expect(grantableRoles(undefined)).toEqual(['USER']);
  });

  it('requires a name and a plausible email before submitting', () => {
    expect(createUserIssues({ name: 'Ada', email: 'ada@example.com' })).toEqual([]);
    expect(createUserIssues({ name: 'Ada', email: '  Ada@Example.COM ' })).toEqual([]);
    expect(createUserIssues({ name: '   ', email: 'ada@example.com' })).toContain('Name is required.');
    expect(createUserIssues({ name: 'Ada', email: '' })).toContain('Email is required.');
    expect(createUserIssues({ name: 'Ada', email: 'nope' })).toContain('Enter a valid email address.');
    expect(createUserIssues({ name: 'Ada', email: 'a b@example.com' })).toContain('Enter a valid email address.');
  });
});
