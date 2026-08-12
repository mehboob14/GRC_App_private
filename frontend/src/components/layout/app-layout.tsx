import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-full min-h-0 bg-surface-page">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="min-h-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
