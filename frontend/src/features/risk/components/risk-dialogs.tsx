import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  PersonSelect,
  SearchInput,
  SegmentedControl,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { controlsApi } from "@/lib/api/endpoints";
import { evidenceApi } from "@/lib/api/endpoints";
import { listAssets } from "@/features/assets/api";
import { listDocuments } from "@/features/documents/api";
import { listTasks } from "@/features/tasks/api";
import { listVendors } from "@/features/vendors/api";
import { listVulnerabilities } from "@/features/vulnerabilities/api";
import {
  addAction,
  decideAcceptance,
  getOptions,
  linkControls,
  linkRecord,
  listApprovers,
  requestAcceptance,
} from "../api";
import type { Acceptance, LinkType, RiskDetail } from "../types";
import { isoDate, LINK_META } from "../tokens";

/** Every mutation on one risk returns the whole record; seed the cache with it. */
function useRiskMutation<V>(
  risk: RiskDetail,
  fn: (vars: V) => Promise<RiskDetail>,
  success: string,
  onDone: () => void,
) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: fn,
    onSuccess: (next) => {
      queryClient.setQueryData(["risk", risk.id], next);
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      toast({ title: success, tone: "success" });
      onDone();
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "risk"), tone: "danger" }),
  });
}

// -- controls ----------------------------------------------------------------------

export function ControlPickerDialog({
  open,
  onOpenChange,
  risk,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risk: RiskDetail;
}) {
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  useEffect(() => {
    if (open) {
      setSearch("");
      setPicked([]);
    }
  }, [open]);
  const controlsQuery = useQuery({ queryKey: ["controls", "picker"], queryFn: () => controlsApi.list(), enabled: open });
  const linked = useMemo(() => new Set(risk.controls.map((c) => c.id)), [risk.controls]);
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (controlsQuery.data ?? []).filter(
      (c) => !linked.has(c.id) && (!q || c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)),
    );
  }, [controlsQuery.data, search, linked]);
  const save = useRiskMutation(
    risk,
    () => linkControls(risk.id, picked),
    picked.length === 1 ? "Control linked" : `${picked.length} controls linked`,
    () => onOpenChange(false),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Link controls</DialogTitle>
          <DialogDescription>Controls that reduce this risk.</DialogDescription>
        </DialogHeader>
        <SearchInput value={search} onChange={setSearch} placeholder="Search code, name or category" aria-label="Search controls" />
        <DialogBody className="mt-3">
          {controlsQuery.isLoading ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">Loading controls</p>
          ) : rows.length === 0 ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">No controls match.</p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {rows.slice(0, 150).map((c) => {
                const on = picked.includes(c.id);
                return (
                  <li key={c.id}>
                    <label className={cn("flex cursor-pointer items-center gap-3 px-3 py-2.5", on ? "bg-action-accent-tint/50" : "hover:bg-surface-hover")}>
                      <Checkbox
                        checked={on}
                        onCheckedChange={(v) => setPicked((p) => (v ? [...p, c.id] : p.filter((x) => x !== c.id)))}
                      />
                      <span className="tabular w-16 shrink-0 text-caption font-semibold text-text-subtle">{c.code}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body-sm text-text-primary">{c.name}</span>
                        <span className="block truncate text-caption text-text-subtle">{c.category}</span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </DialogBody>
        <DialogFooter className="justify-between">
          <span className="self-center text-caption text-text-subtle">{picked.length} selected</span>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button disabled={!picked.length} loading={save.isPending} onClick={() => save.mutate(undefined)}>
              Link
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -- linked records --------------------------------------------------------------------

type Candidate = { id: string; code: string; title: string; status: string };

const SEARCH: Record<LinkType, (q: string) => Promise<Candidate[]>> = {
  asset: async (q) =>
    (await listAssets({ search: q }, 1, 25)).items.map((a) => ({ id: a.id, code: a.hostname ?? "", title: a.name, status: a.status })),
  vulnerability: async (q) =>
    (await listVulnerabilities({ search: q })).slice(0, 25).map((v) => ({ id: v.id, code: v.cve_id ?? "", title: v.title, status: v.state })),
  evidence: async (q) => {
    const needle = q.trim().toLowerCase();
    return (await evidenceApi.list())
      .filter((e) => !needle || e.title.toLowerCase().includes(needle))
      .slice(0, 25)
      .map((e) => ({ id: e.id, code: "", title: e.title, status: e.freshness }));
  },
  task: async (q) =>
    (await listTasks({ search: q }, 1, 25)).items.map((t) => ({ id: t.id, code: t.code, title: t.title, status: t.status })),
  vendor: async (q) =>
    (await listVendors({ search: q }, 1, 25)).items.map((v) => ({ id: v.id, code: "", title: v.name, status: v.lifecycle_status })),
  document: async (q) => {
    const needle = q.trim().toLowerCase();
    return (await listDocuments())
      .filter((d) => !needle || d.title.toLowerCase().includes(needle) || d.code.toLowerCase().includes(needle))
      .slice(0, 25)
      .map((d) => ({ id: d.id, code: d.code, title: d.title, status: d.lifecycle }));
  },
};

export function LinkRecordDialog({
  open,
  onOpenChange,
  risk,
  initialType = "asset",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risk: RiskDetail;
  initialType?: LinkType;
}) {
  const [type, setType] = useState<LinkType>(initialType);
  const [search, setSearch] = useState("");
  useEffect(() => {
    if (open) {
      setType(initialType);
      setSearch("");
    }
  }, [open, initialType]);
  const results = useQuery({
    queryKey: ["risk-link-search", type, search],
    queryFn: () => SEARCH[type](search),
    enabled: open,
  });
  const linked = new Set(risk.links.filter((l) => l.target_type === type).map((l) => l.target_id));
  const link = useRiskMutation(
    risk,
    (targetId: string) => linkRecord(risk.id, type, targetId),
    `${LINK_META[type].label} linked`,
    () => undefined,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Link a record</DialogTitle>
          <DialogDescription>Connect this risk to where it lives in the platform.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(SEARCH) as LinkType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-label-sm transition-colors",
                  t === type
                    ? "border-action-accent bg-action-accent text-white"
                    : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
                )}
              >
                <Icon name={LINK_META[t].icon} className="size-3.5" />
                {LINK_META[t].label}
              </button>
            ))}
          </div>
          <SearchInput value={search} onChange={setSearch} placeholder={`Search ${LINK_META[type].plural.toLowerCase()}`} aria-label="Search records" />
        </div>
        <DialogBody className="mt-3">
          {results.isLoading ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">Searching</p>
          ) : results.isError ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">You may not have access to these records.</p>
          ) : !results.data?.length ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">Nothing found.</p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {results.data.map((c) => {
                const done = linked.has(c.id);
                return (
                  <li key={c.id} className="flex items-center gap-3 px-3 py-2.5">
                    <Icon name={LINK_META[type].icon} className="size-4 shrink-0 text-text-subtle" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm text-text-primary">
                        {c.code ? <span className="mr-1.5 text-caption font-semibold text-text-subtle">{c.code}</span> : null}
                        {c.title}
                      </span>
                      <span className="block truncate text-caption capitalize text-text-subtle">{c.status.replace(/_/g, " ")}</span>
                    </span>
                    <Button
                      size="sm"
                      variant={done ? "ghost" : "secondary"}
                      disabled={done || link.isPending}
                      onClick={() => link.mutate(c.id)}
                    >
                      {done ? (
                        <>
                          <Icon name="check" className="size-3.5" />
                          Linked
                        </>
                      ) : (
                        "Link"
                      )}
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -- treatment action ---------------------------------------------------------------------

export function ActionDialog({
  open,
  onOpenChange,
  risk,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risk: RiskDetail;
}) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");
  const [owner, setOwner] = useState<string | null>(null);
  const [due, setDue] = useState("");
  useEffect(() => {
    if (open) {
      setTitle("");
      setPriority(risk.residual_band === "critical" || risk.inherent_band === "critical" ? "high" : "medium");
      setOwner(risk.owner?.membership_id ?? null);
      setDue(risk.treatment_due_on ?? "");
    }
  }, [open, risk]);
  const optionsQuery = useQuery({ queryKey: ["risk-options"], queryFn: getOptions, staleTime: 60_000 });
  const people = (optionsQuery.data?.members ?? []).map((m) => ({ id: m.membership_id, name: m.name }));
  const save = useRiskMutation(
    risk,
    () => addAction(risk.id, { title: title.trim(), priority, owner_membership_id: owner, due_on: due || null }),
    "Action added to Tasks",
    () => onOpenChange(false),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Add treatment action</DialogTitle>
          <DialogDescription>Tracked in Tasks with its SLA and owner.</DialogDescription>
        </DialogHeader>
        <form
          className="space-y-3.5"
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) save.mutate(undefined);
          }}
        >
          <TextField label="Action" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Enforce MFA on the admin console" autoFocus />
          <div className="grid gap-3.5 sm:grid-cols-2">
            <SelectField label="Priority">
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger aria-label="Priority" />
                <SelectContent>
                  {["critical", "high", "medium", "low"].map((p) => (
                    <SelectItem key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextField label="Due" type="date" optional value={due} onChange={(e) => setDue(e.target.value)} />
          </div>
          <div>
            <p className="mb-1.5 text-label-sm text-text-secondary">Owner</p>
            <PersonSelect people={people} value={owner} onChange={setOwner} placeholder="Select owner" clearLabel="No owner" aria-label="Owner" />
          </div>
          <DialogFooter>
            <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!title.trim()} loading={save.isPending}>
              Add action
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// -- acceptance -----------------------------------------------------------------------------

/** Radix Select has no empty value; this stands in for "nobody chosen yet". */
const PICK = "__pick__";

const EXPIRY_PRESETS = [
  { id: "90", label: "3 months", days: 90 },
  { id: "180", label: "6 months", days: 180 },
  { id: "365", label: "1 year", days: 365 },
  { id: "custom", label: "Date", days: 0 },
] as const;

export function AcceptanceRequestDialog({
  open,
  onOpenChange,
  risk,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risk: RiskDetail;
}) {
  const [approver, setApprover] = useState<string>("");
  const [rationale, setRationale] = useState("");
  const [preset, setPreset] = useState<(typeof EXPIRY_PRESETS)[number]["id"]>("180");
  const [custom, setCustom] = useState(isoDate(180));
  useEffect(() => {
    if (open) {
      setApprover("");
      setRationale("");
      setPreset("180");
      setCustom(isoDate(180));
    }
  }, [open]);
  const approversQuery = useQuery({ queryKey: ["risk-approvers"], queryFn: listApprovers, enabled: open });
  const approvers = approversQuery.data ?? [];
  const expires = preset === "custom" ? custom : isoDate(EXPIRY_PRESETS.find((p) => p.id === preset)!.days);
  const save = useRiskMutation(
    risk,
    () => requestAcceptance(risk.id, { approver_membership_id: approver, rationale: rationale.trim(), expires_on: expires }),
    "Sent for approval",
    () => onOpenChange(false),
  );
  const eligible = approvers.filter((a) => a.eligible);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Request acceptance</DialogTitle>
          <DialogDescription>
            {risk.code} at residual score {risk.residual_score ?? risk.inherent_score ?? "not set"}. The approver signs, you cannot.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-3.5"
          onSubmit={(e) => {
            e.preventDefault();
            if (approver && rationale.trim()) save.mutate(undefined);
          }}
        >
          <SelectField label="Approver">
            <Select value={approver || PICK} onValueChange={(v) => setApprover(v === PICK ? "" : v)}>
              <SelectTrigger aria-label="Approver" />
              <SelectContent>
                <SelectItem value={PICK} disabled>
                  Select approver
                </SelectItem>
                {approvers.map((a) => (
                  <SelectItem key={a.membership_id} value={a.membership_id} disabled={!a.eligible}>
                    {a.name}
                    {a.reason ? ` · ${a.reason}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          {approversQuery.isSuccess && eligible.length === 0 ? (
            <p className="rounded-md bg-status-warning-bg px-3 py-2 text-body-sm text-status-warning-text">
              Nobody else can approve risk acceptances yet. Give someone the approve permission in Roles.
            </p>
          ) : null}
          <TextArea
            label="Why the remaining risk is acceptable"
            rows={4}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            placeholder="Compensating controls, cost of further treatment, business need"
          />
          <div>
            <p className="mb-1.5 text-label-sm text-text-secondary">Expires</p>
            <SegmentedControl
              label="Expiry"
              value={preset}
              onChange={setPreset}
              items={EXPIRY_PRESETS.map((p) => ({ id: p.id, label: p.label }))}
            />
            {preset === "custom" ? (
              <div className="mt-2 max-w-[12rem]">
                <TextField label="Expiry date" type="date" value={custom} min={isoDate(1)} onChange={(e) => setCustom(e.target.value)} />
              </div>
            ) : (
              <p className="mt-1.5 text-caption text-text-subtle">On {expires}. The risk reopens when it lapses.</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!approver || !rationale.trim()} loading={save.isPending}>
              Send for approval
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DecisionDialog({
  open,
  onOpenChange,
  risk,
  acceptance,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risk: RiskDetail;
  acceptance: Acceptance | null;
}) {
  const [approve, setApprove] = useState<"approve" | "reject">("approve");
  const [note, setNote] = useState("");
  useEffect(() => {
    if (open) {
      setApprove("approve");
      setNote("");
    }
  }, [open]);
  const save = useRiskMutation(
    risk,
    () => decideAcceptance(risk.id, acceptance!.id, approve === "approve", note.trim()),
    approve === "approve" ? "Acceptance approved" : "Acceptance rejected",
    () => onOpenChange(false),
  );
  if (!acceptance) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Decide acceptance</DialogTitle>
          <DialogDescription>
            Requested by {acceptance.requested_by?.name ?? "a former member"} until {acceptance.expires_on}.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3.5">
          <blockquote className="rounded-md bg-surface-sunken px-3.5 py-3 text-body-sm text-text-secondary">{acceptance.rationale}</blockquote>
          <SegmentedControl
            label="Decision"
            value={approve}
            onChange={setApprove}
            items={[
              { id: "approve", label: "Approve" },
              { id: "reject", label: "Reject" },
            ]}
          />
          <TextArea
            label={approve === "approve" ? "Note" : "Why it is rejected"}
            optional={approve === "approve"}
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={approve === "approve" ? "success-2" : "destructive"}
            disabled={approve === "reject" && !note.trim()}
            loading={save.isPending}
            onClick={() => save.mutate(undefined)}
          >
            {approve === "approve" ? "Approve" : "Reject"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** A decision that needs a reason: close, reopen, revoke, review. */
export function NoteDialog({
  open,
  onOpenChange,
  title,
  description,
  label,
  confirm,
  required = true,
  destructive = false,
  withDate,
  loading,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  label: string;
  confirm: string;
  required?: boolean;
  destructive?: boolean;
  withDate?: { label: string; value: string };
  loading?: boolean;
  onConfirm: (note: string, date: string | null) => void;
}) {
  const [note, setNote] = useState("");
  const [date, setDate] = useState(withDate?.value ?? "");
  useEffect(() => {
    if (open) {
      setNote("");
      setDate(withDate?.value ?? "");
    }
  }, [open, withDate?.value]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3.5">
          {withDate ? <TextField label={withDate.label} type="date" value={date} onChange={(e) => setDate(e.target.value)} /> : null}
          <TextArea label={label} optional={!required} rows={3} value={note} onChange={(e) => setNote(e.target.value)} autoFocus />
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "destructive" : "primary"}
            disabled={required && !note.trim()}
            loading={loading}
            onClick={() => onConfirm(note.trim(), withDate ? date || null : null)}
          >
            {confirm}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AcceptanceStatus({ acceptance }: { acceptance: Acceptance }) {
  const family =
    acceptance.status === "active"
      ? "success"
      : acceptance.status === "pending"
        ? "progress"
        : acceptance.status === "rejected" || acceptance.status === "revoked"
          ? "danger"
          : "neutral";
  const label = {
    pending: "Awaiting approval",
    active: "In force",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
    expired: "Expired",
    revoked: "Revoked",
  }[acceptance.status];
  return <StatusPill status={family} label={label} kind="inline" />;
}
