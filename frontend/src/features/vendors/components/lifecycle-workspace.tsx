import { useEffect, useMemo, useState } from "react";
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
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  TextArea,
  Tooltip,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { advanceStage, getFacets, getRoster, listMembers, sendBackStage, skipStage } from "../api";
import type { StageRow, VendorDetail } from "../types";
import { fmtDate, ROSTER_ROLE_META, STAGE_LABEL } from "../tokens";
import { Panel } from "./panel";
import { StageRail } from "./stage-rail";
import { ExitCheckRow } from "./exit-check-row";

/**
 * The lifecycle workspace: the rail on the left, the selected stage's work on
 * the right.
 *
 * The design rule the whole panel serves is that a blocker is a piece of work,
 * not a status. Every unmet check names what would clear it and offers the way
 * there; when the last one clears, the list collapses to a single line and the
 * advance control becomes the obvious next thing on screen, with the person it
 * hands to named beside it.
 */
export function LifecycleWorkspace({
  vendor,
  engagementId,
  canManage,
  onApply,
  onGo,
}: {
  vendor: VendorDetail;
  engagementId: string | null;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
  onGo: (target: string) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Only the engagement's own rows. The previous version also filtered on the
  // max cycle across EVERY engagement, so once one engagement was reassessed the
  // others rendered as an empty rail with a "Tier this engagement" button on an
  // engagement that was tiered and possibly at the gate. The service only ever
  // builds stage rows for an engagement's current cycle, so there is nothing
  // left to filter.
  const stages = useMemo(
    () => vendor.stages.filter((s) => engagementId === null || s.engagement_id === engagementId),
    [vendor.stages, engagementId],
  );

  // The stage the work is actually on: the first that is neither finished nor
  // skipped. It is NOT simply the one marked in_progress — a freshly tiered
  // engagement has twelve `not_started` rows and nothing in progress, because
  // a stage only enters in_progress when the one before it is completed. Keying
  // off in_progress alone hides the advance control at exactly the moment
  // somebody needs it, which is the first one.
  const current =
    stages.find((s) => s.status === "in_progress") ??
    stages.find((s) => s.status !== "complete" && s.status !== "skipped") ??
    null;
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Follow the work: when the current stage moves, the selection moves with it,
  // unless the reader has deliberately selected something else that still exists.
  useEffect(() => {
    setSelectedId((prev) =>
      prev && stages.some((s) => s.id === prev) ? prev : (current?.id ?? stages[0]?.id ?? null),
    );
  }, [stages, current?.id]);

  const selected = stages.find((s) => s.id === selectedId) ?? current ?? stages[0] ?? null;

  const [sendBackOpen, setSendBackOpen] = useState(false);
  const [skipOpen, setSkipOpen] = useState(false);

  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });
  const rosterQuery = useQuery({ queryKey: ["vendor-roster"], queryFn: getRoster });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  // Who signs THIS engagement's gate. Reading the vendor's cached worst tier
  // named the wrong reviewers for every engagement but the worst one.
  const engagementTier =
    vendor.engagements.find((e) => e.id === engagementId)?.tier ?? vendor.tier;
  const reviewerRoles = facetsQuery.data?.reviewer_roles_by_tier[engagementTier ?? ""] ?? [];

  const settle = (next: VendorDetail, title: string) => {
    onApply(next);
    void queryClient.invalidateQueries({ queryKey: ["vendors"] });
    toast({ title, tone: "success" });
  };
  const fail = (e: unknown) => toast({ title: errorToast(e, "lifecycle"), tone: "danger" });

  const advance = useMutation({
    mutationFn: (note?: string) => advanceStage(vendor.id, selected!.id, note ?? null),
    onSuccess: (next) => settle(next, `${selected?.label} complete`),
    onError: fail,
  });

  const sendBack = useMutation({
    mutationFn: (input: { toStage: string; reason: string }) =>
      sendBackStage(vendor.id, selected!.id, input.toStage, input.reason),
    onSuccess: (next) => {
      setSendBackOpen(false);
      settle(next, "Sent back");
    },
    onError: fail,
  });

  const skip = useMutation({
    mutationFn: (reason: string) => skipStage(vendor.id, selected!.id, reason),
    onSuccess: (next) => {
      setSkipOpen(false);
      settle(next, `${selected?.label} skipped`);
    },
    onError: fail,
  });

  if (stages.length === 0) {
    return (
      <Panel title="Lifecycle">
        <p className="text-body-md text-text-secondary">
          The lifecycle starts when the engagement is tiered — the tier decides which of the twelve
          stages this vendor actually needs.
        </p>
        {canManage ? (
          <Button className="mt-3" onClick={() => onGo("tiering")}>
            Tier this engagement
          </Button>
        ) : null}
      </Panel>
    );
  }

  return (
    <>
      <Panel
        title="Lifecycle"
        description={`Cycle ${selected?.cycle ?? 1}. A gate is never skipped, whatever the tier.`}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(14rem,17rem)_1fr]">
          <StageRail
            stages={stages}
            selectedId={selected?.id ?? null}
            currentId={current?.id ?? null}
            onSelect={(s) => setSelectedId(s.id)}
          />

          <div className="min-w-0">
            {selected ? (
              <StageDetail
                stage={selected}
                isCurrent={selected.id === current?.id}
                canManage={canManage}
                nextStage={nextActionableAfter(stages, selected)}
                reviewerRoles={reviewerRoles}
                reviewerNames={resolveReviewers(
                  reviewerRoles,
                  rosterQuery.data?.roles ?? {},
                  membersQuery.data ?? [],
                )}
                reviewersReady={
                  facetsQuery.isSuccess && rosterQuery.isSuccess && membersQuery.isSuccess
                }
                advancing={advance.isPending}
                onAdvance={() => advance.mutate(undefined)}
                onSendBack={() => setSendBackOpen(true)}
                onSkip={() => setSkipOpen(true)}
                onGo={onGo}
              />
            ) : null}
          </div>
        </div>
      </Panel>

      <SendBackDialog
        open={sendBackOpen}
        onOpenChange={setSendBackOpen}
        stages={stages}
        from={selected}
        loading={sendBack.isPending}
        onSubmit={(toStage, reason) => sendBack.mutate({ toStage, reason })}
      />
      <SkipDialog
        open={skipOpen}
        onOpenChange={setSkipOpen}
        stage={selected}
        loading={skip.isPending}
        onSubmit={(reason) => skip.mutate(reason)}
      />
    </>
  );
}

/** The next stage the review will actually enter — skipped ones are not it. */
function nextActionableAfter(stages: StageRow[], from: StageRow): StageRow | null {
  const index = stages.findIndex((s) => s.id === from.id);
  return stages.slice(index + 1).find((s) => s.status !== "skipped") ?? null;
}

function resolveReviewers(
  roles: string[],
  roster: Record<string, string[]>,
  members: { membership_id: string; name: string }[],
): { role: string; names: string[] }[] {
  return roles.map((role) => ({
    role,
    names: (roster[role] ?? []).map(
      (id) => members.find((m) => m.membership_id === id)?.name ?? "Unnamed member",
    ),
  }));
}

function StageDetail({
  stage,
  isCurrent,
  canManage,
  nextStage,
  reviewerRoles,
  reviewerNames,
  reviewersReady,
  advancing,
  onAdvance,
  onSendBack,
  onSkip,
  onGo,
}: {
  stage: StageRow;
  isCurrent: boolean;
  canManage: boolean;
  nextStage: StageRow | null;
  reviewerRoles: string[];
  reviewerNames: { role: string; names: string[] }[];
  /** All three lookups have resolved. Until they have, the card cannot honestly
   *  say whether anybody holds the role. */
  reviewersReady: boolean;
  advancing: boolean;
  onAdvance: () => void;
  onSendBack: () => void;
  onSkip: () => void;
  onGo: (target: string) => void;
}) {
  const blockers = stage.blockers;
  const pending = stage.pending;
  const met = stage.checks.filter((c) => c.satisfied === true);
  const canAdvance = stage.allowed_transitions.includes("advance");
  const canSendBack = stage.allowed_transitions.includes("send_back");
  const canSkip = stage.allowed_transitions.includes("skip");

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 font-display text-title-md text-text-primary">
            {stage.label}
            {stage.is_gate ? <Badge variant="role">Gate</Badge> : null}
            {stage.is_required ? (
              <Tooltip content="This stage cannot be skipped by any tier">
                <span>
                  <Badge variant="neutral">Required</Badge>
                </span>
              </Tooltip>
            ) : null}
          </h3>
          <p className="mt-1 text-body-sm text-text-subtle">
            {stage.entered_at ? `Entered ${fmtDate(stage.entered_at)}` : "Not entered yet"}
            {stage.exited_at ? ` · left ${fmtDate(stage.exited_at)}` : ""}
          </p>
        </div>
      </div>

      {stage.status === "complete" ? (
        // Exit checks are recomputed against today's facts, not frozen at exit.
        // Without this branch a stage finished in January renders "1 thing in
        // the way" with a live action button while the rail draws a tick on the
        // same row.
        <div className="mt-4 rounded-md border border-status-success-border bg-status-success-bg p-3.5">
          <p className="flex items-center gap-2 text-body-md text-status-success-text">
            <Icon name="check" className="size-4 shrink-0" />
            Completed {fmtDate(stage.exited_at)}
          </p>
          {blockers.length > 0 ? (
            <p className="mt-1 text-body-sm text-text-secondary">
              {blockers.length === 1
                ? "One condition that held when this stage was completed no longer does."
                : `${blockers.length} conditions that held when this stage was completed no longer do.`}{" "}
              That does not reopen it — send the review back if it needs doing again.
            </p>
          ) : null}
        </div>
      ) : stage.status === "skipped" ? (
        <div className="mt-4 rounded-md border border-border bg-surface-sunken p-4">
          <p className="text-body-md text-text-primary">This stage was skipped.</p>
          <p className="mt-1 text-body-sm text-text-subtle">
            {stage.skipped_by_policy
              ? `The tiering policy skips it for this tier: ${stage.skipped_by_policy}. Nobody chose this per vendor — change the policy to change it everywhere.`
              : (stage.skipped_reason ?? "No reason was recorded.")}
          </p>
        </div>
      ) : !isCurrent ? (
        <div className="mt-4">
          <p className="type-overline">What this stage will need</p>
          <ul className="mt-1 divide-y divide-border">
            {stage.checks.map((check) => (
              <ExitCheckRow key={check.code} check={check} />
            ))}
          </ul>
          <p className="mt-2 text-caption text-text-subtle">
            The review has not reached this stage yet. These are checked when it does.
          </p>
        </div>
      ) : blockers.length > 0 ? (
        <div className="mt-4">
          <p className="type-overline">
            {blockers.length} {blockers.length === 1 ? "thing" : "things"} in the way
          </p>
          <ul className="mt-1 divide-y divide-border">
            {blockers.map((check) => (
              <ExitCheckRow key={check.code} check={check} onGo={onGo} />
            ))}
          </ul>
        </div>
      ) : (
        // 5.6 — the handoff. Once nothing blocks, the checklist stops being the
        // subject of the screen and collapses to one line, so what is left on
        // screen is the move the reader came to make.
        <div className="mt-4 rounded-md border border-status-success-border bg-status-success-bg p-3.5">
          <p className="flex items-center gap-2 text-body-md text-status-success-text">
            <Icon name="check" className="size-4 shrink-0" />
            {met.length > 0
              ? `All ${met.length} ${met.length === 1 ? "check is" : "checks are"} clear`
              : "Nothing is blocking this stage"}
          </p>
          {pending.length > 0 ? (
            <p className="mt-1 text-body-sm text-status-success-text/80">
              {pending.length} {pending.length === 1 ? "check is" : "checks are"} not answerable
              yet and {pending.length === 1 ? "is" : "are"} not holding this up.
            </p>
          ) : null}
        </div>
      )}

      {pending.length > 0 && blockers.length > 0 ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-body-sm text-text-subtle">
            {pending.length} {pending.length === 1 ? "check" : "checks"} not answerable yet
          </summary>
          <ul className="mt-1 divide-y divide-border">
            {pending.map((check) => (
              <ExitCheckRow key={check.code} check={check} />
            ))}
          </ul>
        </details>
      ) : null}

      {met.length > 0 && blockers.length > 0 ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-body-sm text-text-subtle">
            {met.length} already met
          </summary>
          <ul className="mt-1 divide-y divide-border">
            {met.map((check) => (
              <ExitCheckRow key={check.code} check={check} />
            ))}
          </ul>
        </details>
      ) : null}

      {isCurrent && canManage ? (
        <div className="mt-4 border-t border-border pt-4">
          {nextStage && blockers.length === 0 && canAdvance ? (
            <NextActor
              stage={nextStage}
              reviewerRoles={reviewerRoles}
              reviewers={reviewerNames}
              ready={reviewersReady}
            />
          ) : null}

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              loading={advancing}
              disabled={!canAdvance || blockers.length > 0}
              onClick={onAdvance}
            >
              {nextStage ? `Complete and move to ${nextStage.label}` : "Complete this stage"}
            </Button>
            {canSendBack ? (
              <Button variant="secondary" onClick={onSendBack}>
                Send back
              </Button>
            ) : null}
            {canSkip ? (
              <Button variant="ghost" onClick={onSkip}>
                Skip this stage
              </Button>
            ) : null}
          </div>

          {blockers.length > 0 ? (
            <p className="mt-2 text-caption text-text-subtle">
              Clear what is in the way above, and this unlocks.
            </p>
          ) : null}
        </div>
      ) : isCurrent ? (
        <p className="mt-4 border-t border-border pt-3 text-caption text-text-subtle">
          Moving this along needs the Manage vendors permission.
        </p>
      ) : null}
    </div>
  );
}

/**
 * Naming the next actor is the difference between "the gate is open" and
 * "Priya can decide now". When nobody holds the role, say that instead — an
 * unassigned reviewer is the most common reason a review stalls silently.
 */
function NextActor({
  stage,
  reviewerRoles,
  reviewers,
  ready,
}: {
  stage: StageRow;
  reviewerRoles: string[];
  reviewers: { role: string; names: string[] }[];
  ready: boolean;
}) {
  if (!ready) {
    return (
      <div className="rounded-md border border-border bg-surface-sunken p-3.5">
        <p className="type-overline">Next</p>
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
    );
  }
  const relevant = stage.is_gate
    ? reviewers.filter((r) => r.role === "exec_approver" || reviewerRoles.includes(r.role))
    : reviewers;
  const named = relevant.filter((r) => r.names.length > 0);
  const unfilled = relevant.filter((r) => r.names.length === 0);

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-3.5">
      <p className="type-overline">Next</p>
      <p className="mt-1 text-body-md text-text-primary">
        {named.length > 0 ? (
          <>
            {stage.label} goes to{" "}
            {named.map((r, i) => (
              <span key={r.role}>
                {i > 0 ? ", " : ""}
                <span className="font-semibold">{r.names.join(" and ")}</span>
                <span className="text-text-subtle">
                  {" "}
                  ({ROSTER_ROLE_META[r.role]?.label ?? r.role})
                </span>
              </span>
            ))}
            .
          </>
        ) : (
          `${stage.label} has nobody named to pick it up.`
        )}
      </p>
      {unfilled.length > 0 ? (
        <p className="mt-1 text-body-sm text-status-warning-text">
          No one holds{" "}
          {unfilled.map((r) => ROSTER_ROLE_META[r.role]?.label ?? r.role).join(", ")} on the roster.
          Assign them or this will sit unread.
        </p>
      ) : null}
      {named.length > 0 ? (
        <Button
          variant="secondary"
          size="sm"
          className="mt-2.5"
          onClick={() => {
            const to = named.flatMap((r) => r.names).join(", ");
            const subject = encodeURIComponent(`Vendor review: ${stage.label} is ready for you`);
            const body = encodeURIComponent(
              `${stage.label} is unblocked and waiting on you.\n\n${window.location.href}`,
            );
            // No notification endpoint exists for vendor stages yet, so this
            // hands off through the reader's own mail client rather than
            // pretending a message was sent.
            window.location.href = `mailto:?subject=${subject}&body=${body}&to=${encodeURIComponent(to)}`;
          }}
        >
          <Icon name="bell" className="size-4" />
          Let them know
        </Button>
      ) : null}
    </div>
  );
}

function SendBackDialog({
  open,
  onOpenChange,
  stages,
  from,
  loading,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stages: StageRow[];
  from: StageRow | null;
  loading: boolean;
  onSubmit: (toStage: string, reason: string) => void;
}) {
  const earlier = from ? stages.slice(0, stages.findIndex((s) => s.id === from.id)) : [];
  const [toStage, setToStage] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) {
      setToStage(earlier[earlier.length - 1]?.stage ?? "");
      setReason("");
    }
    // The stage list is stable while the dialog is open; re-running on it would
    // clear what the reader is typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Send this review back</DialogTitle>
          <DialogDescription>
            The stages in between reopen. Whoever picks it up sees your reason, so write the thing
            that has to change.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (toStage && reason.trim()) onSubmit(toStage, reason.trim());
          }}
        >
          <DialogBody className="space-y-3.5">
            <SelectField label="Back to">
              <Select value={toStage} onValueChange={setToStage}>
                <SelectTrigger aria-label="Stage to return to" />
                <SelectContent>
                  {earlier.map((s) => (
                    <SelectItem key={s.id} value={s.stage}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextArea
              label="Why"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="The SOC 2 covers a period that ended 14 months ago. We need a current report or a bridge letter."
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={!toStage || !reason.trim()}>
              Send back to {STAGE_LABEL[toStage] ?? "stage"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SkipDialog({
  open,
  onOpenChange,
  stage,
  loading,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stage: StageRow | null;
  loading: boolean;
  onSubmit: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Skip {stage?.label}?</DialogTitle>
          <DialogDescription>
            A skip is recorded against this vendor with your name on it, and shows on the rail from
            then on. It is not the same as the policy skipping a stage for a whole tier.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (reason.trim()) onSubmit(reason.trim());
          }}
        >
          <DialogBody>
            <TextArea
              label="Why this one does not need it"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="No data leaves our estate — the vendor works on site with no system access."
              autoFocus
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={!reason.trim()}>
              Skip {stage?.label}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
