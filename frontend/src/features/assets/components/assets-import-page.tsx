import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  DetailHeader,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { ASSET_TEMPLATE_COLUMNS, assetImportTemplateCsv, importAssets, listMembers, type AssetInput } from "../api";
import {
  ASSET_TYPES,
  CRITICALITY_TIERS,
  DATA_CLASSIFICATIONS,
  type AssetType,
  type CiaRating,
  type CriticalityTier,
  type DataClassification,
  type Member,
} from "../types";
import { ASSET_TYPE_META } from "../tokens";

type ParsedRow = { line: number; input: AssetInput; errors: string[] };

/** Minimal CSV parse with quoted-field support — the real backend uses a proper
 *  parser (and reads Excel); this is enough for the in-browser preview. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.some((c) => c.trim() !== "")) rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field !== "" || row.length) {
    row.push(field);
    if (row.some((c) => c.trim() !== "")) rows.push(row);
  }
  return rows;
}

function cia(raw: string, field: string, errors: string[]): CiaRating | null {
  const v = raw.trim();
  if (!v) return null;
  const n = Number(v);
  if (!Number.isInteger(n) || n < 1 || n > 5) {
    errors.push(`${field} must be 1 to 5`);
    return null;
  }
  return n as CiaRating;
}

function bool(raw: string): boolean {
  return ["true", "yes", "1", "y"].includes(raw.trim().toLowerCase());
}

function mapRow(header: string[], cells: string[], line: number, members: Member[]): ParsedRow {
  const errors: string[] = [];
  const get = (col: string) => cells[header.indexOf(col)]?.trim() ?? "";

  const name = get("name");
  if (!name) errors.push("name is required");

  const rawType = get("asset_type");
  if (!ASSET_TYPES.includes(rawType as AssetType)) errors.push(`asset_type "${rawType}" is not valid`);

  const rawClass = get("data_classification");
  const data_classification = rawClass && DATA_CLASSIFICATIONS.includes(rawClass as DataClassification) ? (rawClass as DataClassification) : null;
  if (rawClass && !data_classification) errors.push(`data_classification "${rawClass}" is not valid`);

  const rawTier = get("criticality");
  const tier_override = rawTier && CRITICALITY_TIERS.includes(rawTier as CriticalityTier) ? (rawTier as CriticalityTier) : null;
  if (rawTier && !tier_override) errors.push(`criticality "${rawTier}" is not a valid tier`);

  const ownerName = get("owner_name");
  const owner = ownerName ? members.find((m) => m.name.toLowerCase() === ownerName.toLowerCase()) : undefined;
  if (ownerName && !owner) errors.push(`owner "${ownerName}" not found`);

  const valuationRaw = get("valuation");
  const valuation = valuationRaw ? Number(valuationRaw.replace(/[^0-9.]/g, "")) || null : null;

  const input: AssetInput = {
    name,
    asset_type: (ASSET_TYPES.includes(rawType as AssetType) ? rawType : "application") as AssetType,
    description: get("description"),
    hostname: get("host_name") || null,
    ip_address: get("ip_address") || null,
    environment: null,
    location: get("location") || null,
    vendor_ref: get("vendor") || null,
    data_classification,
    regulated_data_type: null,
    compliance_scope: get("compliance_scope").split(";").map((s) => s.trim()).filter(Boolean),
    internet_facing: bool(get("internet_facing")),
    customer_facing: false,
    network_segment: get("network_segment") || null,
    business_function: get("business_function") || null,
    confidentiality: cia(get("confidentiality_rating"), "confidentiality_rating", errors),
    integrity: cia(get("integrity_rating"), "integrity_rating", errors),
    availability: cia(get("availability_rating"), "availability_rating", errors),
    tier_override,
    tier_override_reason: get("criticality_override_reason") || null,
    primary_owner_id: owner?.membership_id ?? null,
    secondary_owner_id: null,
    business_owner_id: null,
    custodian_id: null,
    escalation_contact_id: null,
    owning_team: get("owning_team") || null,
    valuation,
    business_impact_notes: null,
    operational_dependency_rating: null,
  };
  return { line, input, errors };
}

export function AssetsImportPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<ParsedRow[] | null>(null);
  const [fileName, setFileName] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const membersQuery = useQuery({ queryKey: ["asset-members"], queryFn: listMembers });

  const valid = rows?.filter((r) => r.errors.length === 0) ?? [];
  const invalid = rows?.filter((r) => r.errors.length > 0) ?? [];

  function download() {
    const blob = new Blob([assetImportTemplateCsv()], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "asset-import-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function onFile(file: File) {
    setFileName(file.name);
    setParseError(null);
    setRows(null);
    const text = await file.text();
    const grid = parseCsv(text);
    if (grid.length < 2) {
      setParseError("The file has no data rows.");
      return;
    }
    const header = grid[0].map((h) => h.trim());
    const missing = ["name", "asset_type"].filter((c) => !header.includes(c));
    if (missing.length) {
      setParseError(`Missing required column(s): ${missing.join(", ")}. Download the template to see the expected columns.`);
      return;
    }
    setRows(grid.slice(1).map((cells, i) => mapRow(header, cells, i + 2, membersQuery.data ?? [])));
  }

  const commit = useMutation({
    mutationFn: () => importAssets(valid.map((r) => r.input)),
    onSuccess: (res) => {
      toast({ title: `Imported ${res.created} asset${res.created === 1 ? "" : "s"}`, tone: "success" });
      navigate("/assets");
    },
    onError: (error) => toast({ title: errorToast(error, "asset import"), tone: "danger" }),
  });

  return (
    <div className="w-full pb-16">
      <DetailHeader icon="upload" backTo="/assets" backLabel="Back to assets" title="Import assets" />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* CSV — available now. */}
        <div className="rounded-lg border border-border bg-surface-primary p-5">
          <h2 className="font-display text-title-sm text-text-primary">Upload a CSV</h2>
          <p className="mt-1 text-body-sm text-text-subtle">
            Download the template, fill it in, and upload. Criticality is derived from the CIA ratings.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={download}>
              Download template
            </Button>
            <Button onClick={() => fileInput.current?.click()}>Choose CSV</Button>
            {fileName ? <span className="text-body-sm text-text-subtle">{fileName}</span> : null}
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onFile(f);
                e.target.value = "";
              }}
            />
          </div>
          <p className="mt-3 text-caption text-text-subtle">
            Columns: {ASSET_TEMPLATE_COLUMNS.join(", ")}. Required: name, asset_type.
          </p>
          {/* Owner columns resolve against the member list, so say when it is missing. */}
          {membersQuery.isError ? (
            <p className="mt-2 text-body-sm text-status-danger-text">
              {describeError(membersQuery.error, "team list").message} Owner columns will not be matched.
            </p>
          ) : null}
        </div>

        {/* Scanners — automated discovery, coming soon. */}
        <div className="rounded-lg border border-border bg-surface-sunken/30 p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-display text-title-sm text-text-primary">Connect a scanner</h2>
            <Badge variant="neutral">Soon</Badge>
          </div>
          <p className="mt-1 text-body-sm text-text-subtle">
            Sync your inventory automatically and keep it current. Discovered hosts populate here with
            their last-seen time and open findings.
          </p>
          <ul className="mt-4 space-y-2">
            {["Tenable Nessus", "Qualys", "Microsoft Defender", "AWS Config"].map((name) => (
              <li
                key={name}
                className="flex items-center justify-between rounded-md border border-border bg-surface-primary px-3 py-2"
              >
                <span className="text-body-sm text-text-primary">{name}</span>
                <span className="text-caption text-text-subtle">Soon</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {parseError ? (
        <div className="mt-5 rounded-md border border-status-danger-border bg-status-danger-bg px-4 py-3 text-body-sm text-status-danger-text">
          {parseError}
        </div>
      ) : null}

      {rows ? (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-3 text-body-sm">
            <Badge variant="statusPass">{valid.length} ready</Badge>
            {invalid.length ? <Badge variant="statusFail">{invalid.length} with errors</Badge> : null}
          </div>
          <Table>
            <THead>
              <TR>
                <TH>Row</TH>
                <TH>Name</TH>
                <TH>Type</TH>
                <TH>CIA</TH>
                <TH>Owner</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {rows.map((r) => {
                const ok = r.errors.length === 0;
                const { confidentiality: c, integrity: i, availability: a } = r.input;
                return (
                  <TR key={r.line}>
                    <TD>
                      <span className="tabular text-caption text-text-subtle">{r.line}</span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-primary">{r.input.name || <span className="text-text-subtle">Missing</span>}</span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">{ASSET_TYPE_META[r.input.asset_type]?.label ?? r.input.asset_type}</span>
                    </TD>
                    <TD>
                      <span className="font-mono text-caption text-text-subtle">
                        {c == null && i == null && a == null ? "Not rated" : [c != null ? `C${c}` : null, i != null ? `I${i}` : null, a != null ? `A${a}` : null].filter(Boolean).join("·")}
                      </span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">{r.input.primary_owner_id ? "Assigned" : "Unassigned"}</span>
                    </TD>
                    <TD>
                      {ok ? (
                        <span className="text-body-sm text-status-success-text">Ready</span>
                      ) : (
                        <span className={cn("text-body-sm text-status-danger-text")}>{r.errors.join("; ")}</span>
                      )}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <div className="mt-5 flex items-center justify-end gap-2">
            <Button variant="secondary" onClick={() => navigate("/assets")}>
              Cancel
            </Button>
            <Button loading={commit.isPending} disabled={valid.length === 0} onClick={() => commit.mutate()}>
              Import {valid.length} asset{valid.length === 1 ? "" : "s"}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
