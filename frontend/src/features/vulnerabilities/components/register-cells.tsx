import { cn } from "@/lib/cn";
import { Tooltip } from "@/components/ui";
import type { VulnInstance } from "../types";

/**
 * Dense list-density cells for the vulnerability register, mirroring the
 * reference GRC register: one triage picture per row without opening a finding.
 * Every cell reads a field the row already carries.
 */

// ─── Title cleanup ──────────────────────────────────────────────────────────
// Scanner (Nessus) plugin names bake version ranges and release-date footnotes
// into the title. Derive a clean list label; the full title stays in the
// tooltip + detail page, so nothing is lost for audit.
export function shortenTitle(title: string): string {
  let t = title.trim();
  t = t.replace(/\s*\([^)]*\)\s*\.?\s*$/g, "").trim();
  t = t.replace(/\s*\d[\w.]*\s*[<>]=?\s*\d[\w.]*(?:\s*\/\s*\d[\w.]*\s*[<>]=?\s*\d[\w.]*)*/g, " ");
  t = t.replace(/\s*[<>]=?\s*\d[\w.]+/g, " ");
  t = t.replace(/\s*\/\s*/g, " ").replace(/\s{2,}/g, " ").replace(/\s+([.,])/g, "$1").trim();
  return t.length >= 3 ? t : title.trim();
}

// ─── Priority (raw vs contextual) ───────────────────────────────────────────
// Raw = the face-value score from CVSS (or a severity baseline) alone, ×10 onto
// the 0-100 scale Verity's risk_score already uses. Contextual = the stored
// risk_score, which folds in EPSS, KEV, exploit maturity, exposure and asset
// criticality. Showing both makes the value of enrichment explicit.
const SEVERITY_BASELINE: Record<string, number> = {
  critical: 9,
  high: 7.5,
  medium: 5,
  low: 2.5,
  info: 1,
};

export function rawPriority(v: Pick<VulnInstance, "cvss_score" | "severity">): {
  score: number;
  from: "CVSS" | "severity";
} {
  const hasCvss = typeof v.cvss_score === "number" && v.cvss_score > 0;
  const base10 = hasCvss ? (v.cvss_score as number) : (SEVERITY_BASELINE[v.severity] ?? 0);
  return { score: Math.round(base10 * 10), from: hasCvss ? "CVSS" : "severity" };
}

export function PriorityRawCell({ v }: { v: VulnInstance }) {
  const { score, from } = rawPriority(v);
  return (
    <Tooltip content={`Raw priority from ${from} alone, before context: ${score}/100`}>
      <span className="inline-flex flex-col leading-tight">
        <span className="w-fit rounded-full bg-surface-sunken px-2 py-0.5 text-caption font-semibold tabular text-text-secondary">
          {score}
        </span>
        <span className="mt-0.5 text-[10px] text-text-subtle">{from} alone</span>
      </span>
    </Tooltip>
  );
}

const BAND_TONE: Record<string, string> = {
  P1: "bg-status-danger-bg text-status-danger-text",
  P2: "bg-status-warning-bg text-status-warning-text",
  P3: "bg-action-accent-tint text-action-accent",
  P4: "bg-surface-sunken text-text-secondary",
};

export function PriorityContextualCell({ v }: { v: VulnInstance }) {
  if (v.risk_score == null) {
    return <span className="text-caption italic text-text-subtle">not scored</span>;
  }
  const raw = rawPriority(v).score;
  const delta = v.risk_score - raw;
  const tone = BAND_TONE[v.priority_band] ?? BAND_TONE.P4;
  return (
    <Tooltip content={v.risk_reason ?? "Contextual composite: CVSS, EPSS, exploit maturity, KEV, attack vector, exposure, asset criticality."}>
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-caption font-semibold", tone)}>
          {v.risk_score} · {v.priority_band}
        </span>
        {delta !== 0 ? (
          <span
            className={cn(
              "text-[10px] font-semibold",
              delta < 0 ? "text-status-success-text" : "text-status-danger-text",
            )}
          >
            {delta < 0 ? "↓" : "↑"}
            {Math.abs(delta)}
          </span>
        ) : (
          <span className="text-[10px] font-medium text-text-subtle">±0</span>
        )}
      </span>
    </Tooltip>
  );
}

// ─── Analyst columns ────────────────────────────────────────────────────────
export function CveCell({ cve }: { cve: string | null }) {
  if (!cve) return <Dash />;
  return (
    <span className="font-mono text-caption text-text-secondary" title={cve}>
      {cve}
    </span>
  );
}

export function CweCell({ cwe }: { cwe: string | null }) {
  if (!cwe) return <Dash />;
  return (
    <span className="font-mono text-caption text-text-subtle" title={cwe}>
      {cwe}
    </span>
  );
}

function cvssTone(s: number | null): string {
  if (s == null) return "text-text-subtle";
  if (s >= 9) return "text-severity-critical";
  if (s >= 7) return "text-severity-high";
  if (s >= 4) return "text-severity-medium";
  return "text-severity-low";
}

export function CvssCell({ score }: { score: number | null }) {
  if (score == null) return <Dash label="Not scored" />;
  return (
    <span className={cn("font-mono text-caption font-semibold tabular", cvssTone(score))} title="CVSS base score">
      {score.toFixed(1)}
    </span>
  );
}

/** EPSS probability (not the percentile) — bold once past the 10% signal line. */
export function EpssCell({ score, percentile }: { score: number | null; percentile: number | null }) {
  if (score == null && percentile == null) return <Dash label="Not scored" />;
  const high = typeof score === "number" && score >= 0.1;
  const title = `EPSS probability of exploitation in the next 30 days${
    percentile != null ? ` · ${Math.round(percentile * 100)}th percentile` : ""
  }`;
  return (
    <span className={cn("font-mono text-caption tabular", high ? "font-semibold text-status-warning-text" : "text-text-secondary")} title={title}>
      {score != null ? `${(score * 100).toFixed(1)}%` : `p${Math.round((percentile as number) * 100)}`}
    </span>
  );
}

const AV_WORD: Record<string, string> = { N: "Network", A: "Adjacent", L: "Local", P: "Physical" };
export function parseAttackVector(vector: string | null): string | null {
  if (!vector) return null;
  const m = /AV:([NALP])/i.exec(vector);
  return m ? m[1].toUpperCase() : null;
}

export function VectorCell({ vector }: { vector: string | null }) {
  const av = parseAttackVector(vector);
  if (!av) return <Dash label="Unknown" />;
  const remote = av === "N" || av === "A";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-1.5 py-0.5 text-[11px] font-medium",
        remote ? "bg-status-danger-bg text-status-danger-text" : "bg-surface-sunken text-text-secondary",
      )}
      title={`CVSS attack vector: ${AV_WORD[av]}`}
    >
      {AV_WORD[av]}
    </span>
  );
}

export function ExploitCell({ count }: { count: number | null }) {
  if (!count || count <= 0) return <span className="text-caption text-text-subtle">None</span>;
  return (
    <span
      className="inline-flex items-center rounded-full bg-status-danger-bg px-1.5 py-0.5 text-[10px] font-bold text-status-danger-text"
      title={`${count} public exploit reference(s) known`}
    >
      Exploit
    </span>
  );
}

export function PatchCell({ available }: { available: boolean | null }) {
  if (!available) return <span className="text-caption text-text-subtle">None</span>;
  return (
    <span className="inline-flex items-center rounded-full bg-status-success-bg px-1.5 py-0.5 text-[10px] font-semibold text-status-success-text" title="A patch or fixed version is available">
      Available
    </span>
  );
}

// ─── Owner avatar ───────────────────────────────────────────────────────────
function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const AVATAR_TINTS = [
  "bg-status-progress-bg text-status-progress-text",
  "bg-status-success-bg text-status-success-text",
  "bg-status-pending-bg text-status-pending-text",
  "bg-status-warning-bg text-status-warning-text",
  "bg-action-accent-tint text-action-accent",
];

function avatarTint(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return AVATAR_TINTS[h % AVATAR_TINTS.length];
}

export function OwnerCell({ name }: { name: string | null }) {
  if (!name) {
    return (
      <span className="inline-flex items-center gap-2 text-body-sm text-text-subtle">
        <span className="inline-flex size-6 items-center justify-center rounded-full bg-surface-sunken text-[10px] font-semibold text-text-subtle">?</span>
        Unassigned
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 text-body-sm text-text-secondary">
      <span className={cn("inline-flex size-6 items-center justify-center rounded-full text-[10px] font-semibold", avatarTint(name))} title={name}>
        {initialsOf(name)}
      </span>
      <span className="truncate">{name}</span>
    </span>
  );
}

function Dash({ label = "None" }: { label?: string }) {
  return <span className="text-caption text-text-subtle">{label}</span>;
}
