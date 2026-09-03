import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import {
  LayoutDashboard, FolderOpen, Database, MessagesSquare, FileCode2, LineChart, 
  Target, Calculator, Scale, AlertTriangle, ShieldCheck, PlayCircle, History, 
  Settings, Box, CheckCircle2, Lock, Unlock
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: any;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "WORKSPACE",
    items: [
      { name: "Overview", href: "/", icon: LayoutDashboard },
      { name: "Cases", href: "/cases", icon: FolderOpen },
      { name: "Files", href: "/files", icon: FileCode2 },
      { name: "Data", href: "/data", icon: Database },
    ]
  },
  {
    label: "COGNITIVE",
    items: [
      { name: "Eureka Chat", href: "/chat", icon: MessagesSquare },
      { name: "Agent Sandbox", href: "/sandbox", icon: Box },
    ]
  },
  {
    label: "ANALYTICS",
    items: [
      { name: "Dashboard", href: "/analytics", icon: LineChart },
      { name: "Explorer", href: "/analytics/explorer", icon: LineChart },
      { name: "Scenarios", href: "/analytics/scenarios", icon: Target },
      { name: "Networks", href: "/analytics/networks", icon: Target },
    ]
  },
  {
    label: "DECISION",
    items: [
      { name: "Objective", href: "/decision/objective", icon: Target },
      { name: "Predicate", href: "/decision/predicate", icon: FileCode2 },
      { name: "Evaluations", href: "/decision/evaluations", icon: Calculator },
      { name: "Ranking", href: "/decision/ranking", icon: Scale },
      { name: "Selection", href: "/decision/selection", icon: CheckCircle2 },
      { name: "Prescription", href: "/decision/prescription", icon: FileCode2 },
    ]
  },
  {
    label: "GOVERNANCE",
    items: [
      { name: "Authority", href: "/governance/authority", icon: ShieldCheck },
      { name: "Freezer", href: "/governance/freezer", icon: Lock },
      { name: "Unfreezer", href: "/governance/unfreezer", icon: Unlock },
      { name: "Actioner", href: "/governance/actioner", icon: AlertTriangle },
    ]
  },
  {
    label: "STORY",
    items: [
      { name: "Executive View", href: "/story/executive", icon: PlayCircle },
      { name: "Technical View", href: "/story/technical", icon: PlayCircle },
      { name: "Timeline", href: "/story/timeline", icon: History },
    ]
  },
  {
    label: "SYSTEM",
    items: [
      { name: "Agents", href: "/agents", icon: Box },
      { name: "Runtime", href: "/runtime", icon: Settings },
      { name: "Audit", href: "/audit", icon: ShieldCheck },
      { name: "Settings", href: "/settings", icon: Settings },
    ]
  }
];

export function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 border-r border-white/5 bg-surface-elevated/50 overflow-y-auto">
      <div className="p-4 border-b border-white/5">
        <h2 className="text-lg font-bold tracking-widest text-text-primary">EUREKA</h2>
        <p className="text-xs text-text-muted">Decision Intelligence OS</p>
      </div>
      <nav className="p-4 space-y-6">
        {navGroups.map((group) => (
          <div key={group.label}>
            <h3 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
              {group.label}
            </h3>
            <ul className="space-y-1">
              {group.items.map((item) => (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-md px-2 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-cognitive/10 text-cognitive font-medium"
                          : "text-text-secondary hover:bg-white/5 hover:text-text-primary"
                      )
                    }
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
