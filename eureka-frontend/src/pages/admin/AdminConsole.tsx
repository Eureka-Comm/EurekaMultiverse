import { useEffect, useMemo, useState } from 'react';
import { Users, UserCheck, CalendarClock, CalendarDays, Search, Download, MoreHorizontal, RefreshCw, RotateCcw, ScrollText, BarChart3, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { adminListUsers, adminUserActivity, adminChangeRole, adminSetStatus, adminSetPassword, adminReportLogins, adminAudit, adminDashboard, adminExportUsers } from '../../lib/authApi';
import { useAuthStore, isSuperAdmin } from '../../store/authStore';
import { passwordIssues, confirmIssue, canResetPassword, resetBlockedReason } from './adminPasswordReset';

type Tab = 'users' | 'reports' | 'audit';
interface U { user_id: string; name: string; email: string; phone: string; company: string; role: string; status: string; email_verified?: boolean; phone_verified?: boolean; created_at: string; last_login_at?: string | null; }

const ROLE_TONE: Record<string, string> = { SUPER_ADMIN: 'bg-signal-semantic/10 text-signal-semantic', ADMIN: 'bg-signal-authority/10 text-signal-authority', USER: 'bg-signal-scientific/10 text-signal-scientific' };
const STATUS_DOT: Record<string, string> = { ACTIVE: 'bg-signal-action', SUSPENDED: 'bg-signal-warning', DISABLED: 'bg-signal-blocked', INVITED: 'bg-text-muted', PENDING_VERIFICATION: 'bg-signal-warning' };
const auditColor = (type: string) => (/SUCCESS|ENABLED|PASSWORD_RESET_COMPLETED/.test(type) ? 'text-signal-action' : /FAILED|DISABLED/.test(type) ? 'text-signal-blocked' : /ROLE_CHANGED/.test(type) ? 'text-signal-semantic' : /PASSWORD_RESET|MFA/.test(type) ? 'text-signal-cognitive' : 'text-text-secondary');
const initials = (name: string) => name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
const fmtUTC = (d = new Date()) => `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} ${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })} UTC`;

export default function AdminConsole() {
  const { user } = useAuthStore();
  const [tab, setTab] = useState<Tab>('users');
  const [rows, setRows] = useState<U[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('All roles');
  const [status, setStatus] = useState('All statuses');
  const [company, setCompany] = useState('All companies');
  const [report, setReport] = useState<any>(null);
  const [audit, setAudit] = useState<any>({ total: 0, events: [] });
  const [dash, setDash] = useState<any>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const superAdmin = isSuperAdmin(user?.role);

  // Admin-initiated password reset — the only recovery path, since /forgot-password has no mailer.
  const [pwTarget, setPwTarget] = useState<U | null>(null);
  const [pwValue, setPwValue] = useState('');
  const [pwConfirm, setPwConfirm] = useState('');
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [pwDone, setPwDone] = useState<string | null>(null);
  const openReset = (u: U) => { setOpenMenu(null); setPwTarget(u); setPwValue(''); setPwConfirm(''); setPwErr(null); setPwDone(null); };
  const closeReset = () => { setPwTarget(null); setPwValue(''); setPwConfirm(''); setPwErr(null); };
  const pwIssues = passwordIssues(pwValue, pwTarget?.email ?? '');
  const pwMismatch = confirmIssue(pwValue, pwConfirm);
  const canSubmit = !!pwTarget && pwValue.length > 0 && pwIssues.length === 0 && !pwMismatch;
  const submitReset = async () => {
    if (!pwTarget || !canSubmit) return;
    setPwErr(null); setBusy(true);
    const label = pwTarget.email;
    try {
      await adminSetPassword(pwTarget.user_id, pwValue);
      setPwDone(`Password reset for ${label}. Their previous sessions were revoked.`);
      closeReset();
      await loadAll();
    } catch (e: any) {
      setPwErr(String(e));
    } finally { setBusy(false); }
  };

  const run = async (fn: () => Promise<void>) => { setErr(null); setBusy(true); try { await fn(); } catch (e: any) { setErr(String(e)); } finally { setBusy(false); } };
  const loadAll = () => run(async () => { const [u, d] = await Promise.all([adminListUsers({ limit: 500 }), adminDashboard()]); setRows(u.users as U[]); setTotal(u.total); setDash(d); });
  const loadReport = () => run(async () => setReport(await adminReportLogins({ aggregation: 'day' })));
  const loadAudit = () => run(async () => setAudit(await adminAudit(100)));
  useEffect(() => { void loadAll(); }, []); // eslint-disable-line
  const companies = useMemo(() => Array.from(new Set(rows.map(r => r.company).filter(Boolean))).sort(), [rows]);
  const filtered = useMemo(() => rows.filter(r => {
    const q = search.toLowerCase();
    return (!q || r.name.toLowerCase().includes(q) || r.email.toLowerCase().includes(q) || r.company.toLowerCase().includes(q))
      && (role === 'All roles' || r.role === role)
      && (status === 'All statuses' || r.status === status)
      && (company === 'All companies' || r.company === company);
  }), [rows, search, role, status, company]);
  const clearFilters = () => { setSearch(''); setRole('All roles'); setStatus('All statuses'); setCompany('All companies'); };
  const isMe = (email: string) => email.toLowerCase() === (user?.email ?? '').toLowerCase();
  const doExport = () => run(async () => { await adminExportUsers(); });
  const switchTab = (t: Tab) => { setTab(t); if (t === 'reports') loadReport(); if (t === 'audit') loadAudit(); };

  const metric = (icon: React.ReactNode, label: string, value: number | undefined, sub: string, iconColor: string) => (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-sm">
      <div className="flex items-center gap-2 text-[13px] text-text-muted"><span className={iconColor}>{icon}</span>{label}</div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-text">{value ?? '—'}</div>
      <div className="mt-1 text-xs text-text-muted">{sub}</div>
    </div>
  );

  const pill = (active: boolean) => `inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium ${active ? 'border border-signal-cognitive text-signal-cognitive bg-signal-cognitive/5' : 'border border-transparent text-text-muted hover:bg-surface-elevated hover:text-text'}`;
  const iconBtn = "inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-muted hover:text-text";

  return (
    <div className="flex flex-col gap-6" data-testid="admin-console">
      {/* breadcrumb + title */}
      <div>
        <div className="text-xs text-text-muted">Administration <span className="mx-1">/</span> <span className="text-text">Users</span></div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-text">User Management</h1>
        <p className="text-sm text-text-muted">Manage accounts, roles and activity across the EUREKA platform.</p>
      </div>

      {/* metrics */}
      {dash && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metric(<Users size={15} />, 'Total users', dash.users, 'All registered users', 'text-signal-cognitive')}
          {metric(<UserCheck size={15} />, 'Active users', dash.active_users, `${dash.users ? Math.round((dash.active_users / dash.users) * 100) : 0}% active`, 'text-signal-action')}
          {metric(<CalendarClock size={15} />, 'Users today', dash.logins_today, 'Unique logins', 'text-signal-cognitive')}
          {metric(<CalendarDays size={15} />, 'Users this month', dash.logins_this_month, 'Unique logins', 'text-signal-cognitive')}
        </div>
      )}

      {/* tabs */}
      <div className="flex flex-wrap items-center gap-3">
        {([['users', 'Users', <Users key="i" size={15} />], ['reports', 'Reports', <BarChart3 key="i" size={15} />], ['audit', 'Audit', <ScrollText key="i" size={15} />]] as [Tab, string, React.ReactNode][]).map(([t, l, ic]) => (
          <button key={t} onClick={() => switchTab(t)} className={pill(tab === t)}>{ic}{l}</button>
        ))}
      </div>
      {err && <div className="rounded-lg border border-signal-blocked/30 bg-signal-blocked/5 px-4 py-2 text-sm text-signal-blocked">Error (fail-closed): {err}</div>}
      {pwDone && <div className="rounded-lg border border-signal-action/30 bg-signal-action/5 px-4 py-2 text-sm text-signal-action">{pwDone}</div>}

      {tab === 'users' && (
        <div className="space-y-4">
          {/* toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-1 flex-wrap items-center gap-2.5">
              <div className="relative min-w-56 flex-1">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name, email or company..." aria-label="Search users" className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text outline-none focus:border-signal-cognitive focus:ring-2 focus:ring-cognitive/20" />
              </div>
              <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter role" className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-signal-cognitive">{['All roles', 'USER', 'ADMIN', 'SUPER_ADMIN'].map((r) => <option key={r}>{r}</option>)}</select>
              <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter status" className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-signal-cognitive">{['All statuses', 'ACTIVE', 'SUSPENDED', 'DISABLED', 'INVITED', 'PENDING_VERIFICATION'].map((s) => <option key={s}>{s}</option>)}</select>
              <select value={company} onChange={(e) => setCompany(e.target.value)} aria-label="Filter company" className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-signal-cognitive"><option>All companies</option>{companies.map((c) => <option key={c}>{c}</option>)}</select>
              {(search || role !== 'All roles' || status !== 'All statuses' || company !== 'All companies') && <button onClick={clearFilters} className="inline-flex items-center gap-1.5 h-10 px-3 rounded-lg border border-border text-sm text-text-muted hover:text-text"><RotateCcw size={15} /> Clear</button>}
            </div>
            <div className="flex items-center gap-2.5">
              <div className="text-right text-xs text-text-muted"><div>Last updated</div><div className="font-medium text-text-secondary">{fmtUTC()}</div></div>
              <button onClick={loadAll} aria-label="Refresh" className={iconBtn}><RefreshCw size={16} className={busy ? 'animate-spin' : ''} /></button>
              <button onClick={doExport} className="inline-flex items-center gap-2 h-10 px-4 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--eureka-signal-cognitive)' }}><Download size={16} /> Export to Excel</button>
            </div>
          </div>

          {/* table */}
          <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-sm">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5"><span className="text-sm font-medium text-text">Users <span className="text-text-muted">{filtered.length}</span></span><span className="text-xs text-text-muted">Page 1 of 1</span></div>
            <table className="w-full text-sm">
              <thead><tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted"><th className="w-10 px-4 py-3"><input type="checkbox" aria-label="Select all" className="h-4 w-4 rounded border-border" /></th><th className="w-[13%] px-4 py-3 font-medium">User ID</th><th className="w-[14%] px-4 py-3 font-medium">Name</th><th className="w-[20%] px-4 py-3 font-medium">Email</th><th className="w-[11%] px-4 py-3 font-medium">Phone</th><th className="w-[10%] px-4 py-3 font-medium">Company</th><th className="w-[9%] px-4 py-3 font-medium">Role</th><th className="w-[9%] px-4 py-3 font-medium">Status</th><th className="w-[10%] px-4 py-3 font-medium">Last Login</th><th className="w-12 px-4 py-3" /></tr></thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.user_id} className="border-b border-border/40 last:border-0 hover:bg-surface-elevated/40">
                    <td className="px-4 py-3"><input type="checkbox" aria-label={`Select ${u.name}`} className="h-4 w-4 rounded border-border" /></td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-text-muted">{u.user_id}</td>
                    <td className="px-4 py-3"><div className="flex items-center gap-3"><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold" style={{ background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text-section)' }}>{initials(u.name)}</div><span className="whitespace-nowrap font-medium text-text">{u.name}{isMe(u.email) && <span className="ml-2 rounded bg-signal-cognitive/10 px-1.5 py-0.5 text-[10px] font-medium text-signal-cognitive">You</span>}</span></div></td>
                    <td className="whitespace-nowrap px-4 py-3 text-text-secondary">{u.email}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-text-secondary">{u.phone || '—'}</td>
                    <td className="px-4 py-3 text-text-secondary">{u.company || '—'}</td>
                    <td className="px-4 py-3"><span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${ROLE_TONE[u.role] ?? ''}`}>{u.role}</span></td>
                    <td className="px-4 py-3"><span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-text-secondary"><span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[u.status] ?? 'bg-text-muted'}`} />{u.status}</span></td>
                    <td className="px-4 py-3 text-text-muted">{(u.last_login_at ?? '—').slice(0, 10) || '—'}</td>
                    <td className="px-4 py-3"><div className="relative"><button aria-label="Actions" onClick={() => setOpenMenu(openMenu === u.user_id ? null : u.user_id)} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border text-text-muted hover:text-text"><MoreHorizontal size={16} /></button>
                      {openMenu === u.user_id && <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border border-border bg-surface p-1 shadow-lg">
                        <button onClick={() => { setOpenMenu(null); run(async () => { const a = await adminUserActivity(u.user_id); window.alert(`Total logins: ${a.total_logins}\nFirst: ${a.first_login ?? '—'}\nLast: ${a.last_login ?? '—'}`); }); }} className="block w-full rounded-md px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-elevated">View activity</button>
                        <button onClick={() => openReset(u)} disabled={!canResetPassword(user?.role, user?.email, u)} title={canResetPassword(user?.role, user?.email, u) ? undefined : 'Only a SUPER_ADMIN may reset an ADMIN or SUPER_ADMIN account'} className="inline-flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-elevated disabled:cursor-not-allowed disabled:opacity-40"><RotateCcw size={14} /> Reset password</button>
                        {superAdmin && <button onClick={() => { setOpenMenu(null); run(async () => { await adminChangeRole(u.user_id, u.role === 'SUPER_ADMIN' ? 'USER' : 'SUPER_ADMIN'); await loadAll(); }); }} className="block w-full rounded-md px-3 py-2 text-left text-sm text-signal-cognitive hover:bg-surface-elevated">Change role</button>}
                        <button onClick={() => { setOpenMenu(null); run(async () => { await adminSetStatus(u.user_id, u.status === 'DISABLED' ? 'ACTIVE' : 'DISABLED'); await loadAll(); }); }} className={`block w-full rounded-md px-3 py-2 text-left text-sm ${u.status === 'DISABLED' ? 'text-signal-action' : 'text-signal-blocked'} hover:bg-surface-elevated`}>{u.status === 'DISABLED' ? 'Enable' : 'Disable'}</button>
                      </div>}
                    </div></td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={10} className="px-4 py-10 text-center text-sm text-text-muted">No users match your filters.</td></tr>}
              </tbody>
            </table>
          </div>

          {/* pagination */}
          <div className="flex items-center justify-between"><div className="text-sm text-text-muted">Users <b className="text-text">{filtered.length}</b></div>
            <div className="flex items-center gap-2"><span className="text-xs text-text-muted">Page 1 of 1</span><button aria-label="Previous" className={`${iconBtn} opacity-40`}><ChevronLeft size={16} /></button><button aria-label="Next" className={`${iconBtn} opacity-40`}><ChevronRight size={16} /></button></div>
          </div>
        </div>
      )}

      {tab === 'reports' && report && (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-sm"><table className="w-full text-sm"><thead><tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted"><th className="px-4 py-3 font-medium">Period</th><th className="px-4 py-3 font-medium">Logins</th></tr></thead><tbody>{(report.series ?? []).map((s: any) => <tr key={s.period} className="border-b border-border/40 last:border-0"><td className="px-4 py-3 text-text">{s.period}</td><td className="px-4 py-3 text-text-secondary">{s.logins}</td></tr>)}{(report.series ?? []).length === 0 && <tr><td colSpan={2} className="px-4 py-10 text-center text-sm text-text-muted">No login events.</td></tr>}</tbody></table></div>
      )}

      {tab === 'audit' && (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-sm"><table className="w-full text-sm"><thead><tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted"><th className="px-4 py-3 font-medium">Time</th><th className="px-4 py-3 font-medium">Event</th><th className="px-4 py-3 font-medium">User</th><th className="px-4 py-3 font-medium">Ok</th></tr></thead><tbody>{(audit.events ?? []).map((e: any) => <tr key={e.event_id} className="border-b border-border/40 last:border-0"><td className="px-4 py-3 text-xs text-text-muted">{(e.timestamp ?? '').slice(0, 19)}</td><td className={`px-4 py-3 font-medium ${auditColor(e.event_type)}`}>{e.event_type}</td><td className="px-4 py-3 text-text-secondary">{e.user_id ?? '—'}</td><td className="px-4 py-3"><span className={e.success ? 'text-signal-action' : 'text-signal-blocked'}>{String(e.success)}</span></td></tr>)}{(audit.events ?? []).length === 0 && <tr><td colSpan={4} className="px-4 py-10 text-center text-sm text-text-muted">No security events.</td></tr>}</tbody></table></div>
      )}

      {/* Admin-initiated password reset — the ONLY recovery path: /forgot-password has no mailer,
          so without this the admin cannot restore anybody's access. */}
      {pwTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-label="Reset password">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-text">Reset password</h2>
                <p className="mt-0.5 truncate text-xs text-text-muted">{pwTarget.name} · {pwTarget.email} · <span className="font-mono">{pwTarget.user_id}</span></p>
              </div>
              <button onClick={closeReset} aria-label="Close" className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border text-text-muted hover:text-text"><X size={15} /></button>
            </div>

            <div className="mt-4 space-y-3">
              <label className="block text-sm text-text-secondary">New password
                <input type="password" autoComplete="new-password" value={pwValue} onChange={(e) => setPwValue(e.target.value)} aria-label="New password" className="mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-signal-cognitive" />
              </label>
              <label className="block text-sm text-text-secondary">Confirm password
                <input type="password" autoComplete="new-password" value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)} aria-label="Confirm password" className="mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-signal-cognitive" />
              </label>
              {pwValue.length > 0 && pwIssues.length > 0 && (
                <ul className="list-inside list-disc space-y-0.5 text-xs text-signal-warning">{pwIssues.map((i) => <li key={i}>{i}</li>)}</ul>
              )}
              {pwMismatch && <p className="text-xs text-signal-warning">{pwMismatch}</p>}
              {pwTarget.status !== 'ACTIVE' && (
                <p className="rounded-lg border border-signal-warning/30 bg-signal-warning/5 px-3 py-2 text-xs text-signal-warning">{resetBlockedReason(pwTarget)}</p>
              )}
              {pwErr && <p className="rounded-lg border border-signal-blocked/30 bg-signal-blocked/5 px-3 py-2 text-xs text-signal-blocked">{pwErr}</p>}
              <p className="text-xs text-text-muted">You set this password and it is never stored in plaintext — only its Argon2id hash is persisted. All of this user&apos;s active sessions will be revoked, and they will need the new password to sign in again.</p>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button onClick={closeReset} className="h-10 rounded-lg border border-border px-4 text-sm text-text-muted hover:text-text">Cancel</button>
              <button onClick={submitReset} disabled={!canSubmit || busy} className="h-10 rounded-lg px-4 text-sm font-medium text-white disabled:opacity-40" style={{ background: 'var(--eureka-signal-cognitive)' }}>Reset password</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
