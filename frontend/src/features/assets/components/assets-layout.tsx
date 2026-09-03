import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { getSummary } from "../api";

/** Assets is a small workspace: the register is the day-to-day inventory,
 *  Overview is the read on the whole estate. Detail, form and import sit outside
 *  this strip — they are drill-downs, not tabs. */
const TABS: TabStripItem[] = [
  { id: "/assets/overview", label: "Overview" },
  { id: "/assets", label: "Register", end: true },
];

export function AssetsLayout() {
  // Same query key the register and overview use, so react-query serves it from
  // cache — the tab count costs no extra request.
  const summaryQuery = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });

  const tabs = TABS.map((t) =>
    t.id === "/assets" ? { ...t, count: summaryQuery.data?.total } : t,
  );

  return (
    <div className="w-full">
      <PageHeader eyebrow="Inventory" title="Assets" />
      <TabStrip label="Asset sections" items={tabs} />
      <Outlet />
    </div>
  );
}
