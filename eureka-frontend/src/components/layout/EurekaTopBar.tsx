import { Search, Bell } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

const initials = (n?: string) => (n ?? 'EUREKA').split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

// EUREKA app top bar (Search + notifications + current admin identity).
export default function EurekaTopBar() {
  const { user } = useAuthStore();
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div className="relative w-72 max-w-[40vw]">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input className="h-10 w-full rounded-lg border border-border bg-canvas pl-9 pr-8 text-sm text-text outline-none focus:border-signal-cognitive focus:ring-2 focus:ring-cognitive/20" placeholder="Search anything..." aria-label="Search anything" />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-muted">⌘K</span>
      </div>
      <div className="flex items-center gap-4">
        <button aria-label="Notifications" className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-muted hover:text-text"><Bell size={17} /></button>
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold" style={{ background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text-section)' }}>{initials(user?.name)}</div>
          <div className="leading-tight"><div className="text-sm font-medium text-text">{user?.name ?? '—'}</div><div className="text-[10px] text-signal-semantic">{user?.role ?? ''}</div></div>
        </div>
      </div>
    </header>
  );
}
