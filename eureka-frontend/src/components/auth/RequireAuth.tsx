import { useEffect, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore, isAdmin } from '../../store/authStore';

export function AccessDenied() {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--eureka-canvas)] text-[var(--eureka-text-label)] font-mono">
      <div className="text-center">
        <div className="text-lg uppercase tracking-widest text-[var(--eureka-signal-blocked)]">403 · Access Denied</div>
        <div className="mt-2 text-[11px]">Your role does not grant access to this surface.</div>
      </div>
    </div>
  );
}

export default function RequireAuth({ children, requireAdmin = false }: { children: ReactNode; requireAdmin?: boolean }) {
  const { status, user } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    if (status === 'loading') { void useAuthStore.getState().bootstrap(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === 'loading') {
    return <div className="flex h-screen items-center justify-center bg-[var(--eureka-canvas)] text-[var(--eureka-text-label)] font-mono text-xs uppercase tracking-widest">Checking access…</div>;
  }
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (requireAdmin && !isAdmin(user?.role)) {
    return <AccessDenied />;
  }
  return <>{children}</>;
}
