import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";

const NAV_ITEMS = [
  { id: "overview", path: "/", icon: "⎈", label: "Field" },
  { id: "cognitive", path: "/cognitive", icon: "⌬", label: "Cognitive" },
  { id: "analytics", path: "/analytics", icon: "◱", label: "Analytics" },
  { id: "governance", path: "/governance", icon: "⚖", label: "Governance" },
];

export function LeftRibbon() {
  return (
    <div className="w-16 h-full flex flex-col items-center py-4 bg-surface-elevated border-r border-[var(--eureka-border)]">
      <div className="w-8 h-8 bg-text-primary rounded mb-8 flex items-center justify-center text-canvas font-bold text-xs">
        EU
      </div>
      
      <div className="flex flex-col gap-4 flex-1 w-full px-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "w-full aspect-square flex flex-col items-center justify-center rounded-md text-text-muted transition-all duration-300",
                isActive 
                  ? "bg-surface-active text-cognitive shadow-[var(--eureka-glow-cognitive)] border border-[rgba(0,240,255,0.2)]" 
                  : "hover:text-text-primary hover:bg-[var(--eureka-surface-hover)]"
              )
            }
            title={item.label}
          >
            <span className="text-xl leading-none">{item.icon}</span>
          </NavLink>
        ))}
      </div>
      
      <div className="w-10 h-10 rounded-full bg-surface border border-[var(--eureka-border)] flex items-center justify-center text-text-muted text-xs cursor-pointer hover:border-human hover:text-human transition-colors">
        SYS
      </div>
    </div>
  );
}
