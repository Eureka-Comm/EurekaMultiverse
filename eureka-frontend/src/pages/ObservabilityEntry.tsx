import ErrorBoundary from '../components/ErrorBoundary';
import EurekaSidebar from '../components/layout/EurekaSidebar';
import ObservabilityConsole from '../components/observability/ObservabilityConsole';

/**
 * ObservabilityEntry — the PRODUCTIVE observability entry (not DEV-only).
 *
 * Reuses the existing productive shell (EurekaSidebar) + the already-closed read-only
 * ObservabilityConsole (CANONICAL / HYPOTHETICAL / EVIDENCE domains). This is presentation/routing
 * only: it adds NO domain expansion, NO backend, NO authority, NO persistence, NO Work↔Scenario
 * relationship, and NO Release. The console consumes only real, server-authoritative data.
 */
export default function ObservabilityEntry() {
  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden">
        <EurekaSidebar />
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <ObservabilityConsole />
        </div>
      </div>
    </ErrorBoundary>
  );
}
