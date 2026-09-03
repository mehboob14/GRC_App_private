import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { getSummary } from "../api";

/** Tasks is a small workspace of its own: the register is the day-to-day view,
 *  Overview is the read on the whole queue, Settings holds the SLA matrix and
 *  templates. Detail sits outside this strip — it is a drill-down, not a tab. */
const TABS: TabStripItem[] = [
  { id: "/tasks/overview", label: "Overview" },
  { id: "/tasks", label: "Register", end: true },
  { id: "/tasks/settings", label: "Settings" },
];

export function TasksLayout() {
  // Same query key the register and overview use, so react-query serves it from
  // cache. The summary only exposes open_total, so the badge counts OPEN tasks —
  // which is what the register itself reports.
  const summaryQuery = useQuery({ queryKey: ["task-summary"], queryFn: getSummary });

  const tabs = TABS.map((t) =>
    t.id === "/tasks" ? { ...t, count: summaryQuery.data?.open_total } : t,
  );

  return (
    <div className="w-full">
      <PageHeader eyebrow="Operations" title="Tasks and issues" />
      <TabStrip label="Task sections" items={tabs} />
      <Outlet />
    </div>
  );
}
