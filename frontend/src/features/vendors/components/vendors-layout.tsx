import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Icon, PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getSummary, listFindings, listIntake } from "../api";
import { RequestVendorDialog } from "./request-vendor-dialog";
import { VendorFormDrawer } from "./vendor-form-drawer";
import type { VendorsOutlet } from "./vendors-outlet";


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
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const [formOpen, setFormOpen] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);

  const summaryQuery = useQuery({ queryKey: ["vendor-summary"], queryFn: getSummary });
  const summary = summaryQuery.data;
  const subtitle = summary
    ? [
        `${summary.total} ${summary.total === 1 ? "vendor" : "vendors"}`,
        summary.by_tier.critical ? `${summary.by_tier.critical} critical` : null,
        summary.findings_open ? `${summary.findings_open} open findings` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Third-party risk";

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
      <PageHeader
        title="Vendors"
        icon="vendor"
        subtitle={subtitle}
        actions={
          <>
            <Button variant="secondary" onClick={() => setRequestOpen(true)}>
              <Icon name="doc" className="size-4" />
              Request vendor
            </Button>
            {canManage ? (
              <Button onClick={() => setFormOpen(true)}>
                <Icon name="plus" className="size-4" />
                Add vendor
              </Button>
            ) : null}
          </>
        }
      />
      <TabStrip label="Vendor sections" items={tabs} variant="bar" />
      <Outlet context={{ addVendor: () => setFormOpen(true) } satisfies VendorsOutlet} />
      <VendorFormDrawer open={formOpen} onOpenChange={setFormOpen} />
      <RequestVendorDialog open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}
