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
  EmptyState,
  ErrorState,
  Icon,
  SegmentedControl,
  Skeleton,
  StatusPill,
  TextArea,
  Toolbar,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { decideIntake, listIntake } from "../api";
import type { IntakeRequest } from "../types";
import {
  duplicateReason,
  fmtDate,
  INTAKE_DECISION_META,
  SCREENING_META,
  URGENCY_META,
} from "../tokens";
import { RequestVendorDialog } from "./request-vendor-dialog";

type Scope = "pending" | "approved" | "rejected" | "all";

const SCOPES = [
  { id: "pending" as const, label: "Awaiting decision" },
  { id: "approved" as const, label: "Approved" },
  { id: "rejected" as const, label: "Declined" },
  { id: "all" as const, label: "All" },
];

/**
 * The queue of asks that have not become vendors yet.
 *
 * A decision queue is read, not scanned: each request carries a proposed use, a
 * screening result and possibly a list of vendors it duplicates, and none of
 * that survives being squeezed into a table row. So this is a card list, with
 * the two decisions on the card that needs them.
 */
export function VendorIntakePage() {
  const { principal } = useAuth();
  const canDecide = hasPermission(principal, "vendors:manage");
  const [scope, setScope] = useState<Scope>("pending");
  const [requestOpen, setRequestOpen] = useState(false);

  const query = useQuery({
    queryKey: ["vendor-intake", scope],
    queryFn: () => listIntake(scope === "all" ? null : scope),
  });

  const listError = query.isError ? describeError(query.error, "intake queue") : null;
  const items = query.data?.items ?? [];

  return (
    <div>
      <Toolbar
        actions={
          <Button variant="secondary" onClick={() => setRequestOpen(true)}>
            <Icon name="plus" className="size-4" />
            Request a vendor
          </Button>
        }
      >
        <SegmentedControl
          items={SCOPES}
          value={scope}
          onChange={setScope}
          label="Intake queue scope"
        />
      </Toolbar>

      <div className="mt-4">
        {query.isError ? (
          <ErrorState
            title={listError!.title}
            description={listError!.message}
            referenceId={listError!.referenceId}
            onRetry={listError!.retryable ? () => void query.refetch() : undefined}
          />
        ) : query.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon="audit"
            variant={scope === "pending" ? "no-data" : "no-match"}
            title={
              scope === "pending"
                ? "Nothing waiting on a decision"
                : "No requests in this state"
            }
            description={
              scope === "pending"
                ? "Requests from the business land here. Each one is screened against the register before anyone reads it."
                : "Switch the filter above to see the rest of the queue."
            }
          />
        ) : (
          <ul className="space-y-3">
            {items.map((r) => (
              <li key={r.id}>
                <IntakeCard request={r} canDecide={canDecide} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <RequestVendorDialog open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}

function IntakeCard({ request: r, canDecide }: { request: IntakeRequest; canDecide: boolean }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [declining, setDeclining] = useState(false);

  const decision = INTAKE_DECISION_META[r.decision] ?? {
    label: r.decision,
    family: "neutral" as const,
  };
  const screening = SCREENING_META[r.screening_status] ?? {
    label: r.screening_status,
    family: "neutral" as const,
  };
  const urgency = URGENCY_META[r.urgency] ?? { label: r.urgency, family: "neutral" as const };
  const pending = r.decision === "pending";

  const decide = useMutation({
    mutationFn: (input: { approve: boolean; reason?: string }) =>
      decideIntake(r.id, input.approve, input.reason ?? null),
    onSuccess: (next) => {
      void queryClient.invalidateQueries({ queryKey: ["vendor-intake"] });
      void queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setDeclining(false);
      if (next.created_vendor_id) {
        toast({ title: `${next.vendor_name} added to the register`, tone: "success" });
        navigate(`/vendors/${next.created_vendor_id}`);
        return;
      }
      toast({ title: "Request declined", tone: "neutral" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "vendor request"), tone: "danger" }),
  });

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-title-md text-text-primary">{r.vendor_name}</h2>
          <p className="mt-1 text-body-sm text-text-subtle">
            {[r.requested_by_name, r.department].filter(Boolean).join(" · ") || "Unattributed"}
            <span className="mx-1.5">·</span>
            {fmtDate(r.created_at)}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <StatusPill status={urgency.family} label={`${urgency.label} urgency`} kind="inline" />
          <StatusPill status={screening.family} label={screening.label} kind="inline" />
          <StatusPill status={decision.family} label={decision.label} />
        </div>
      </div>

      {r.proposed_service ? (
        <p className="mt-3 whitespace-pre-line text-body-md text-text-secondary">
          {r.proposed_service}
        </p>
      ) : (
        <p className="mt-3 text-body-sm text-text-subtle">
          No description of the intended use was given.
        </p>
      )}

      {r.data_types_shared.length > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="type-overline">Data shared</span>
          {r.data_types_shared.map((d) => (
            <Badge key={d} variant="neutral">
              {d}
            </Badge>
          ))}
        </div>
      ) : null}

      {r.duplicates.length > 0 ? (
        <div className="mt-3 rounded-md border border-status-warning-border bg-status-warning-bg p-3">
          <p className="flex items-center gap-1.5 text-label-sm text-status-warning-text">
            <Icon name="alert" className="size-4 shrink-0" />
            Already in the register
          </p>
          <ul className="mt-2 space-y-1">
            {r.duplicates.map((d) => (
              <li key={d.id} className="text-body-sm text-text-secondary">
                <Link
                  to={`/vendors/${d.id}`}
                  className="font-semibold text-text-link underline underline-offset-2"
                >
                  {d.name}
                </Link>
                <span className="text-text-subtle"> — {duplicateReason(d.reason)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-caption text-text-subtle">
            Approving creates a second record. Decline and point the requester at the existing
            vendor unless these really are different organisations.
          </p>
        </div>
      ) : null}

      {r.decision_reason ? (
        <p className="mt-3 border-t border-border pt-3 text-body-sm text-text-secondary">
          <span className="text-caption text-text-subtle">
            {decision.label} by {r.decided_by_name ?? "the system"} · {fmtDate(r.decided_at)}
          </span>
          <span className="mt-0.5 block">{r.decision_reason}</span>
        </p>
      ) : null}

      {r.created_vendor_id ? (
        <div className="mt-4 border-t border-border pt-3">
          <Link
            to={`/vendors/${r.created_vendor_id}`}
            className="inline-flex items-center gap-1 text-label-sm text-text-link"
          >
            Open the vendor this created
            <Icon name="chevr" className="size-4" />
          </Link>
        </div>
      ) : null}

      {pending && canDecide ? (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
          <Button
            size="sm"
            loading={decide.isPending && !declining}
            onClick={() => decide.mutate({ approve: true })}
          >
            <Icon name="check" className="size-4" />
            Approve and create the vendor
          </Button>
          <Button size="sm" variant="destructive-2" onClick={() => setDeclining(true)}>
            Decline
          </Button>
        </div>
      ) : pending ? (
        <p className="mt-4 border-t border-border pt-3 text-caption text-text-subtle">
          Waiting on someone with permission to manage vendors.
        </p>
      ) : null}

      <DeclineDialog
        open={declining}
        onOpenChange={setDeclining}
        vendorName={r.vendor_name}
        loading={decide.isPending}
        onDecline={(reason) => decide.mutate({ approve: false, reason })}
      />
    </div>
  );
}

function DeclineDialog({
  open,
  onOpenChange,
  vendorName,
  loading,
  onDecline,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorName: string;
  loading: boolean;
  onDecline: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setReason("");
      }}
    >
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Decline {vendorName}?</DialogTitle>
          <DialogDescription>
            The requester sees this reason. It is the only thing they get back, so say what would
            change the answer.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (reason.trim()) onDecline(reason.trim());
          }}
        >
          <DialogBody>
            <TextArea
              label="Why"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="We already have this capability under the Contoso agreement — ask Marketing Ops for access."
              autoFocus
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" loading={loading} disabled={!reason.trim()}>
              Decline request
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
