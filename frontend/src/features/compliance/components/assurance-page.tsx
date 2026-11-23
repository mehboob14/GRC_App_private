import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { useSelectedFramework } from "../use-frameworks";

/**
 * Audits (guided onboarding EN-9, EN-10, CN-5, EX-2, EX-4): internal audits, management reviews,
 * outside audit stages, and reports or certificates you already hold. A finding raises its
 * corrective action task; a graded finding closes only with evidence of the fix.
 */

type Finding = {
  id: string;
  grade: "major" | "minor" | "observation" | "exception";
  summary: string;
  due_on: string | null;
  task_id: string | null;
  closed_on: string | null;
  verified_on: string | null;
  overdue: boolean;
};

type AuditRecord = {
  id: string;
  kind: string;
  label: string;
  starts_on: string | null;
  ends_on: string | null;
  performed_by_name: string | null;
  performed_by_firm: string | null;
  document_id: string | null;
  status: string;
  findings: Finding[];
  notice?: string | null;
};

type Assurance = { records: AuditRecord[]; review_inputs: string[] };

const KINDS: { id: string; label: string; iso?: boolean }[] = [
  { id: "internal_audit", label: "Internal audit" },
  { id: "management_review", label: "Management review", iso: true },
  { id: "external_stage", label: "Audit by your auditor" },
  { id: "prior_report", label: "Past report" },
  { id: "prior_certificate", label: "Certificate", iso: true },
];

const GRADE: Record<Finding["grade"], { family: StatusFamily; label: string }> = {
  major: { family: "danger", label: "Major" },
  minor: { family: "warning", label: "Minor" },
  exception: { family: "warning", label: "Exception" },
  observation: { family: "neutral", label: "Observation" },
};

const today = () => new Date().toISOString().slice(0, 10);

export function AssurancePage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "controls:manage");
  const { code, selected } = useSelectedFramework();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const path = `/engagement/assurance?framework=${code}`;
  const query = useQuery({
    queryKey: ["assurance", principal?.tenant_id, code],
    queryFn: () => apiFetch<Assurance>(path),
  });
  const [creating, setCreating] = useState<string | null>(null);
  const [form, setForm] = useState({ starts_on: "", ends_on: "", performed_by_name: "", performed_by_firm: "", scope_note: "" });
  const [finding, setFinding] = useState<AuditRecord | null>(null);
  const [draft, setDraft] = useState({ grade: "minor", summary: "", due_on: "" });

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["assurance"] }),
      queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
    ]);
  const save = useMutation({
    mutationFn: (kind: string) =>
      apiFetch<AuditRecord>(path, {
        method: "POST",
        body: JSON.stringify({
          kind,
          starts_on: form.starts_on || null,
          ends_on: form.ends_on || null,
          performed_by_name: form.performed_by_name || null,
          performed_by_firm: form.performed_by_firm || null,
          scope_note: form.scope_note || null,
          status: "held",
        }),
      }),
    onSuccess: async (record) => {
      await refresh();
      setCreating(null);
      toast({ title: record.notice ?? "Recorded", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "record"), tone: "danger" }),
  });
  const addFinding = useMutation({
    mutationFn: (record: AuditRecord) =>
      apiFetch<Finding>(`/engagement/assurance/${record.id}/findings`, {
        method: "POST",
        body: JSON.stringify({ grade: draft.grade, summary: draft.summary, due_on: draft.due_on || null }),
      }),
    onSuccess: async () => {
      await refresh();
      setFinding(null);
      toast({ title: "Finding recorded and a task raised", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "finding"), tone: "danger" }),
  });
  const close = useMutation({
    mutationFn: (args: { id: string; verify?: boolean }) =>
      apiFetch<Finding>(`/engagement/assurance/findings/${args.id}`, {
        method: "PUT",
        body: JSON.stringify(args.verify ? { verified_on: today() } : { closed_on: today() }),
      }),
    onSuccess: () => void refresh(),
    onError: (error: unknown) => toast({ title: errorToast(error, "finding"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-64 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "audits");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  const iso = selected?.scope_model === "applicability";
  const kinds = KINDS.filter((k) => iso || !k.iso);
  const records = query.data.records;

  return (
    <div>
      {canManage ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {kinds.map((k) => (
            <Button
              key={k.id}
              size="sm"
              variant="secondary"
              onClick={() => {
                setForm({ starts_on: "", ends_on: "", performed_by_name: "", performed_by_firm: "", scope_note: "" });
                setCreating(k.id);
              }}
            >
              Record {k.label.toLowerCase()}
            </Button>
          ))}
        </div>
      ) : null}

      <PeriodicCard framework={code} />

      {records.length === 0 ? (
        <EmptyState
          title="Nothing recorded yet"
          description={iso ? "Record your internal audit and management review here." : "Record audits and past reports here."}
        />
      ) : (
        <div className="space-y-3">
          {records.map((r) => (
            <section key={r.id} className="rounded-lg border border-border bg-surface-primary">
              <header className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-3">
                <span className="font-semibold text-text-primary">{r.label}</span>
                <span className="text-body-sm tabular text-text-secondary">
                  {r.starts_on ?? "No date"}
                  {r.ends_on ? ` to ${r.ends_on}` : ""}
                </span>
                {r.performed_by_name ? (
                  <span className="text-body-sm text-text-secondary">
                    {r.performed_by_name}
                    {r.performed_by_firm ? `, ${r.performed_by_firm}` : ""}
                  </span>
                ) : null}
                <span className="flex-1" />
                {r.document_id ? null : <StatusPill status="pending" label="No report attached" />}
                {canManage ? (
                  <Button size="sm" variant="ghost" onClick={() => { setDraft({ grade: "minor", summary: "", due_on: "" }); setFinding(r); }}>
                    Add finding
                  </Button>
                ) : null}
              </header>
              {r.findings.map((f) => (
                <div key={f.id} className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-2.5 first:border-t-0">
                  <StatusPill status={GRADE[f.grade].family} label={GRADE[f.grade].label} />
                  <span className="min-w-0 flex-1 text-body-sm text-text-primary">{f.summary}</span>
                  {f.overdue ? <StatusPill status="danger" label="Past due" /> : null}
                  {f.closed_on ? (
                    <StatusPill status="success" label={f.verified_on ? "Verified" : "Closed"} />
                  ) : canManage ? (
                    <Button size="sm" variant="ghost" onClick={() => close.mutate({ id: f.id })}>
                      Close
                    </Button>
                  ) : null}
                  {f.closed_on && !f.verified_on && f.grade === "major" && canManage ? (
                    <Button size="sm" variant="ghost" onClick={() => close.mutate({ id: f.id, verify: true })}>
                      Verified by the body
                    </Button>
                  ) : null}
                </div>
              ))}
            </section>
          ))}
        </div>
      )}

      <Dialog open={creating !== null} onOpenChange={(v) => (v ? null : setCreating(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Record {KINDS.find((k) => k.id === creating)?.label.toLowerCase()}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <TextField label={creating === "prior_certificate" ? "Issued" : "Date"} type="date" value={form.starts_on} onChange={(e) => setForm({ ...form, starts_on: e.target.value })} />
              <TextField label={creating === "prior_certificate" ? "Expires" : "Ends"} type="date" optional value={form.ends_on} onChange={(e) => setForm({ ...form, ends_on: e.target.value })} />
            </div>
            <TextField label={creating === "internal_audit" ? "Performed by" : "Auditor or issuer"} optional value={form.performed_by_name} onChange={(e) => setForm({ ...form, performed_by_name: e.target.value })} />
            <TextField label="Firm" optional value={form.performed_by_firm} onChange={(e) => setForm({ ...form, performed_by_firm: e.target.value })} />
            <TextArea label="Scope" optional rows={3} value={form.scope_note} onChange={(e) => setForm({ ...form, scope_note: e.target.value })} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setCreating(null)}>
              Cancel
            </Button>
            <Button loading={save.isPending} onClick={() => creating && save.mutate(creating)}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={finding !== null} onOpenChange={(v) => (v ? null : setFinding(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Add a finding</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <SelectField label="Grade">
              <Select value={draft.grade} onValueChange={(v) => setDraft({ ...draft, grade: v })}>
                <SelectTrigger aria-label="Grade" />
                <SelectContent>
                  {Object.entries(GRADE).map(([value, g]) => (
                    <SelectItem key={value} value={value}>
                      {g.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextArea label="What was found" rows={3} value={draft.summary} onChange={(e) => setDraft({ ...draft, summary: e.target.value })} />
            <TextField label="Due" type="date" optional value={draft.due_on} onChange={(e) => setDraft({ ...draft, due_on: e.target.value })} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setFinding(null)}>
              Cancel
            </Button>
            <Button disabled={!draft.summary.trim()} loading={addFinding.isPending} onClick={() => finding && addFinding.mutate(finding)}>
              Add and raise task
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

type Periodic = {
  start: string | null;
  end: string | null;
  label: string | null;
  rows: { control_id: string; code: string; name: string; cadence: string; needed: number; found: number }[];
};

/** Periodic controls planned against the audit period (EN-8): what is still missing in it. */
function PeriodicCard({ framework }: { framework: string }) {
  const { principal } = useAuth();
  const query = useQuery({
    queryKey: ["periodic", principal?.tenant_id, framework],
    queryFn: () => apiFetch<Periodic>(`/engagement/periodic?framework=${framework}`),
  });
  const data = query.data;
  if (!data || !data.start) {
    return data?.label ? <p className="mb-4 text-body-sm text-text-secondary">{data.label}</p> : null;
  }
  const short = data.rows.filter((r) => r.found < r.needed);
  return (
    <section className="mb-4 rounded-lg border border-border bg-surface-primary px-5 py-4">
      <h2 className="font-display text-title-md text-text-primary">
        Periodic controls in the {data.label}, {data.start} to {data.end}
      </h2>
      <p className="mt-1 text-body-sm text-text-secondary">
        {short.length
          ? `${short.length} of ${data.rows.length} still need evidence dated inside it.`
          : `All ${data.rows.length} have evidence dated inside it.`}
      </p>
      {short.length ? (
        <ul className="mt-2 space-y-1">
          {short.slice(0, 12).map((r) => (
            <li key={r.control_id} className="text-body-sm">
              <Link to={`/controls/${r.control_id}?tab=evidence`} className="text-text-link">
                {r.code}
              </Link>{" "}
              <span className="text-text-secondary">
                {r.name}: {r.found} of {r.needed} {r.cadence}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
