import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Vitest config for the EUREKA frontend.
// - `include` scopes tests to `src` so the timestamped `_backup_*` snapshots are never
//   re-run as test suites.
// - `plugins: [react()]` enables the same JSX transform the app uses so component
//   smoke tests (react-dom/server renderToString) can mount presentational components.
// - `environment: 'node'` for the pure domain/projection tests (no DOM needed).
export default defineConfig({
  plugins: [react()],
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/_backup*/**',
      '**/dist/**',
      '**/build/**',
      // Legacy script-style selector "test" (runs at module load, no vitest suite).
      '**/selectors/decisionSelectors.test.ts',
    ],
    environment: 'node',
  },
});
