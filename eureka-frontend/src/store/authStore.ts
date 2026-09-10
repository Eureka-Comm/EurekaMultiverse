import { create } from 'zustand';
import { me, logout as apiLogout, type SafeUser } from '../lib/authApi';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthState {
  status: AuthStatus;
  user: SafeUser | null;
  bootstrap: () => Promise<void>;
  setUser: (u: SafeUser) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'loading',
  user: null,

  // Resolve the session from the HttpOnly cookie (server-authoritative).
  bootstrap: async () => {
    try {
      const user = await me();
      set({ status: 'authenticated', user });
    } catch {
      set({ status: 'unauthenticated', user: null });
    }
  },

  setUser: (u) => set({ user: u, status: 'authenticated' }),

  logout: async () => {
    try { await apiLogout(); } catch { /* best-effort; the cookie is also cleared server-side */ }
    set({ status: 'unauthenticated', user: null });
  },
}));

export function isAdmin(role?: string | null): boolean {
  return role === 'ADMIN' || role === 'SUPER_ADMIN';
}
export function isSuperAdmin(role?: string | null): boolean {
  return role === 'SUPER_ADMIN';
}
