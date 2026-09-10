import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

const KEY = 'eureka-theme';

export function ThemeToggle() {
  const [light, setLight] = useState<boolean>(() => localStorage.getItem(KEY) === 'light');

  useEffect(() => {
    document.documentElement.classList.toggle('theme-light', light);
    localStorage.setItem(KEY, light ? 'light' : 'dark');
  }, [light]);

  return (
    <button
      onClick={() => setLight((l) => !l)}
      title={light ? 'Cambiar a oscuro cósmico' : 'Cambiar a claro'}
      className="flex items-center gap-1.5 rounded-md border border-[var(--eureka-spatial-hairline)] bg-surface/40 px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest text-text-technical transition hover:border-signal-cognitive/50 hover:text-text-display"
    >
      {light ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
      <span className="hidden lg:inline">{light ? 'Dark' : 'Light'}</span>
    </button>
  );
}
