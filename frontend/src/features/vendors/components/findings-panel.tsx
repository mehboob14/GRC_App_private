import { useState } from "react";
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
import { describeError, errorToast } from "@/lib/api/describe-error";
import { acceptFinding, closeFinding, listFindings, listMembers, remediateFinding } from "../api";
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
}: {
  vendorId: string;
  canManage: boolean;
  canApprove: boolean;
}) {
  const queryClient = useQueryClient();
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
          ? `${blocking.length} of these hold the approval gate until they are closed or accepted.`
          : undefined
      }
    >
      {query.isError ? (
        <p className="text-body-md text-status-danger-text">
          {describeError(query.error, "findings").message}
        </p>
      ) : query.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : items.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          None raised. Findings come out of a scored questionnaire, a document review, or a breached
          service level — they are not entered by hand.
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
  const [accepting, setAccepting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [owner, setOwner] = useState<string | null>(f.owner_membership_id);

  const status = FINDING_STATUS_META[f.status] ?? { label: f.status, family: "neutral" as const };
  const due = daysUntil(f.sla_due);
  const overdue = due !== null && due < 0 && (f.status === "open" || f.status === "in_remediation");
  const settled = f.status === "closed" || f.status === "accepted";

  const fail = (e: unknown) => toast({ title: errorToast(e, "finding"), tone: "danger" });

  const remediate = useMutation({
    mutationFn: (membershipId: string | null) => remediateFinding(vendorId, f.id, membershipId),
    onSuccess: () => {
      onSettled();
      toast({ title: "Remediation started", tone: "success" });
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
              <Tooltip content="The approval gate cannot be passed while this is open">
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
        <StatusPill status={status.family} label={status.label} kind="inline" />
      </div>

      {f.status === "accepted" ? (
        <div className="mt-2 rounded-md border border-status-pending-border bg-status-pending-bg p-3">
          <p className="text-label-sm text-status-pending-text">
            Accepted until {fmtDate(f.accepted_until)}
          </p>
          <p className="mt-1 text-body-sm text-text-secondary">
            {f.accepted_rationale || "No rationale was recorded."}
          </p>
        </div>
      ) : null}

      {!settled && canManage ? (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <div className="w-56">
            <PersonSelect
              people={people}
              value={owner}
              onChange={(next) => {
                setOwner(next);
                if (next) remediate.mutate(next);
              }}
              placeholder="Assign an owner"
              aria-label={`Owner for ${f.title}`}
            />
          </div>
          {f.status === "open" ? (
            <Button
              variant="secondary"
              size="sm"
              loading={remediate.isPending}
              onClick={() => remediate.mutate(owner)}
            >
              Start remediation
            </Button>
          ) : null}
          <Button variant="secondary" size="sm" onClick={() => setClosing(true)}>
            Close
          </Button>
          {canApprove ? (
            <Button variant="ghost" size="sm" onClick={() => setAccepting(true)}>
              Accept the risk
            </Button>
          ) : (
            <Tooltip content="Accepting risk needs the Approve vendors permission">
              <span className="text-caption text-text-subtle">
                <Icon name="info" className="mr-1 inline size-3.5" />
                Someone else has to accept this
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
        loading={close.isPending}
        onClose={(note) => close.mutate(note)}
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
          <DialogDescription>
            Accepting is time-boxed on purpose. When the date passes the finding comes back open, so
            pick a date you are willing to be asked about.
          </DialogDescription>
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
              label="Why this is acceptable"
              hint="What compensates for it, and what would make you revisit."
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
  loading,
  onClose,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  loading: boolean;
  onClose: (note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Close this finding?</DialogTitle>
          <DialogDescription>
            Closing says the thing was fixed. If you are instead deciding to live with it, accept
            the risk rather than closing it.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onClose(note.trim());
          }}
        >
          <DialogBody className="space-y-3.5">
            <p className="text-body-sm text-text-secondary">{title}</p>
            <TextArea
              label="What was done"
              optional
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={4000}
              placeholder="They shipped MFA on the admin console on 3 March and sent the screenshot."
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              Close finding
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
