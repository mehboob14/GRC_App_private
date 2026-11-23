import { Outlet } from "react-router-dom";
import { PageHeader, SegmentedControl, TabStrip, type TabStripItem } from "@/components/ui";
import { frameworkSearch, useSelectedFramework } from "../use-frameworks";

/** Scope is a property of the framework you are being audited against, so it
 *  lives inside Frameworks rather than competing with it in the sidebar.
 *
 *  Scope and Coverage were one tab, which put two different jobs on one screen:
 *  Scope is a form you fill in once, Coverage is a report you come back to.
 *
 *  A workspace on more than one framework gets a switch beside the title, and
 *  the choice rides in the address so every tab, a refresh and a shared link
 *  keep it. A workspace on SOC 2 alone sees exactly what it always saw. */
export function FrameworksLayout() {
  const { added, selected, code, select } = useSelectedFramework();
  const search = frameworkSearch(code);

  const tabs: TabStripItem[] = [
    { id: `/frameworks/dashboard${search}`, label: "Dashboard", end: false },
    { id: `/frameworks/list${search}`, label: "Frameworks", end: false },
    { id: `/frameworks/scope${search}`, label: "Scope", end: false },
    // Only a framework that works by applicability has a statement to keep.
    ...(selected?.added && selected.scope_model === "applicability"
      ? [{ id: `/frameworks/soa${search}`, label: "Applicability", end: false }]
      : []),
    { id: `/frameworks/objectives${search}`, label: "Objectives", end: false },
    ...(selected?.added ? [{ id: `/frameworks/assurance${search}`, label: "Audits", end: false }] : []),
    ...(selected?.added && selected.scope_model === "categories"
      ? [{ id: `/frameworks/description${search}`, label: "Description", end: false }]
      : []),
  ];

  return (
    <div className="w-full">
      <PageHeader
        title="Frameworks"
        icon="shield"
        actions={
          added.length > 1 ? (
            <SegmentedControl
              label="Framework"
              items={added.map((f) => ({ id: f.code, label: f.name }))}
              value={selected?.added ? code : added[0].code}
              onChange={select}
            />
          ) : undefined
        }
      />
      <TabStrip label="Framework sections" items={tabs} variant="bar" />
      <Outlet />
    </div>
  );
}
