import { Outlet } from "react-router-dom";
import { PageHeader, TabStrip, type TabStripItem } from "@/components/ui";

/** Scope is a property of the framework you are being audited against, so it
 *  lives inside Frameworks rather than competing with it in the sidebar.
 *
 *  Scope and Coverage were one tab, which put two different jobs on one screen:
 *  Scope is a form you fill in once, Coverage is a report you come back to. */
const TABS: TabStripItem[] = [
  { id: "/frameworks/dashboard", label: "Dashboard", end: false },
  { id: "/frameworks/list", label: "Frameworks", end: false },
  { id: "/frameworks/scope", label: "Scope", end: false },
];

export function FrameworksLayout() {
  return (
    <div className="w-full">
      <PageHeader eyebrow="Compliance" title="Frameworks" />
      <TabStrip label="Framework sections" items={TABS} />
      <Outlet />
    </div>
  );
}
