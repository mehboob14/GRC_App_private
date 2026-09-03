import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, DetailHeader, Icon, TextField, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  VULN_TEMPLATE_COLUMNS,
  downloadVulnImportTemplate,
  downloadVulnReport,
  importVulnerabilities,
  listVulnReports,
  reparseVulnReport,
} from "../api";
import type { ImportResult, VulnReport } from "../types";
import { ManualAddFinding } from "./manual-add-finding";

// Column names shown under the upload card — the parser's canonical columns,
// with the first two collapsed to "asset OR asset_id". The template download
// and its column list are the shared api helpers.
const CSV_COLUMNS = ["asset OR asset_id", ...VULN_TEMPLATE_COLUMNS.slice(2)];

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="mb-3 font-display text-title-sm text-text-primary">{title}</h2>
      {children}
    </div>
  );
}

export function VulnerabilitiesImportPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [reportName, setReportName] = useState("");
  const [scanTool, setScanTool] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);

  const runImport = useMutation({
    mutationFn: () => importVulnerabilities(file!, reportName.trim(), "vulnerability_scan", scanTool || undefined),
    onSuccess: (r) => {
      setResult(r);
      queryClient.invalidateQueries({ queryKey: ["vuln-reports"] });
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      if (r.status === "failed") {
        toast({ title: r.parse_error ?? "The file couldn't be parsed.", tone: "danger" });
      } else {
        toast({ title: `Imported ${r.created + r.resurfaced} findings`, tone: "success" });
      }
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "import"), tone: "danger" }),
  });

  return (
    <div className="w-full">
      <DetailHeader
        backTo="/vulnerabilities"
        backLabel="Back to vulnerabilities"
        title="Import findings"
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Upload a CSV">
          <div className="space-y-3">
            <p className="text-body-sm text-text-subtle">
              Upload a scanner export (CSV, Excel, or XML including Nessus{" "}
              <span className="font-mono">.nessus</span>). Findings are matched to assets by{" "}
              <span className="font-mono">asset_id</span> or by name, enriched with live
              EPSS/KEV/exploit data, and prioritised automatically. Live scanner connectors arrive
              in Phase 3.
            </p>
            <TextField
              label="Report name"
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              placeholder="e.g. Q3 external scan"
            />
            <TextField
              label="Scanner (optional)"
              value={scanTool}
              onChange={(e) => setScanTool(e.target.value)}
              placeholder="nessus, qualys, burp…"
            />
            <div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xml,.nessus,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/xml"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-border py-4 text-body-sm text-text-subtle transition-colors hover:border-border-strong hover:text-text-primary"
              >
                <Icon name="download" className="size-4" />
                {file ? file.name : "Choose a file (CSV, Excel, or XML)"}
              </button>
            </div>
            <Button
              className="w-full"
              disabled={!file || reportName.trim() === ""}
              loading={runImport.isPending}
              onClick={() => runImport.mutate()}
            >
              Import
            </Button>
            <div className="flex items-center justify-between gap-2">
              <p className="text-caption text-text-subtle">
                New to the format?{" "}
                <button
                  type="button"
                  onClick={() => downloadVulnImportTemplate()}
                  className="font-semibold text-text-link hover:underline"
                >
                  Download template
                </button>
              </p>
            </div>
            <p className="text-caption text-text-subtle">
              Columns: {CSV_COLUMNS.map((c) => (
                <span key={c} className="mr-1.5 font-mono">
                  {c}
                </span>
              ))}
            </p>
            {result ? (
              <div className="rounded-md border border-border bg-surface-hover p-3 text-body-sm text-text-secondary">
                <p className="font-semibold text-text-primary">Imported</p>
                <p>
                  {result.created} new · {result.resurfaced} resurfaced · {result.updated} updated ·{" "}
                  {result.unmatched} unmatched ({result.definitions} definitions)
                </p>
                <Link to="/vulnerabilities" className="mt-1 inline-block text-text-link">
                  View the register →
                </Link>
              </div>
            ) : null}
          </div>
        </Card>

        <Card title="Add one finding">
          <ManualAddFinding onAdded={(id) => navigate(`/vulnerabilities/${id}`)} />
        </Card>
      </div>

      <div className="mt-4">
        <Card title="Uploaded reports">
          <ReportsList />
        </Card>
      </div>
    </div>
  );
}

const REPORT_STATUS: Record<string, { label: string; variant: "statusPass" | "statusFail" | "statusReview" | "neutral" }> = {
  parsed: { label: "Parsed", variant: "statusPass" },
  failed: { label: "Failed", variant: "statusFail" },
  parsing: { label: "Parsing", variant: "statusReview" },
  uploaded: { label: "Uploaded", variant: "neutral" },
};

function ReportsList() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const reportsQuery = useQuery({ queryKey: ["vuln-reports"], queryFn: listVulnReports });

  const reparse = useMutation({
    mutationFn: (id: string) => reparseVulnReport(id),
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["vuln-reports"] });
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      toast({ title: `Reparsed, ${r.created + r.resurfaced} findings`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "report"), tone: "danger" }),
  });

  async function download(report: VulnReport) {
    try {
      const blob = await downloadVulnReport(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = report.file_name ?? "report";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: errorToast(e, "report file"), tone: "danger" });
    }
  }

  const reports = reportsQuery.data ?? [];
  // A failed load is not "no reports", so this comes before the empty line.
  if (reportsQuery.isError) {
    return (
      <p className="text-body-sm text-status-danger-text">
        {describeError(reportsQuery.error, "report list").message}
      </p>
    );
  }
  if (reports.length === 0) {
    return <p className="text-body-sm text-text-subtle">No reports uploaded yet.</p>;
  }

  return (
    <ul className="divide-y divide-border">
      {reports.map((r) => {
        const st = REPORT_STATUS[r.status] ?? REPORT_STATUS.uploaded;
        return (
          <li key={r.id} className="flex items-center gap-3 py-2.5">
            <div className="min-w-0 flex-1">
              <p className="truncate text-body-sm font-semibold text-text-primary">{r.name}</p>
              <p className="truncate text-caption text-text-subtle">
                {r.scan_tool ? `${r.scan_tool} · ` : ""}
                {r.total_count} findings
                {r.critical_count ? ` · ${r.critical_count} critical` : ""}
                {r.uploaded_by_name ? ` · by ${r.uploaded_by_name}` : ""}
                {r.parse_error ? ` · ${r.parse_error}` : ""}
              </p>
            </div>
            <Badge variant={st.variant}>{st.label}</Badge>
            {r.has_file ? (
              <button
                type="button"
                onClick={() => download(r)}
                aria-label="Download report"
                className="text-text-subtle transition-colors hover:text-text-primary"
              >
                <Icon name="download" className="size-4" />
              </button>
            ) : null}
            {r.has_file ? (
              <Button
                size="sm"
                variant="secondary"
                loading={reparse.isPending && reparse.variables === r.id}
                onClick={() => reparse.mutate(r.id)}
              >
                Reparse
              </Button>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
