import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  PersonSelect,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  SeverityChip,
  Skeleton,
  StatusPill,
  TextArea,
  TextField,
  Tooltip,
  useToast,
  type Severity,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { FINDING_SEVERITIES } from "../types";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { listRegisters, promoteFinding } from "@/features/risk/api";
import { rememberedRegister } from "@/features/risk/components/risks-outlet";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  acceptFinding,
  closeFinding,
  createFinding,
  listFindings,
  listMembers,
  remediateFinding,
  reopenFinding,
} from "../api";
import type { Finding } from "../types";
import {
  daysUntil,
  fmtCountdown,
  fmtDate,
  FINDING_SOURCE_LABEL,
  FINDING_STATUS_META,
  TREATMENT_LABEL,
} from "../tokens";
import { Panel } from "./panel";

/**
 * The findings raised against one vendor, and the three things anyone can do
 * with them: put someone on it, time-box the risk, or close it.
 *
 * Accepting is the privileged one — it is the act of deciding to live with
 * something — so it sits behind `vendors:approve` while the other two need only
 * `vendors:manage`.
 */
export function FindingsPanel({
  vendorId,
  canManage,
  canApprove,
  engagementId = null,
}: {
  vendorId: string;
  canManage: boolean;
  canApprove: boolean;
  /** Attached to a finding raised by hand, so it holds that gate rather than all of them. */
  engagementId?: string | null;
}) {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const query = useQuery({
    queryKey: ["vendor-findings", { vendor_id: vendorId }],
    queryFn: () => listFindings({ vendor_id: vendorId }),
  });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  const items = query.data?.items ?? [];
  const open = items.filter((f) => f.status === "open" || f.status === "in_remediation");
  const blocking = open.filter((f) => f.is_blocking);

  const settle = () => {
    void queryClient.invalidateQueries({ queryKey: ["vendor-findings"] });
    void queryClient.invalidateQueries({ queryKey: ["vendor", vendorId] });
    void queryClient.invalidateQueries({ queryKey: ["vendors"] });
  };

  return (
    <Panel
      title="Findings"
      count={items.length || undefined}
      description={
        blocking.length > 0
          ? `${blocking.length} blocking the approval gate`
          : undefined
      }
      action={
        canManage ? (
          <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
            <Icon name="plus" className="size-4" />
            Raise finding
          </Button>
        ) : null
      }
    >
      <RaiseFindingDialog
        open={adding}
        onOpenChange={setAdding}
        vendorId={vendorId}
        engagementId={engagementId}
        people={(membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name }))}
        onRaised={settle}
      />
      {query.isError ? (
        <p className="text-body-md text-status-danger-text">
          {describeError(query.error, "findings").message}
        </p>
      ) : query.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : items.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No findings. They come from questionnaires, reviews and SLA breaches.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {items.map((f) => (
            <FindingItem
              key={f.id}
              finding={f}
              vendorId={vendorId}
              people={(membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name }))}
              canManage={canManage}
              canApprove={canApprove}
              onSettled={settle}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function RaiseFindingDialog({
  open,
  onOpenChange,
  vendorId,
  engagementId,
  people,
  onRaised,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  engagementId: string | null;
  people: { id: string; name: string }[];
  onRaised: () => void;
}) {
  const { toast } = useToast();
  const blank = { title: "", detail: "", severity: "medium", is_blocking: false };
  const [form, setForm] = useState(blank);
  const [owner, setOwner] = useState<string | null>(null);

  const raise = useMutation({
    mutationFn: () =>
      createFinding(vendorId, {
        title: form.title.trim(),
        detail: form.detail.trim(),
        severity: form.severity,
        engagement_id: engagementId,
        is_blocking: form.is_blocking,
        owner_membership_id: owner,
      }),
    onSuccess: () => {
      onRaised();
      onOpenChange(false);
      setForm(blank);
      setOwner(null);
      toast({ title: "Finding raised", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "finding"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Raise a finding</DialogTitle>
          <DialogDescription>
            For a gap no question asked about. Its due date comes from the severity.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (form.title.trim()) raise.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="What is wrong"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="No MFA on their support console"
              autoFocus
            />
            <TextArea
              label="Detail"
              optional
              value={form.detail}
              onChange={(e) => setForm((f) => ({ ...f, detail: e.target.value }))}
              rows={3}
              maxLength={8000}
              placeholder="Raised on the quarterly call with their security lead."
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <SelectField label="Severity">
                <Select
                  value={form.severity}
                  onValueChange={(v) => setForm((f) => ({ ...f, severity: v }))}
                >
                  <SelectTrigger aria-label="Severity" />
                  <SelectContent>
                    {FINDING_SEVERITIES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <div>
                <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Owner</p>
                <PersonSelect
                  people={people}
                  value={owner}
                  onChange={setOwner}
                  placeholder="Unassigned"
                  aria-label="Finding owner"
                />
              </div>
            </div>
            <label className="flex items-start gap-2.5 rounded-md border border-border bg-surface-sunken px-3 py-2.5">
              <input
                type="checkbox"
                className="mt-1 size-4 accent-action-accent"
                checked={form.is_blocking}
                onChange={(e) => setForm((f) => ({ ...f, is_blocking: e.target.checked }))}
              />
              <span>
                <span className="block font-sans text-label-sm text-text-primary">
                  Holds the approval gate
                </span>
                <span className="block text-caption text-text-subtle">
                  The vendor cannot be approved until this is fixed, accepted or closed.
                </span>
              </span>
            </label>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={raise.isPending} disabled={!form.title.trim()}>
              Raise finding
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function FindingItem({
  finding: f,
  vendorId,
  people,
  canManage,
  canApprove,
  onSettled,
}: {
  finding: Finding;
  vendorId: string;
  people: { id: string; name: string }[];
  canManage: boolean;
  canApprove: boolean;
  onSettled: () => void;
}) {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { principal } = useAuth();
  const canPromote = hasPermission(principal, "risks:manage");
  const [accepting, setAccepting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [reopening, setReopening] = useState(false);
  const [owner, setOwner] = useState<string | null>(f.owner_membership_id);

  const status = FINDING_STATUS_META[f.status] ?? { label: f.status, family: "neutral" as const };
  const due = daysUntil(f.sla_due);
  const overdue = due !== null && due < 0 && (f.status === "open" || f.status === "in_remediation");
  const settled = f.status === "closed" || f.status === "accepted";

  const fail = (e: unknown) => toast({ title: errorToast(e, "finding"), tone: "danger" });

  const remediate = useMutation({
    mutationFn: (membershipId: string | null) => remediateFinding(vendorId, f.id, membershipId),
    onSuccess: (next) => {
      onSettled();
      toast({
        title: next.owner_name
          ? `Remediation task opened for ${next.owner_name}`
          : "Remediation task opened",
        tone: "success",
      });
    },
    onError: fail,
  });

  // Spec 85: a vendor finding can become a risk in the register. It lands in the
  // register the person last worked in, or the default one.
  const promote = useMutation({
    mutationFn: async () => {
      const registers = await listRegisters();
      const target =
        registers.find((r) => r.id === rememberedRegister() && r.status === "active") ??
        registers.find((r) => r.is_default) ??
        registers[0];
      return target ? promoteFinding(f.id, target.id) : null;
    },
    onSuccess: (risk) => {
      if (risk === null) {
        toast({ title: "Create a risk register first, then promote this finding.", tone: "neutral" });
        navigate("/risks");
        return;
      }
      onSettled();
      toast({ title: `${risk.code} added to the risk register`, tone: "success" });
      navigate(`/risks/${risk.id}`);
    },
    onError: fail,
  });

  const accept = useMutation({
    mutationFn: (input: { until: string; rationale: string }) =>
      acceptFinding(vendorId, f.id, input.until, input.rationale),
    onSuccess: () => {
      setAccepting(false);
      onSettled();
      toast({ title: "Risk accepted", tone: "success" });
    },
    onError: fail,
  });

  const close = useMutation({
    mutationFn: (note: string) => closeFinding(vendorId, f.id, note || null),
    onSuccess: () => {
      setClosing(false);
      onSettled();
      toast({ title: "Finding closed", tone: "success" });
    },
    onError: fail,
  });

  const reopen = useMutation({
    mutationFn: (reason: string) => reopenFinding(vendorId, f.id, reason),
    onSuccess: () => {
      setReopening(false);
      onSettled();
      toast({ title: "Finding reopened", tone: "success" });
    },
    onError: fail,
  });

  return (
    <li className="py-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-2">
            <SeverityChip
              severity={f.severity as Severity}
              label={f.severity.charAt(0).toUpperCase() + f.severity.slice(1)}
            />
            <span className="text-body-md font-semibold text-text-primary">{f.title}</span>
            {f.is_blocking ? (
              <Tooltip content="Blocks approval while open">
                <span>
                  <Badge variant="statusFail">Blocking</Badge>
                </span>
              </Tooltip>
            ) : null}
          </p>
          {f.detail ? (
            <p className="mt-1 whitespace-pre-line text-body-sm text-text-secondary">{f.detail}</p>
          ) : null}
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-text-subtle">
            <span>{FINDING_SOURCE_LABEL[f.finding_source] ?? f.finding_source}</span>
            <span>·</span>
            <span>{TREATMENT_LABEL[f.treatment] ?? f.treatment}</span>
            <span>·</span>
            <span>raised {fmtDate(f.created_at)}</span>
            {f.sla_due ? (
              <>
                <span>·</span>
                <span className={cn(overdue && "font-semibold text-status-danger-text")}>
                  due {fmtCountdown(due)}
                </span>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {f.promoted_risk_id ? (
            <Link
              to={`/risks/${f.promoted_risk_id}`}
              className="inline-flex items-center gap-1 text-label-sm text-text-link hover:underline"
            >
              <Icon name="risk" className="size-3.5" />
              In risk register
            </Link>
          ) : canPromote ? (
            <Button variant="ghost" size="sm" loading={promote.isPending} onClick={() => promote.mutate()}>
              <Icon name="risk" className="size-3.5" />
              Promote to risk
            </Button>
          ) : null}
          <StatusPill status={status.family} label={status.label} kind="inline" />
        </div>
      </div>

      {f.status === "accepted" ? (
        <div className="mt-2 rounded-md border border-status-pending-border bg-status-pending-bg p-3">
          <p className="text-label-sm text-status-pending-text">
            Accepted until {fmtDate(f.accepted_until)}
          </p>
          <p className="mt-1 text-body-sm text-text-secondary">
            {f.accepted_rationale || "No rationale recorded."}
          </p>
        </div>
      ) : null}

      {settled && canManage ? (
        <div className="mt-2.5">
          <Button variant="ghost" size="sm" onClick={() => setReopening(true)}>
            <Icon name="undo" className="size-3.5" />
            Reopen
          </Button>
        </div>
      ) : null}

      {!settled && canManage ? (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <div className="w-56">
            <PersonSelect
              people={people}
              value={owner}
              // Local only. Choosing a name used to POST straight away, which
              // opens a real task in the tasks module, flips the finding to
              // in_remediation and sets its treatment -- none of which the
              // picker said. The second choice on the same finding then 409s.
              onChange={setOwner}
              placeholder="Assign an owner"
              aria-label={`Owner for ${f.title}`}
            />
          </div>
          {f.task_id === null ? (
            <Button
              variant="secondary"
              size="sm"
              loading={remediate.isPending}
              onClick={() => remediate.mutate(owner)}
            >
              Start remediation
            </Button>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-body-sm text-text-secondary">
              <Icon name="check" className="size-3.5 shrink-0 text-status-success-base" />
              Tracked as a task
            </span>
          )}
          <Button variant="secondary" size="sm" onClick={() => setClosing(true)}>
            Close
          </Button>
          {canApprove ? (
            <Button variant="ghost" size="sm" onClick={() => setAccepting(true)}>
              Accept risk
            </Button>
          ) : (
            <Tooltip content="Accepting risk needs the Approve vendors permission">
              <span className="text-caption text-text-subtle">
                <Icon name="info" className="mr-1 inline size-3.5" />
                Approver must accept
              </span>
            </Tooltip>
          )}
        </div>
      ) : null}

      <AcceptDialog
        open={accepting}
        onOpenChange={setAccepting}
        title={f.title}
        loading={accept.isPending}
        onAccept={(until, rationale) => accept.mutate({ until, rationale })}
      />
      <CloseDialog
        open={closing}
        onOpenChange={setClosing}
        title={f.title}
        noteRequired={f.severity === "critical" || f.is_blocking}
        loading={close.isPending}
        onClose={(note) => close.mutate(note)}
      />
      <ReopenDialog
        open={reopening}
        onOpenChange={setReopening}
        title={f.title}
        loading={reopen.isPending}
        onReopen={(reason) => reopen.mutate(reason)}
      />
    </li>
  );
}

function AcceptDialog({
  open,
  onOpenChange,
  title,
  loading,
  onAccept,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  loading: boolean;
  onAccept: (until: string, rationale: string) => void;
}) {
  const [until, setUntil] = useState("");
  const [rationale, setRationale] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Accept this risk?</DialogTitle>
          <DialogDescription>The finding reopens when this date passes.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (until && rationale.trim()) onAccept(until, rationale.trim());
          }}
        >
          <DialogBody className="space-y-3.5">
            <p className="text-body-sm text-text-secondary">{title}</p>
            <TextField
              label="Accepted until"
              type="date"
              value={until}
              onChange={(e) => setUntil(e.target.value)}
            />
            <TextArea
              label="Rationale"
              hint="Compensating controls and revisit triggers."
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              maxLength={4000}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={!until || !rationale.trim()}>
              Accept until {until || "…"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CloseDialog({
  open,
  onOpenChange,
  title,
  noteRequired,
  loading,
  onClose,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Critical and blocking findings say how they were resolved. */
  noteRequired: boolean;
  loading: boolean;
  onClose: (note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Close this finding?</DialogTitle>
          <DialogDescription>Close only if fixed. To live with it, accept the risk.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!noteRequired || note.trim()) onClose(note.trim());
          }}
        >
          <DialogBody className="space-y-3.5">
            <p className="text-body-sm text-text-secondary">{title}</p>
            <TextArea
              label="What was done"
              optional={!noteRequired}
              hint={noteRequired ? "Required for a critical or blocking finding." : undefined}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={4000}
              placeholder="MFA enabled on admin console, screenshot received"
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={noteRequired && !note.trim()}>
              Close finding
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ReopenDialog({
  open,
  onOpenChange,
  title,
  loading,
  onReopen,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  loading: boolean;
  onReopen: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Reopen this finding?</DialogTitle>
          <DialogDescription>It goes back on the open list and counts again.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (reason.trim()) onReopen(reason.trim());
          }}
        >
          <DialogBody className="space-y-3.5">
            <p className="text-body-sm text-text-secondary">{title}</p>
            <TextArea
              label="Why"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="The fix was rolled back in the last release"
              autoFocus
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={!reason.trim()}>
              Reopen finding
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
