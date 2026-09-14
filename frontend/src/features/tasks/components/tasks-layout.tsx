import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Icon, PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { getSummary } from "../api";
import { TaskFormDialog } from "./task-form-dialog";
import type { TasksOutlet } from "./tasks-outlet";

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
  const [creating, setCreating] = useState(false);
  const summary = summaryQuery.data;
  const subtitle = summary
    ? [
        `${summary.open_total} open`,
        summary.breaching_now ? `${summary.breaching_now} overdue` : null,
        summary.due_soon ? `${summary.due_soon} due soon` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Tasks and issues";

  const tabs = TABS.map((t) =>
    t.id === "/tasks" ? { ...t, count: summaryQuery.data?.open_total } : t,
  );

  return (
    <div className="w-full">
      <PageHeader
        title="Tasks and issues"
        icon="list"
        subtitle={subtitle}
        actions={
          <Button onClick={() => setCreating(true)}>
            <Icon name="plus" className="size-4" />
            New task
          </Button>
        }
      />
      <TabStrip label="Task sections" items={tabs} variant="bar" />
      <Outlet context={{ addTask: () => setCreating(true) } satisfies TasksOutlet} />
      <TaskFormDialog mode="create" open={creating} onOpenChange={setCreating} />
    </div>
  );
}
