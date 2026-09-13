import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { decideVulnException, requestVulnException } from "../api";
import type { VulnException, VulnInstanceDetail } from "../types";

/**
 * The risk-exception flow: someone makes the case, someone else decides.
 *
 * Accepting risk used to be one act — an approver typed a reason and an expiry.
 * That recorded the outcome but not the argument, and gave a reviewer nowhere
 * to say how long it is needed for, why, or what could go wrong if it is
 * granted. Those three are now required of the requester, and the decision is a
 * separate step the server refuses to let the same person take.
 */

const STATUS_META: Record<
  VulnException["status"],
  { label: string; family: "pending" | "success" | "danger" | "neutral" }
> = {
  requested: { label: "Awaiting decision", family: "pending" },
  approved: { label: "Exception approved", family: "success" },
  rejected: { label: "Exception rejected", family: "danger" },
  expired: { label: "Exception expired", family: "neutral" },
  revoked: { label: "Exception revoked", family: "neutral" },
};

const fmt = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso)) : "No date";

export function ExceptionCard({
  vuln,
  canRequest,
  canDecide,
}: {
  vuln: VulnInstanceDetail;
  /** vulnerabilities:manage — anyone working the finding can make the case. */
  canRequest: boolean;
  /** vulnerabilities:accept — granting the waiver is the privileged step. */
  canDecide: boolean;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [requesting, setRequesting] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");

  const exception = vuln.exception;
  const key = ["vulnerability", vuln.id];

  const apply = (next: VulnInstanceDetail) => {
    queryClient.setQueryData(key, next);
    queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
    queryClient.invalidateQueries({ queryKey: ["vuln-kpis"] });
  };

  const decide = useMutation({
    mutationFn: ({ approve, why }: { approve: boolean; why?: string }) =>
      decideVulnException(vuln.id, approve, why),
    onSuccess: (next, vars) => {
      apply(next);
      setRejecting(false);
      setNote("");
      toast({
        title: vars.approve ? "Exception approved" : "Exception rejected",
        tone: vars.approve ? "success" : "neutral",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "exception"), tone: "danger" }),
  });

  // Nothing yet: offer to start one, but only where it makes sense.
  if (!exception) {
    const closed = vuln.state === "fixed" || vuln.state === "false_positive";
    if (closed || !canRequest) return null;
    return (
      <section className="rounded-lg border border-border bg-surface-primary p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-display text-title-md text-text-primary">Risk exception</h2>
            <p className="mt-0.5 text-body-sm text-text-subtle">
              If this cannot be fixed in time, ask for a time-boxed exception. Someone else has
              to approve it.
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => setRequesting(true)}>
            Request exception
          </Button>
        </div>
        <RequestDialog
          open={requesting}
          onOpenChange={setRequesting}
          instanceId={vuln.id}
          onDone={apply}
        />
      </section>
    );
  }

  const meta = STATUS_META[exception.status];
  const pending = exception.status === "requested";

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">Risk exception</h2>
        <StatusPill status={meta.family} label={meta.label} />
      </div>

      <dl className="space-y-2.5">
        <Row label="Requested for">
          {exception.duration_days} days
          {exception.expires_at ? (
            <span className="ml-1.5 font-normal text-text-subtle">
              · expires {fmt(exception.expires_at)}
            </span>
          ) : null}
        </Row>
        <Row label="By">
          {exception.requested_by_name ?? "Unknown"}
          <span className="ml-1.5 font-normal text-text-subtle">
            · {fmt(exception.requested_at)}
          </span>
        </Row>
        <Block label="Rationale">{exception.rationale}</Block>
        <Block label="Potential risks if granted">{exception.potential_risks}</Block>
        {exception.compensating_controls ? (
          <Block label="Compensating controls">{exception.compensating_controls}</Block>
        ) : null}
        {exception.decided_by_name ? (
          <Row label={exception.status === "approved" ? "Approved by" : "Rejected by"}>
            {exception.decided_by_name}
            <span className="ml-1.5 font-normal text-text-subtle">
              · {fmt(exception.decided_at)}
            </span>
          </Row>
        ) : null}
        {exception.decision_note ? (
          <Block label="Decision note">{exception.decision_note}</Block>
        ) : null}
      </dl>

      {pending && canDecide ? (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
          <Button
            size="sm"
            loading={decide.isPending}
            onClick={() => decide.mutate({ approve: true })}
          >
            <Icon name="check" className="size-4" />
            Approve exception
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={decide.isPending}
            onClick={() => setRejecting(true)}
          >
            Reject
          </Button>
          <p className="w-full text-caption text-text-subtle">
            Approving accepts the risk until {exception.duration_days} days from today, and
            reopens the finding automatically when it lapses.
          </p>
        </div>
      ) : pending ? (
        <p className="mt-4 border-t border-border pt-3 text-caption text-text-subtle">
          Waiting on someone with permission to accept risk. Whoever raised it cannot decide it.
        </p>
      ) : null}

      <Dialog open={rejecting} onOpenChange={setRejecting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject this exception</DialogTitle>
            <DialogDescription>
              Say what would change the answer. The requester sees this, and it is recorded on
              the audit trail.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              autoFocus
              placeholder="e.g. a 90-day window is too long for an internet-facing host; resubmit for 30."
              className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary placeholder:text-text-faint focus:border-action-accent focus:outline-none"
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setRejecting(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={decide.isPending}
              disabled={note.trim() === ""}
              onClick={() => decide.mutate({ approve: false, why: note.trim() })}
            >
              Reject exception
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function RequestDialog({
  open,
  onOpenChange,
  instanceId,
  onDone,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instanceId: string;
  onDone: (next: VulnInstanceDetail) => void;
}) {
  const { toast } = useToast();
  const [days, setDays] = useState("90");
  const [rationale, setRationale] = useState("");
  const [risks, setRisks] = useState("");
  const [controls, setControls] = useState("");

  const submit = useMutation({
    mutationFn: () =>
      requestVulnException(instanceId, {
        duration_days: Number(days),
        rationale: rationale.trim(),
        potential_risks: risks.trim(),
        compensating_controls: controls.trim() || null,
      }),
    onSuccess: (next) => {
      onDone(next);
      onOpenChange(false);
      toast({ title: "Exception requested", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "exception"), tone: "danger" }),
  });

  const duration = Number(days);
  const validDuration = Number.isInteger(duration) && duration >= 1 && duration <= 365;
  const ready = validDuration && rationale.trim() !== "" && risks.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Request a risk exception</DialogTitle>
          <DialogDescription>
            A time-boxed waiver, not a dismissal. The finding reopens by itself when the window
            closes, and someone other than you has to approve it.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <TextField
            label="Duration in days"
            type="number"
            min={1}
            max={365}
            value={days}
            onChange={(event) => setDays(event.target.value)}
            hint="Up to a year. The clock starts when it is approved, not today."
            error={days !== "" && !validDuration ? "Enter a whole number from 1 to 365." : undefined}
          />
          <Field
            label="Rationale"
            value={rationale}
            onChange={setRationale}
            placeholder="Why can this not be remediated inside the SLA?"
          />
          <Field
            label="Potential risks if granted"
            value={risks}
            onChange={setRisks}
            placeholder="What could go wrong while this stays open, and how bad would it be?"
          />
          <Field
            label="Compensating controls"
            optional
            value={controls}
            onChange={setControls}
            placeholder="What reduces the risk meanwhile: WAF rule, network restriction, monitoring?"
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={submit.isPending} disabled={!ready} onClick={() => submit.mutate()}>
            Submit request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  optional,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  optional?: boolean;
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
}) {
  const id = `exc-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <label className="mb-1 block text-label-md font-semibold text-text-primary" htmlFor={id}>
        {label}
        {optional ? <span className="ml-1 font-normal text-text-subtle">(optional)</span> : null}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        maxLength={4000}
        placeholder={placeholder}
        className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary placeholder:text-text-faint focus:border-action-accent focus:outline-none"
      />
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-body-sm text-text-subtle">{label}</dt>
      <dd className="min-w-0 text-right text-body-sm font-semibold text-text-primary">
        {children}
      </dd>
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-caption font-semibold text-text-subtle">{label}</dt>
      <dd className="mt-0.5 whitespace-pre-line text-body-sm text-text-secondary">{children}</dd>
    </div>
  );
}
