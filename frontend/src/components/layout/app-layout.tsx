import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { ShellHeaderProvider } from "@/components/layout/shell-header";
import { BrandingEffects } from "@/features/tenancy/branding-effects";

export function AppLayout() {
  return (
    <ShellHeaderProvider>
      <BrandingEffects />
      <div className="flex h-full min-h-0 bg-surface-page">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main className="min-h-0 flex-1 overflow-auto px-5 py-4">
            <Outlet />
          </main>
        </div>
      </div>
    </ShellHeaderProvider>
  );
}
