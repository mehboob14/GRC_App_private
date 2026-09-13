import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Icon, PersonSelect, TextField, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { addFinding, listAssetOptions, lookupCveByTitle } from "../api";
import type { CveLookup, Severity } from "../types";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

/**
 * The manual "add one finding" form, shared by the import page and the register
 * "Add vulnerability" drawer. CVE autofill resolves the title/CVE against NVD
 * and offers to fill empty fields — a read only, nothing saved until submit.
 */
export function ManualAddFinding({ onAdded }: { onAdded: (id: string) => void }) {
  const { toast } = useToast();
  const [assetId, setAssetId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<Severity>("high");
  const [cve, setCve] = useState("");
  const [cvss, setCvss] = useState("");
  const [description, setDescription] = useState("");
  const [evidence, setEvidence] = useState("");

  const assetsQuery = useQuery({ queryKey: ["vuln-asset-options"], queryFn: listAssetOptions });
  const assets = (assetsQuery.data ?? []).map((a) => ({ id: a.id, name: a.name }));

  const [lookup, setLookup] = useState<CveLookup | null>(null);
  const [lookupDismissed, setLookupDismissed] = useState(false);
  useEffect(() => {
    const q = title.trim();
    const cveId = cve.trim() || null;
    if (q.length < 4 && !cveId) {
      setLookup(null);
      return;
    }
    const handle = setTimeout(() => {
      lookupCveByTitle(q, cveId)
        .then((r) => {
          setLookup(r.matched && r.cve_id ? r : null);
          setLookupDismissed(false);
        })
        .catch(() => setLookup(null));
    }, 600);
    return () => clearTimeout(handle);
  }, [title, cve]);

  const applyLookup = () => {
    if (!lookup?.cve_id) return;
    if (!cve.trim()) setCve(lookup.cve_id);
    if (!cvss && lookup.cvss_score !== null) setCvss(String(lookup.cvss_score));
    if (lookup.severity) setSeverity(lookup.severity);
    if (!description.trim() && lookup.description) setDescription(lookup.description);
    setLookupDismissed(true);
  };
  const lookupOffers =
    lookup?.cve_id &&
    (!cve.trim() || lookup.cvss_score !== null || (!description.trim() && !!lookup.description));

  const add = useMutation({
    mutationFn: () =>
      addFinding({
        asset_id: assetId!,
        title: title.trim(),
        severity,
        cve_id: cve.trim() || null,
        cvss_score: cvss ? Number(cvss) : null,
        description: description.trim() || null,
        evidence: evidence.trim() || null,
      }),
    onSuccess: (v) => {
      toast({ title: "Finding added", tone: "success" });
      onAdded(v.id);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "finding"), tone: "danger" }),
  });

  return (
    <div className="space-y-3">
      <div>
        <span className="mb-1 block text-label-md font-semibold text-text-primary">Asset</span>
        <PersonSelect
          people={assets}
          value={assetId}
          onChange={setAssetId}
          placeholder={assetsQuery.isLoading ? "Loading assets…" : "Select an asset…"}
          aria-label="Asset"
        />
        {assetsQuery.isError ? (
          <p className="mt-1 text-body-sm text-status-danger-text">
            {describeError(assetsQuery.error, "asset list").message}
          </p>
        ) : null}
      </div>
      <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      {lookupOffers && !lookupDismissed ? (
        <div className="flex items-start gap-2 rounded-md border border-action-accent bg-action-accent-tint px-3 py-2">
          <Icon name="info" className="mt-0.5 size-4 shrink-0 text-action-accent" />
          <div className="min-w-0 flex-1">
            <p className="text-body-sm text-text-primary">
              Matched <span className="font-mono">{lookup?.cve_id}</span>
              {lookup?.severity ? ` · ${lookup.severity}` : ""}
              {lookup?.cvss_score !== null && lookup?.cvss_score !== undefined
                ? ` · CVSS ${lookup.cvss_score}`
                : ""}
            </p>
            <div className="mt-1.5 flex items-center gap-3">
              <button type="button" onClick={applyLookup} className="text-body-sm font-semibold text-text-link hover:underline">
                Autofill
              </button>
              <button type="button" onClick={() => setLookupDismissed(true)} className="text-body-sm text-text-subtle hover:text-text-primary">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <span className="mb-1 block text-label-md font-semibold text-text-primary">Severity</span>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as Severity)}
            className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary capitalize"
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <TextField label="CVSS (optional)" value={cvss} onChange={(e) => setCvss(e.target.value)} placeholder="0 to 10" />
      </div>
      <TextField label="CVE (optional)" value={cve} onChange={(e) => setCve(e.target.value)} placeholder="CVE-2024-…" />
      <div>
        <span className="mb-1 block text-label-md font-semibold text-text-primary">
          Description <span className="font-normal text-text-subtle">(optional)</span>
        </span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
        />
      </div>
      <div>
        <span className="mb-1 block text-label-md font-semibold text-text-primary">
          Evidence <span className="font-normal text-text-subtle">(optional)</span>
        </span>
        <textarea
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          rows={2}
          placeholder="Proof / analyst output…"
          className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
        />
      </div>
      <Button
        className="w-full"
        disabled={!assetId || title.trim() === ""}
        loading={add.isPending}
        onClick={() => add.mutate()}
      >
        Add finding
      </Button>
    </div>
  );
}
