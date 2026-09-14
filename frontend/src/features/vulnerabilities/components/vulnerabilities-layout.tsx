import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Icon, PageHeader, TabStrip, type TabStripItem } from "@/components/ui";
import { downloadVulnImportTemplate, vulnerabilityKpis } from "../api";
import type { VulnInstance } from "../types";
import { AddFindingDrawer } from "./add-finding-drawer";
import type { VulnerabilitiesOutlet } from "./vulnerabilities-outlet";

/** Import and a finding's own page are drill-downs and sit outside this strip. */
const TABS: TabStripItem[] = [
  { id: "/vulnerabilities/overview", label: "Overview" },
  { id: "/vulnerabilities", label: "Register", end: true },
  { id: "/vulnerabilities/settings", label: "Settings" },
];

const EXPORT_COLUMNS = [
  "id", "title", "cve_id", "cwe_id", "severity", "cvss_score", "cvss_vector",
  "epss_score", "priority_band", "risk_score", "state", "kev_flag",
  "public_exploit_count", "patch_available", "asset_name", "owner_name",
  "sla_due_at", "overdue",
] as const;

/** The register's rows, with every filter applied, as a CSV download. */
function exportCsv(rows: VulnInstance[]) {
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const lines = rows.map((v) =>
    EXPORT_COLUMNS.map((c) => esc(v[c] == null ? "" : String(v[c]))).join(","),
  );
  const csv = `${EXPORT_COLUMNS.join(",")}\n${lines.join("\n")}\n`;
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "vulnerabilities.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export function VulnerabilitiesLayout() {
  const navigate = useNavigate();
  const [addOpen, setAddOpen] = useState(false);
  const [exportRows, setExportRows] = useState<VulnInstance[] | null>(null);

  // Same key the pages use, so react-query serves it from cache.
  const kpisQuery = useQuery({ queryKey: ["vuln-kpis"], queryFn: vulnerabilityKpis });
  const k = kpisQuery.data;
  const subtitle = k
    ? [
        `${k.open_total} open`,
        k.open_by_severity.critical ? `${k.open_by_severity.critical} critical` : null,
        k.overdue ? `${k.overdue} overdue` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Security findings";

  const tabs = TABS.map((t) => (t.id === "/vulnerabilities" ? { ...t, count: k?.open_total } : t));

  return (
    <div className="w-full">
      <PageHeader
        title="Vulnerabilities"
        icon="bug"
        subtitle={subtitle}
        actions={
          <>
            {exportRows ? (
              <Button variant="secondary" onClick={() => exportCsv(exportRows)}>
                <Icon name="export" className="size-4" />
                Export
              </Button>
            ) : null}
            <Button variant="secondary" onClick={() => downloadVulnImportTemplate()}>
              <Icon name="spreadsheet" className="size-4" />
              Template
            </Button>
            <Button variant="secondary" onClick={() => navigate("/vulnerabilities/import")}>
              <Icon name="upload" className="size-4" />
              Import
            </Button>
            <Button onClick={() => setAddOpen(true)}>
              <Icon name="plus" className="size-4" />
              Add finding
            </Button>
          </>
        }
      />
      <TabStrip label="Vulnerability sections" items={tabs} variant="bar" />
      <Outlet
        context={{ openAddFinding: () => setAddOpen(true), setExportRows } satisfies VulnerabilitiesOutlet}
      />
      <AddFindingDrawer open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}
