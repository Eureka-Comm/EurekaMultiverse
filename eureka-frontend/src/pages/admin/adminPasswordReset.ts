/**
 * Client-side PRE-VALIDATION for the admin password reset.
 *
 * AUTHORITY NOTE (non-negotiable): everything here is UX only. The server re-validates the password
 * against `password_policy` and re-checks authorization on POST /api/admin/users/{id}/password.
 * A client that lies to these helpers cannot widen its authority — it only gets a 400/403 back.
 * The rules below deliberately MIRROR the backend so the admin sees the rejection before the round
 * trip, not instead of it.
 */

/** Mirrors identity_config().password_policy.min_length (12). */
export const PASSWORD_MIN_LENGTH = 12;

/** Mirrors service.validate_password()'s trivial list. */
const TRIVIAL = new Set([
  'password', 'password1', 'password123', '12345678', '1234567890', 'qwerty123',
  'letmein1', 'admin123', 'welcome1', 'iloveyou1', 'abc12345',
]);

/** Returns the list of policy violations for a candidate password (empty array = acceptable). */
export function passwordIssues(password: string, email = ''): string[] {
  const issues: string[] = [];
  if (password.length < PASSWORD_MIN_LENGTH) issues.push(`At least ${PASSWORD_MIN_LENGTH} characters.`);
  if (!/[A-Za-z]/.test(password)) issues.push('At least one letter.');
  if (!/[0-9]/.test(password)) issues.push('At least one digit.');
  if (password && email && password.toLowerCase() === email.trim().toLowerCase()) {
    issues.push('Must not be the account email.');
  }
  if (TRIVIAL.has(password.toLowerCase())) issues.push('Must not be a common password.');
  return issues;
}

/** Confirmation check — silent until the admin actually types a confirmation. */
export function confirmIssue(password: string, confirm: string): string | null {
  if (!confirm) return null;
  return password === confirm ? null : 'Passwords do not match.';
}

/**
 * Mirrors service.admin_set_password(): a SUPER_ADMIN may reset anyone; an ADMIN may reset a USER
 * or their OWN account, never another ADMIN/SUPER_ADMIN (no lateral takeover).
 */
export function canResetPassword(
  actorRole: string | undefined,
  actorEmail: string | undefined,
  target: { role: string; email: string },
): boolean {
  const actor = (actorRole ?? '').toUpperCase();
  if (actor === 'SUPER_ADMIN') return true;
  if (actor !== 'ADMIN') return false;
  if (target.role === 'USER') return true;
  return (actorEmail ?? '').toLowerCase() === target.email.toLowerCase();
}

/**
 * A reset on a non-ACTIVE account succeeds but does not grant access — say so, instead of leaving
 * the admin to rediscover the INVITED trap (login returns a generic 401 for every failure).
 */
export function resetBlockedReason(target: { status: string }): string | null {
  if (target.status === 'ACTIVE') return null;
  return `This account is ${target.status}: the new password will not let the user sign in until the account is ACTIVE.`;
}
