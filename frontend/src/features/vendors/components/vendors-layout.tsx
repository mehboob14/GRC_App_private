import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { listFindings, listIntake } from "../api";

/**
 * The module-root surfaces.
 *
 * Overview is the portfolio picture and stays the first thing offered, but the
 * register remains the index route so every existing /vendors link still lands
 * on the table. Intake is the queue of requests that have not become vendors
 * yet. Findings is the cross-vendor work list. Roster is who plays which role in
 * the programme — settings, but named for what it holds.
 *
 * A vendor's own pages (detail, questionnaire) are drill-downs and sit outside
 * this strip.
 */
const TABS: TabStripItem[] = [
  { id: "/vendors/overview", label: "Overview" },
  { id: "/vendors", label: "Register", end: true },
  { id: "/vendors/intake", label: "Intake" },
  { id: "/vendors/findings", label: "Findings" },
  { id: "/vendors/roster", label: "Roster" },
];

export function VendorsLayout() {
  // Both counts are the queue length a person is expected to act on, not a
  // total: requests awaiting a decision, and findings still open. The same
  // query keys the two pages use, so react-query serves them from cache.
  const intakeQuery = useQuery({
    queryKey: ["vendor-intake", "pending"],
    queryFn: () => listIntake("pending"),
  });
  const findingsQuery = useQuery({
    queryKey: ["vendor-findings", { statuses: ["open", "in_remediation"] }],
    queryFn: () => listFindings({ statuses: ["open", "in_remediation"] }),
  });

  // Pass undefined while a count is in flight — TabStrip renders a badge only
  // for a real number, so a loading tab shows nothing rather than a false zero.
  const tabs = TABS.map((t) => {
    if (t.id === "/vendors/intake") return { ...t, count: intakeQuery.data?.total || undefined };
    if (t.id === "/vendors/findings") return { ...t, count: findingsQuery.data?.total || undefined };
    return t;
  });

  return (
    <div className="w-full">
      <PageHeader eyebrow="Risk" title="Vendors" />
      <TabStrip label="Vendor sections" items={tabs} />
      <Outlet />
    </div>
  );
}
