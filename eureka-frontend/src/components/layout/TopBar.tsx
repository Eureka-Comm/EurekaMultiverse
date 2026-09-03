import { Badge } from "../ui/Badge";
import { Bell, Search } from "lucide-react";

export function TopBar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-white/5 bg-surface px-6">
      <div className="flex items-center gap-4">
        <div className="flex flex-col">
          <span className="text-xs text-text-muted">Workspace</span>
          <span className="text-sm font-medium">Strategic Planning</span>
        </div>
        <div className="h-6 w-px bg-white/10" />
        <div className="flex flex-col">
          <span className="text-xs text-text-muted">Current Case</span>
          <span className="text-sm font-medium text-cognitive">Q4 Expansion (case-001)</span>
        </div>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Runtime:</span>
          <Badge variant="outline" className="border-cognitive/50 text-cognitive">LOCAL</Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Agent:</span>
          <Badge variant="outline">DeepSeek</Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Governance:</span>
          <Badge variant="governance" className="gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-governance" />
            GOVERNED
          </Badge>
        </div>
        <div className="flex items-center gap-4 border-l border-white/10 pl-6">
          <button className="text-text-muted hover:text-text-primary">
            <Search className="h-4 w-4" />
          </button>
          <button className="text-text-muted hover:text-text-primary">
            <Bell className="h-4 w-4" />
          </button>
          <div className="h-8 w-8 rounded-full bg-surface-elevated border border-white/10 flex items-center justify-center text-xs font-medium">
            JD
          </div>
        </div>
      </div>
    </header>
  );
}
