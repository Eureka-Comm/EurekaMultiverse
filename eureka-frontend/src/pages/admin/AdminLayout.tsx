import EurekaSidebar from '../../components/layout/EurekaSidebar';
import EurekaTopBar from '../../components/layout/EurekaTopBar';

// EUREKA app shell for a module page (reuses the SAME sidebar + a top bar).
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-canvas text-text-section">
      <EurekaSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <EurekaTopBar />
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>
    </div>
  );
}
