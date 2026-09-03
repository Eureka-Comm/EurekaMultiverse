import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const navigate = useNavigate();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (action: () => void) => {
    action();
    setOpen(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed left-[50%] top-[20%] z-50 w-full max-w-lg translate-x-[-50%] rounded-xl border border-white/10 bg-surface shadow-2xl overflow-hidden p-0">
          <div className="flex items-center border-b border-white/10 px-4">
            <Search className="mr-2 h-5 w-5 text-text-muted" />
            <input
              placeholder="Search or type a command (⌘K)..."
              className="flex h-14 w-full bg-transparent py-3 text-sm outline-none placeholder:text-text-muted text-text-primary"
              autoFocus
            />
          </div>
          <div className="max-h-[300px] overflow-y-auto p-2">
            <div className="px-2 py-1.5 text-xs font-medium text-text-muted">Suggestions</div>
            <button
              onClick={() => runCommand(() => navigate("/cases/new"))}
              className="w-full text-left rounded-md px-3 py-2 text-sm hover:bg-surface-elevated text-text-primary"
            >
              New Case
            </button>
            <button
              onClick={() => runCommand(() => navigate("/chat"))}
              className="w-full text-left rounded-md px-3 py-2 text-sm hover:bg-surface-elevated text-text-primary"
            >
              Ask Eureka
            </button>
            <button
              onClick={() => runCommand(() => navigate("/decision/ranking"))}
              className="w-full text-left rounded-md px-3 py-2 text-sm hover:bg-surface-elevated text-text-primary"
            >
              Open Ranking
            </button>
            <button
              onClick={() => runCommand(() => navigate("/governance/freezer"))}
              className="w-full text-left rounded-md px-3 py-2 text-sm hover:bg-surface-elevated text-text-primary"
            >
              Open Frozen Decisions
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
