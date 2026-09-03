import { Activity } from "lucide-react";

export function StatusBar() {
  return (
    <footer className="flex h-8 items-center justify-between border-t border-white/5 bg-surface-elevated/30 px-4 text-xs text-text-muted">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-human" />
          System Active
        </span>
        <span>Version 1.0.0-MVP</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <Activity className="h-3 w-3" />
          Zero-Cost Local Mode
        </span>
        <span className="text-blocked">Network OFF</span>
      </div>
    </footer>
  );
}
