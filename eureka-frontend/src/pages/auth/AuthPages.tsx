import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff, Mail, Lock } from 'lucide-react';
import { login, register, verifyEmail, forgotPassword, resetPassword, mfaVerify, ApiError } from '../../lib/authApi';
import { useAuthStore } from '../../store/authStore';

// --------------------------------------------------------------------------- //
// EUREKA Identity Experience — a restrained product surface, not a cyberpunk
// concept. Mirrors CONSTELACIÓN's observability language: a small set of surfaces
// (`--eureka-surface`), 1px hairline borders, muted labels, cyan as accent, and
// generous whitespace. No stars/orbs/grids/glow, no excessive tracking, no filler
// copy. Only what supports function, hierarchy, brand, usability.
// --------------------------------------------------------------------------- //

function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div style={{ position: 'relative', minHeight: '100vh', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: 'var(--font-sans)', background: 'var(--eureka-canvas)', overflowY: 'auto', overflowX: 'hidden' }}>
      {/* subtle depth: an elevated focus at the top, fading into the universe canvas. No showcase. */}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(80% 55% at 50% 22%, var(--eureka-surface-elevated) 0%, var(--eureka-canvas) 68%)', pointerEvents: 'none' }} />

      <div className="ci-panel" style={{ position: 'relative', width: 'min(420px, 92vw)', borderRadius: 16, padding: '38px 38px 30px', borderColor: 'var(--eureka-spatial-hairline)', boxShadow: '0 28px 64px rgba(0,0,0,0.5)' }}>
        {/* WORDMARK — a real brand, not tracked technical text */}
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 27, letterSpacing: '0.04em', color: 'var(--eureka-text-display)', lineHeight: 1.1 }}>EUREKA</div>
        {subtitle && <div style={{ marginTop: 8, fontSize: 12.5, letterSpacing: '0.01em', color: 'var(--eureka-text-label)' }}>{subtitle}</div>}

        {/* gentle divider (structure, not decoration) */}
        <div style={{ margin: '22px 0 24px', height: 1, background: 'var(--eureka-spatial-hairline)' }} />

        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 15, color: 'var(--eureka-text-section)' }}>{title}</div>

        <div className="mt-7">{children}</div>
      </div>
    </div>
  );
}

const labelCls = "block text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--eureka-text-label)] mb-1.5 mt-5";

const inputBase: React.CSSProperties = {
  width: '100%', padding: '12px 13px', borderRadius: 10, fontSize: '14px', fontFamily: 'var(--font-sans)',
  color: '#1f2328', background: '#ffffff', border: '1px solid rgba(0,0,0,0.14)',
  outline: 'none', transition: 'border-color .18s ease, box-shadow .18s ease, background .18s ease',
};

const focusCls = 'eureka-auth-input';

function CtaBtn({ busy, label, onSubmit }: { busy: boolean; label: string; onSubmit?: () => void }) {
  return (
    <button type="submit" onClick={onSubmit} disabled={busy}
      style={{ width: '100%', marginTop: 26, padding: '13px 16px', borderRadius: 10, fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 600, letterSpacing: '0.01em', cursor: 'pointer', color: '#ffffff', background: 'var(--eureka-signal-cognitive)', border: '1px solid var(--eureka-signal-cognitive)', transition: 'filter .15s ease, transform .06s ease, opacity .2s ease', opacity: busy ? 0.6 : 1 }}>
      <span className="inline-flex items-center gap-2">{busy ? (label === 'Sign in' ? 'Signing in…' : 'Working…') : (<>{label}<ArrowRight size={15} /></>)}</span>
    </button>
  );
}

export function LoginPage() {
  const nav = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault(); setBusy(true); setError(null);
    try {
      if (!challenge) {
        const r = await login(email, password);
        if (r.mfa_required && r.mfa_challenge_id) { setChallenge(r.mfa_challenge_id); setPassword(''); setBusy(false); return; }
        setUser(r.user); nav('/', { replace: true });
      } else {
        const r = await mfaVerify(challenge, code);
        setUser(r.user); nav('/', { replace: true });
      }
    } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <AuthShell title={challenge ? 'Two-factor authentication' : 'Sign in to EUREKA'} subtitle="Cognitive Intelligence Platform">
      <form onSubmit={submit} data-testid="login-form" noValidate>
        {!challenge ? (
          <>
            <label className={labelCls} htmlFor="email">Email</label>
            <div className="relative">
              <Mail size={17} style={{ position: 'absolute', left: 13, top: 13, color: '#8a8a9c' }} />
              <input id="email" className={focusCls} style={{ ...inputBase, paddingLeft: 39 }} type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" aria-label="Email" autoComplete="email" required />
            </div>
            <label className={labelCls} htmlFor="password">Password</label>
            <div className="relative">
              <Lock size={17} style={{ position: 'absolute', left: 13, top: 13, color: '#8a8a9c' }} />
              <input id="password" className={focusCls} style={{ ...inputBase, paddingLeft: 39, paddingRight: 40 }} type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" aria-label="Password" autoComplete="current-password" required />
              <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'} style={{ position: 'absolute', right: 9, top: 10, cursor: 'pointer', background: 'transparent', border: 'none', color: '#7a7a8a' }}>
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </>
        ) : (
          <>
            <label className={labelCls} htmlFor="code">Verification code</label>
            <input id="code" className={focusCls} style={{ ...inputBase, textAlign: 'center', letterSpacing: '0.35em', fontSize: 18 }} value={code} onChange={(e) => setCode(e.target.value)} placeholder="000000" aria-label="Verification code" autoComplete="one-time-code" inputMode="numeric" maxLength={6} required />
          </>
        )}
        {error && <div className="mt-3 text-[13px]" style={{ color: 'var(--eureka-signal-blocked)' }}>{error}</div>}
        <CtaBtn busy={busy} label={challenge ? 'Verify' : 'Sign in'} />
        {!challenge ? (
          <>
            <div className="mt-4 text-right text-[13px]"><Link style={{ color: 'var(--eureka-text-label)' }} to="/forgot-password">Forgot password?</Link></div>
            <div className="mt-7 pt-6 text-[13px]" style={{ borderTop: '1px solid var(--eureka-spatial-hairline)', color: 'var(--eureka-text-label)' }}>
              New to EUREKA? <Link className="font-medium" style={{ color: 'var(--eureka-signal-cognitive)' }} to="/register">Create an account</Link>
            </div>
          </>
        ) : (
          <div className="mt-4 text-right text-[13px]"><Link style={{ color: 'var(--eureka-text-label)' }} to="/login">Back to sign in</Link></div>
        )}
      </form>
    </AuthShell>
  );
}

function FormField({ value, onChange, type = 'text', placeholder, label }: { value: string; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; type?: string; placeholder?: string; label: string }) {
  const id = label.toLowerCase().replace(/[^a-z]/g, '-');
  const [show, setShow] = useState(false);
  const isPw = type === 'password';
  return (
    <div>
      <label className={labelCls} htmlFor={id}>{label}</label>
      <div className="relative">
        <input id={id} className={`block w-full ${focusCls}`} style={{ ...inputBase, paddingRight: isPw ? 42 : undefined }}
          type={isPw && show ? 'text' : type} value={value} onChange={onChange} placeholder={placeholder}
          aria-label={label} autoComplete={type === 'password' ? 'new-password' : 'off'} required />
        {isPw && (
          <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}
            style={{ position: 'absolute', right: 9, top: 10, cursor: 'pointer', background: 'transparent', border: 'none', color: '#7a7a8a' }}>
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
    </div>
  );
}

export function RegisterPage() {
  const nav = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [form, setForm] = useState({ name: '', phone: '', email: '', company: '', password: '' });
  const [verifyToken, setVerifyToken] = useState('');
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault(); setBusy(true); setError(null);
    try {
      const r = await register(form);
      if (import.meta.env.DEV) {
        // DEV convenience (single click): verify the account and log in immediately.
        // Production keeps the honest token/email flow (email delivery is an external dependency).
        try {
          await verifyEmail(r.verification_token);
          const l = await login(form.email, form.password);
          setUser(l.user);
          nav('/', { replace: true });
          return;
        } catch (autoErr) {
          // Fall back to the manual token screen rather than leaving the user stuck.
          setVerifyToken(r.verification_token);
        }
      } else {
        setVerifyToken(r.verification_token);
      }
    } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
    finally { setBusy(false); }
  };
  const doVerify = async () => { setBusy(true); setError(null); try { await verifyEmail(verifyToken); nav('/login', { replace: true }); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } finally { setBusy(false); } };
  const f = (k: keyof typeof form) => ({ value: form[k], onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value }) });

  return (
    <AuthShell title="Create your account" subtitle="Cognitive Intelligence Platform">
      {!verifyToken ? (
        <form onSubmit={submit} data-testid="register-form">
          <FormField {...f('name')} label="Name" placeholder="Your name" />
          <FormField {...f('email')} type="email" label="Email" placeholder="name@company.com" />
          <FormField {...f('company')} label="Company" placeholder="Company" />
          <FormField {...f('phone')} label="Phone" placeholder="+1" />
          <FormField {...f('password')} type="password" label="Password" placeholder="At least 12 characters" />
          {error && <div className="mt-3 text-[13px]" style={{ color: 'var(--eureka-signal-blocked)' }}>{error}</div>}
          <CtaBtn busy={busy} label="Create account" />
          <div className="mt-7 pt-6 text-[13px]" style={{ borderTop: '1px solid var(--eureka-spatial-hairline)', color: 'var(--eureka-text-label)' }}>
            Already registered? <Link className="font-medium" style={{ color: 'var(--eureka-signal-cognitive)' }} to="/login">Sign in</Link>
          </div>
        </form>
      ) : (
        <div className="space-y-4">
          <div className="text-[13px]" style={{ color: 'var(--eureka-text-label)' }}>
            Account created. <span style={{ fontWeight: 600 }}>No real email was sent</span> — email delivery is a not-yet-connected external dependency, so we never pretend a message went out. To finish verification right here, use the code below.
          </div>
          <div className="flex items-center gap-2">
            <input className={`block w-full ${focusCls}`} style={{ ...inputBase, fontFamily: 'var(--font-mono)', fontSize: 13 }} value={verifyToken} readOnly aria-label="Verification token" />
            <button type="button" onClick={() => { try { void navigator.clipboard.writeText(verifyToken); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* clipboard unavailable */ } }}
              style={{ height: 44, padding: '0 12px', borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: 'pointer', background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text-display)', border: '1px solid var(--eureka-spatial-hairline)' }}>
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <CtaBtn busy={busy} label="Verify & continue" onSubmit={doVerify} />
          {error && <div className="text-[13px]" style={{ color: 'var(--eureka-signal-blocked)' }}>{error}</div>}
        </div>
      )}
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const submit = async (ev: React.FormEvent) => { ev.preventDefault(); setMsg(null); try { const r = await forgotPassword(email); setMsg(r.message); } catch (e) { setMsg(String(e)); } };
  return (
    <AuthShell title="Reset your password" subtitle="Cognitive Intelligence Platform">
      <form onSubmit={submit}>
        <label className={labelCls} htmlFor="email">Email</label>
        <div className="relative">
          <Mail size={17} style={{ position: 'absolute', left: 13, top: 13, color: '#8a8a9c' }} />
          <input id="email" className={focusCls} style={{ ...inputBase, paddingLeft: 39 }} type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" aria-label="Email" autoComplete="email" required />
        </div>
        <div className="mt-3 text-[13px]" style={{ color: 'var(--eureka-text-label)' }}>We’ll email you a link to reset your password. Delivery is an external dependency.</div>
        {msg && <div className="mt-3 text-[13px]" style={{ color: 'var(--eureka-text-section)' }}>{msg}</div>}
        <CtaBtn busy={false} label="Request reset" />
        <div className="mt-7 pt-6 text-[13px]" style={{ borderTop: '1px solid var(--eureka-spatial-hairline)' }}><Link style={{ color: 'var(--eureka-text-label)' }} to="/login">Back to sign in</Link></div>
      </form>
    </AuthShell>
  );
}

export function ResetPasswordPage() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const submit = async (ev: React.FormEvent) => { ev.preventDefault(); setError(null); try { await resetPassword(token, password); nav('/login', { replace: true }); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } };
  return (
    <AuthShell title="Set a new password" subtitle="Cognitive Intelligence Platform">
      <form onSubmit={submit}>
        <FormField value={password} onChange={(e) => setPassword(e.target.value)} type="password" label="New password" placeholder="At least 12 characters" />
        {error && <div className="mt-3 text-[13px]" style={{ color: 'var(--eureka-signal-blocked)' }}>{error}</div>}
        <CtaBtn busy={false} label="Reset password" />
        <div className="mt-7 pt-6 text-[13px]" style={{ borderTop: '1px solid var(--eureka-spatial-hairline)' }}><Link style={{ color: 'var(--eureka-text-label)' }} to="/login">Back to sign in</Link></div>
      </form>
    </AuthShell>
  );
}
