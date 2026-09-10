import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Settings as SettingsIcon, ShieldAlert, Database, Paintbrush } from "lucide-react";
import { useAuthStore, isAdmin } from "../../store/authStore";
import AdminConsole from "../admin/AdminConsole";

export default function Settings() {
  const { user } = useAuthStore();
  const admin = isAdmin(user?.role);

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-text">Platform Settings</h1>
        <p className="text-text-muted mt-1 text-sm">Configure EUREKA environment variables, appearance, and strictness.</p>
      </div>

      {/* ADMINISTRATION — visible only to administrators; /api/admin/* is server-authoritative */}
      {admin && (
        <div className="mb-8 rounded-xl border border-border overflow-hidden" style={{ background: 'var(--eureka-canvas)', padding: '22px' }}>
          <AdminConsole />
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        <Card className="bg-surface-elevated border-border">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Paintbrush className="h-5 w-5 text-text-muted" />
              Appearance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-text-secondary">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>Theme</span>
              <span className="font-medium text-text bg-surface px-2 py-1 rounded">Dark Intelligence</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>Motion & Animations</span>
              <span className="font-medium text-text bg-surface px-2 py-1 rounded">Enabled</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated border-border">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-governance" />
              Governance Strictness
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-text-secondary">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>Semantic Validation</span>
              <span className="font-medium text-text bg-surface px-2 py-1 rounded">STRICT_ACFL</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>Human-in-the-Loop Required</span>
              <span className="font-medium text-governance bg-governance/10 px-2 py-1 rounded">ALWAYS</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated border-border col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Database className="h-5 w-5 text-scientific" />
              Repository Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-text-secondary">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>Data Source</span>
              <span className="font-medium text-scientific bg-scientific/10 px-2 py-1 rounded">DemoDecisionRepository (MOCK)</span>
            </div>
            <p className="text-xs text-text-muted pt-2">
              To connect to the live Python FastAPI backend, switch the Repository Provider to <code>FastAPIDecisionRepository</code> in the runtime configuration.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}