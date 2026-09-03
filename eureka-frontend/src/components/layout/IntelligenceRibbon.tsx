import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import {
  Brain,
  Database,
  FolderOpen,
  LayoutDashboard,
  Network,
  Settings,
  Shield,
  Activity,
  History,
  Workflow
} from "lucide-react";

const NAV_ITEMS = [
  { group: "WORKSPACE", items: [
    { icon: LayoutDashboard, label: "Overview", path: "/" },
    { icon: FolderOpen, label: "Cases", path: "/cases" },
    { icon: Database, label: "Data", path: "/data" },
  ]},
  { group: "COGNITIVE", items: [
    { icon: Brain, label: "Sandbox", path: "/sandbox" },
  ]},
  { group: "INTELLIGENCE", items: [
    { icon: Network, label: "Decision Field", path: "/decision/objective" },
    { icon: Activity, label: "Analytics", path: "/analytics" },
  ]},
  { group: "GOVERNANCE", items: [
    { icon: Shield, label: "Authority", path: "/governance/authority" },
    { icon: Workflow, label: "Actioner", path: "/governance/actioner" },
  ]},
  { group: "SYSTEM", items: [
    { icon: History, label: "Audit", path: "/audit" },
    { icon: Settings, label: "Settings", path: "/settings" },
  ]},
];

export function IntelligenceRibbon() {
  return (
    <nav className="w-16 md:w-64 flex flex-col border-r border-[var(--eureka-spatial-hairline)] bg-surface shrink-0 h-full overflow-y-auto">
      <div className="p-4 border-b border-[var(--eureka-spatial-hairline)]">
        <div className="flex items-center gap-3 text-text-display font-bold tracking-wider">
          <div className="w-6 h-6 rounded bg-signal-cognitive flex items-center justify-center shrink-0">
            <div className="w-2 h-2 bg-canvas rounded-sm" />
          </div>
          <span className="hidden md:block uppercase text-xs">Intelligence Fabric</span>
        </div>
      </div>

      <div className="flex-1 py-4 flex flex-col gap-6">
        {NAV_ITEMS.map((group, i) => (
          <div key={i} className="flex flex-col gap-1">
            <div className="px-4 text-[10px] uppercase font-mono text-text-micro tracking-widest hidden md:block mb-1">
              {group.group}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-4 py-2 mx-2 rounded text-sm transition-colors relative",
                    isActive 
                      ? "bg-surface-selected text-text-display font-medium" 
                      : "text-text-technical hover:text-text-section hover:bg-surface-elevated"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon className={cn("w-4 h-4 shrink-0", isActive && "text-signal-cognitive")} />
                    <span className="hidden md:block">{item.label}</span>
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 bg-signal-cognitive rounded-r" />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}
