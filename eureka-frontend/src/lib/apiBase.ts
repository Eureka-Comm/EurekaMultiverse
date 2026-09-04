// Single source of truth for the API base used by every EUREKA fetch call.
//
// ARCHITECTURE: same-origin. The browser must reach the backend through the frontend origin's
// `/api` route (nginx proxies it to the backend container, or the Vite dev server proxies it to
// the local backend). NO loopback/localhost value may ever become the production API base,
// because `localhost` resolves to the USER's machine, and a cross-origin call to a loopback
// address from a public origin is blocked by the browser's Private Network Access guard.
//
// RULES:
//   - empty/undefined VITE_EUREKA_API_URL  -> '' (relative /api)
//   - VITE_EUREKA_API_URL is a loopback origin (localhost|127.0.0.1|0.0.0.0|::1) -> '' (relative)
//   - any other absolute origin            -> used verbatim (split deployment only)
export function getApiBase(): string {
  const raw = (import.meta.env.VITE_EUREKA_API_URL as string | undefined) ?? '';
  const v = raw.trim();
  if (!v) return '';
  if (/^(https?:)?\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0|::1|\[::1\])(:\d+)?$/i.test(v)) return '';
  return v.replace(/\/+$/, '');
}

export const API_BASE = getApiBase();
