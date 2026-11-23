import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
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
  PageHeader,
  Skeleton,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { onboardingApi, type Proposal } from "../api";
import { DraftButton } from "./draft-button";

/**
 * Suggestions from the company profile (guided onboarding PL-1 to PL-5). Each one is a change
 * a person accepts or rejects; nothing changes on its own. Groups a person may accept at once
 * offer "Accept all"; the rest open one at a time, in a popup with the reason to edit.
 */

const STATE: Record<Proposal["state"], { family: StatusFamily; label: string }> = {
  open: { family: "pending", label: "Waiting" },
  accepted: { family: "success", label: "Accepted" },
  rejected: { family: "neutral", label: "Rejected" },
  review_needed: { family: "warning", label: "Look again" },
};

const FRAMEWORK: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

/** Where a decision lives, for one whose answer has since changed. */
const RECORD: Record<Proposal["kind"], string> = {
  control_status: "/controls",
  iso_applicability: "/frameworks/soa?framework=ISO27001",
  soc2_category: "/frameworks/scope?framework=SOC2",
};

export function SuggestionsPage() {
  const { principal } = useAuth();
  const canDecide = hasPermission(principal, "controls:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["onboarding-proposals", principal?.tenant_id],
    queryFn: onboardingApi.proposals,
  });
  const [open, setOpen] = useState<Proposal | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const decide = useMutation({
    mutationFn: onboardingApi.decide,
    onSuccess: async (result, vars) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["onboarding-proposals"] }),
        queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
        queryClient.invalidateQueries({ queryKey: ["controls"] }),
      ]);
      setOpen(null);
      toast({
        title: vars.accept ? `${result.decided} accepted` : "Rejected",
        tone: "success",
      });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "suggestion"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "suggestions");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  const all = query.data.proposals;
  const waiting = all.filter((p) => p.state === "open" || p.state === "review_needed");
  const decided = all.filter((p) => p.state === "accepted" || p.state === "rejected");
  const groups = new Map<string, Proposal[]>();
  for (const p of waiting) groups.set(p.because, [...(groups.get(p.because) ?? []), p]);

  const show = (p: Proposal) => {
    setOpen(p);
    setRejecting(false);
    setReason(p.reason);
  };

  return (
    <div className="mx-auto w-full max-w-[960px]">
      <PageHeader title="Suggestions from your profile" />
      <p className="mt-2 text-body-sm text-text-secondary">
        {waiting.length} waiting, {decided.length} decided.{" "}
        <Link to="/settings/organization/profile" className="text-text-link">
          Change your answers
        </Link>
      </p>

      {waiting.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="Nothing waiting"
            description="New suggestions appear here when your profile answers change."
          />
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {[...groups.entries()].map(([because, items]) => {
            const bulk = items.filter((p) => p.state === "open" && p.bulk_ok);
            return (
              <section key={because} className="rounded-lg border border-border bg-surface-primary">
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
                  <p className="text-body-md text-text-primary">{because}</p>
                  {canDecide && bulk.length > 1 ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={decide.isPending}
                      onClick={() =>
                        decide.mutate({ keys: bulk.map((p) => p.key), accept: true, bulk: true })
                      }
                    >
                      Accept all {bulk.length}
                    </Button>
                  ) : null}
                </header>
                {items.map((p) => (
                  <Row key={p.key} p={p} onOpen={canDecide ? () => show(p) : undefined} />
                ))}
              </section>
            );
          })}
        </div>
      )}

      {decided.length ? (
        <details className="mt-5 rounded-lg border border-border bg-surface-primary">
          <summary className="cursor-pointer px-5 py-3 text-body-sm text-text-secondary">
            Decided ({decided.length})
          </summary>
          {decided.map((p) => (
            <Row key={p.key} p={p} onOpen={canDecide && p.state === "rejected" ? () => show(p) : undefined} />
          ))}
        </details>
      ) : null}

      <Dialog open={open !== null} onOpenChange={(v) => (v ? null : setOpen(null))}>
        <DialogContent size="md">
          {open ? (
            <>
              <DialogHeader>
                <DialogTitle>
                  {open.subject} {open.subject_name !== open.subject ? open.subject_name : ""}
                </DialogTitle>
                <DialogDescription>{open.change}</DialogDescription>
              </DialogHeader>
              <DialogBody>
                <p className="mb-3 text-body-sm text-text-secondary">{open.because}</p>
                <TextArea
                  label={rejecting ? "Why does this not fit?" : "Reason on record"}
                  rows={5}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                {!rejecting && open.state === "open" ? (
                  <DraftButton kind="proposal_reason" subject={open.key} onDraft={setReason} label="Reword with AI" />
                ) : null}
              </DialogBody>
              <DialogFooter>
                {rejecting ? (
                  <>
                    <Button variant="secondary" onClick={() => { setRejecting(false); setReason(open.reason); }}>
                      Back
                    </Button>
                    <Button
                      variant="destructive"
                      disabled={!reason.trim()}
                      loading={decide.isPending}
                      onClick={() => decide.mutate({ keys: [open.key], accept: false, reason })}
                    >
                      Reject
                    </Button>
                  </>
                ) : (
                  <>
                    {open.state !== "rejected" ? (
                      <Button variant="secondary" onClick={() => { setRejecting(true); setReason(""); }}>
                        Not for us
                      </Button>
                    ) : null}
                    <Button
                      disabled={!reason.trim()}
                      loading={decide.isPending}
                      onClick={() => decide.mutate({ keys: [open.key], accept: true, reason })}
                    >
                      Accept
                    </Button>
                  </>
                )}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Row({ p, onOpen }: { p: Proposal; onOpen?: () => void }) {
  const state = STATE[p.state];
  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-3 first:border-t-0">
      <span className="min-w-[72px] font-mono text-body-sm text-text-primary">{p.subject}</span>
      <span className="min-w-0 flex-1 text-body-sm text-text-secondary">
        {p.subject_name !== p.subject ? `${p.subject_name}. ` : ""}
        {p.change}
      </span>
      {p.framework ? (
        <span className="rounded-sm bg-surface-sunken px-1.5 py-px text-caption text-text-secondary">
          {FRAMEWORK[p.framework] ?? p.framework}
        </span>
      ) : null}
      <StatusPill status={state.family} label={state.label} />
      {p.state === "review_needed" ? (
        <Button asChild size="sm" variant="ghost">
          <Link to={RECORD[p.kind]}>Open</Link>
        </Button>
      ) : onOpen ? (
        <Button size="sm" variant="ghost" onClick={onOpen}>
          {p.state === "rejected" ? "Reconsider" : "Review"}
        </Button>
      ) : null}
    </div>
  );
}
