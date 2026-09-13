import { useEffect, useMemo, useState, type ReactNode } from "react";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextArea,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { advanceStage, getFacets, getRoster, listMembers, sendBackStage, skipStage } from "../api";
import type { StageRow, Tiering, VendorDetail } from "../types";
import { fmtDate, ROSTER_ROLE_META, STAGE_LABEL, STAGE_STATUS_META, TIER_META } from "../tokens";
import { ApprovalSection } from "./approval-panel";
import { ExitCheckRow } from "./exit-check-row";
import { StageRail, type RailItem } from "./stage-rail";
import { TierBadge } from "./tier-badge";
import { TieringDialog, TierSummary } from "./tiering-panel";

/** The rail's id for the tiering step before any stage rows exist. */
const TIERING_STEP = "tiering";

/**
 * The lifecycle workspace: a summary strip, the stages as a sub-navigation on
 * the left, and the selected stage's work on the right.
 *
 * Tiering leads until it is done. An untiered engagement has no stage rows at
 * all, so the rail shows tiering as the one live step with every other stage
 * locked beneath it. Once tiered, tiering drops into its own place in the
 * sequence and the work moves on to whatever is current.
 *
 * Tiering and the approval decision live inside their stages rather than as
 * panels stacked underneath, so the whole lifecycle fits on one screen.
 */
export function LifecycleWorkspace({
  vendor,
  engagementId,
  canManage,
  canAssess,
  canApprove,
  onApply,
  onGo,
}: {
  vendor: VendorDetail;
  engagementId: string | null;
  canManage: boolean;
  canAssess: boolean;
  canApprove: boolean;
  onApply: (next: VendorDetail) => void;
  onGo: (target: string) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const stages = useMemo(
    () => vendor.stages.filter((s) => engagementId === null || s.engagement_id === engagementId),
    [vendor.stages, engagementId],
  );

  const latest = useMemo<Tiering | null>(() => {
    const rows = vendor.tierings.filter((t) => t.engagement_id === engagementId);
    return rows.length > 0 ? rows.reduce((a, b) => (b.cycle >= a.cycle ? b : a)) : null;
  }, [vendor.tierings, engagementId]);

  // The stage the work is on: the first neither finished nor skipped. A freshly
  // tiered engagement has twelve `not_started` rows and none in progress, so
  // keying off in_progress alone hides the advance control at the first stage.
  const current =
    stages.find((s) => s.status === "in_progress") ??
    stages.find((s) => s.status !== "complete" && s.status !== "skipped") ??
    null;

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tieringOpen, setTieringOpen] = useState(false);
  const [sendBackOpen, setSendBackOpen] = useState(false);
  const [skipOpen, setSkipOpen] = useState(false);

  // Follow the work: when the current stage moves, the selection moves with it,
  // unless the reader deliberately selected something that still exists.
  useEffect(() => {
    setSelectedId((prev) =>
      prev && stages.some((s) => s.id === prev) ? prev : (current?.id ?? stages[0]?.id ?? null),
    );
  }, [stages, current?.id]);

  const selected = stages.find((s) => s.id === selectedId) ?? current ?? stages[0] ?? null;

  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });
  const rosterQuery = useQuery({ queryKey: ["vendor-roster"], queryFn: getRoster });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  // Who signs THIS engagement's gate, not the vendor's worst engagement's.
  const engagementTier = vendor.engagements.find((e) => e.id === engagementId)?.tier ?? null;
  const reviewerRoles = facetsQuery.data?.reviewer_roles_by_tier[engagementTier ?? ""] ?? [];

  const settle = (next: VendorDetail, title: string) => {
    onApply(next);
    void queryClient.invalidateQueries({ queryKey: ["vendors"] });
    toast({ title, tone: "success" });
  };
  const fail = (e: unknown) => toast({ title: errorToast(e, "lifecycle"), tone: "danger" });

  const advance = useMutation({
    mutationFn: () => advanceStage(vendor.id, selected!.id, null),
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

  /** A blocker's action. Tiering and the decision are handled here, not by a tab. */
  const go = (target: string) => {
    if (target === "tiering") {
      setTieringOpen(true);
      return;
    }
    if (target === "approval") {
      const gate = stages.find((s) => s.is_gate);
      if (gate) setSelectedId(gate.id);
      return;
    }
    if (target === "lifecycle") return;
    onGo(target);
  };

  if (!engagementId) {
    return (
      <section className="rounded-lg border border-border bg-surface-primary px-6 py-10 text-center">
        <p className="font-display text-title-md text-text-primary">No engagement yet</p>
        <p className="mt-1 text-body-sm text-text-subtle">The lifecycle runs per engagement.</p>
        {canManage ? (
          <Button className="mt-4" onClick={() => onGo("engagement")}>
            <Icon name="plus" className="size-4" />
            Add engagement
          </Button>
        ) : null}
      </section>
    );
  }

  const tiered = stages.length > 0;
  const settled = stages.filter((s) => s.status === "complete" || s.status === "skipped").length;
  const tieringRow = stages.find((s) => s.stage === "tiering");

  const items: RailItem[] = tiered
    ? stages.map((s) => railItem(s, current, latest))
    : [
        { id: TIERING_STEP, label: STAGE_LABEL.tiering, state: "current", isGate: false, meta: "Start" },
        ...Object.entries(STAGE_LABEL)
          .filter(([key]) => key !== "tiering")
          .map(([key, label]) => ({
            id: key,
            label,
            state: "locked" as const,
            isGate: key === "approval",
          })),
      ];

  return (
    <>
      <section className="overflow-hidden rounded-lg border border-border bg-surface-primary">
        <header className="flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-border px-5 py-3">
          {tiered ? (
            <>
              <StripItem label="Tier">
                <button
                  type="button"
                  onClick={() => tieringRow && setSelectedId(tieringRow.id)}
                  className="flex items-center gap-2 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
                >
                  <TierBadge tier={engagementTier} />
                  {latest ? (
                    <span className="tabular text-body-md font-semibold text-text-primary">
                      {latest.score}
                    </span>
                  ) : null}
                </button>
              </StripItem>
              <StripItem label="Progress">
                <span className="flex items-center gap-2.5">
                  <span className="flex h-1.5 w-28 overflow-hidden rounded-full bg-border">
                    <span
                      className="h-full rounded-full bg-status-success-base"
                      style={{ width: `${(settled / stages.length) * 100}%` }}
                    />
                  </span>
                  <span className="tabular text-body-sm text-text-secondary">
                    {settled}/{stages.length}
                  </span>
                </span>
              </StripItem>
              <StripItem label="Now">
                {current ? (
                  <button
                    type="button"
                    onClick={() => setSelectedId(current.id)}
                    className="flex items-center gap-2 rounded-sm text-body-md font-semibold text-text-primary hover:text-text-link focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
                  >
                    {current.label}
                    {current.blockers.length > 0 ? (
                      <Badge variant="countWarn">{current.blockers.length} to clear</Badge>
                    ) : null}
                  </button>
                ) : (
                  <span className="text-body-md text-text-secondary">All stages settled</span>
                )}
              </StripItem>
              <span className="ml-auto text-caption text-text-subtle">
                Cycle {selected?.cycle ?? 1}
              </span>
            </>
          ) : (
            <>
              <StripItem label="Tier">
                <TierBadge tier={null} />
              </StripItem>
              <p className="text-body-sm text-text-subtle">Stages unlock after tiering.</p>
            </>
          )}
        </header>

        <div className="grid lg:grid-cols-[15rem_minmax(0,1fr)]">
          <div className="border-b border-border p-3 lg:border-b-0 lg:border-r">
            <StageRail
              items={items}
              selectedId={tiered ? (selected?.id ?? null) : TIERING_STEP}
              onSelect={(id) => (tiered ? setSelectedId(id) : setTieringOpen(true))}
            />
          </div>

          <div className="min-w-0 p-5">
            {tiered && selected ? (
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
                onAdvance={() => advance.mutate()}
                onSendBack={() => setSendBackOpen(true)}
                onSkip={() => setSkipOpen(true)}
                onGo={go}
              >
                {selected.stage === "tiering" && latest ? (
                  <TierSummary
                    latest={latest}
                    canAssess={canAssess}
                    onRetier={() => setTieringOpen(true)}
                  />
                ) : null}
                {selected.is_gate ? (
                  <ApprovalSection
                    vendor={vendor}
                    engagementId={engagementId}
                    canApprove={canApprove}
                    canManage={canManage}
                    onApply={onApply}
                  />
                ) : null}
              </StageDetail>
            ) : (
              <TieringStart
                factors={(facetsQuery.data?.tiering_factors ?? []).map((f) => f.label)}
                canAssess={canAssess}
                onStart={() => setTieringOpen(true)}
              />
            )}
          </div>
        </div>
      </section>

      <TieringDialog
        open={tieringOpen}
        onOpenChange={setTieringOpen}
        vendor={vendor}
        engagementId={engagementId}
        latest={latest}
        onApply={(next) => {
          onApply(next);
          void queryClient.invalidateQueries({ queryKey: ["vendors"] });
        }}
      />
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

function railItem(stage: StageRow, current: StageRow | null, latest: Tiering | null): RailItem {
  const isCurrent = stage.id === current?.id;
  const skipReason = stage.skipped_by_policy
    ? `Skipped by policy: ${stage.skipped_by_policy}`
    : (stage.skipped_reason ?? undefined);
  const state: RailItem["state"] =
    stage.status === "complete"
      ? "done"
      : stage.status === "skipped"
        ? "skipped"
        : isCurrent
          ? stage.blockers.length > 0
            ? "blocked"
            : "current"
          : "upcoming";
  const meta =
    state === "blocked"
      ? `${stage.blockers.length} open`
      : state === "current"
        ? "Now"
        : state === "skipped"
          ? "Skipped"
          : stage.stage === "tiering" && latest
            ? TIER_META[latest.effective_tier]?.label
            : undefined;
  return {
    id: stage.id,
    label: stage.label,
    state,
    isGate: stage.is_gate,
    meta,
    tooltip: state === "skipped" ? skipReason : undefined,
  };
}

function StripItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="type-overline">{label}</span>
      {children}
    </div>
  );
}

function TieringStart({
  factors,
  canAssess,
  onStart,
}: {
  factors: string[];
  canAssess: boolean;
  onStart: () => void;
}) {
  return (
    <div className="flex max-w-lg flex-col items-start py-2">
      <span className="grid size-10 place-items-center rounded-md bg-action-accent-tint text-action-accent">
        <Icon name="gauge" className="size-5" />
      </span>
      <h3 className="mt-3 font-display text-title-md text-text-primary">Tier this engagement</h3>
      <p className="mt-1 text-body-sm text-text-subtle">
        Five questions. The tier unlocks every other stage.
      </p>
      {factors.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-1.5">
          {factors.map((f) => (
            <li key={f}>
              <Badge variant="neutral">{f}</Badge>
            </li>
          ))}
        </ul>
      ) : null}
      {canAssess ? (
        <Button className="mt-5" onClick={onStart}>
          Start tiering
          <Icon name="arrowr" className="size-4" />
        </Button>
      ) : (
        <p className="mt-4 text-caption text-text-subtle">Needs the Assess vendors permission.</p>
      )}
    </div>
  );
}

/** The next stage the review will actually enter. Skipped ones are not it. */
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

function Callout({ tone, children }: { tone: "success" | "neutral"; children: ReactNode }) {
  return (
    <p
      className={cn(
        "mt-4 flex items-center gap-2 rounded-md px-3.5 py-2.5 text-body-sm",
        tone === "success"
          ? "bg-status-success-bg text-status-success-text"
          : "bg-surface-sunken text-text-secondary",
      )}
    >
      {tone === "success" ? <Icon name="check" className="size-4 shrink-0" /> : null}
      {children}
    </p>
  );
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
  children,
}: {
  stage: StageRow;
  isCurrent: boolean;
  canManage: boolean;
  nextStage: StageRow | null;
  reviewerRoles: string[];
  reviewerNames: { role: string; names: string[] }[];
  /** All three lookups resolved. Until then nobody can honestly say who holds a role. */
  reviewersReady: boolean;
  advancing: boolean;
  onAdvance: () => void;
  onSendBack: () => void;
  onSkip: () => void;
  onGo: (target: string) => void;
  /** Stage-specific work: the tier on Tiering, the decision on the gate. */
  children?: ReactNode;
}) {
  const { blockers, pending } = stage;
  const met = stage.checks.filter((c) => c.satisfied === true);
  const complete = stage.status === "complete";
  const skipped = stage.status === "skipped";
  const canAdvance = stage.allowed_transitions.includes("advance");
  const canSendBack = stage.allowed_transitions.includes("send_back");
  const canSkip = stage.allowed_transitions.includes("skip");
  const status = STAGE_STATUS_META[stage.status] ?? { label: stage.status, family: "neutral" as const };

  // Blocking first, then the ones nobody can answer yet, then what is met.
  // Exit checks are recomputed against today, so a completed stage lists only
  // what has stopped holding since, and a skipped one lists nothing.
  const checks = complete ? blockers : skipped ? [] : [...blockers, ...pending, ...met];

  const completeButton = (
    <Button loading={advancing} disabled={!canAdvance || blockers.length > 0} onClick={onAdvance}>
      <Icon name="check" className="size-4" />
      Complete stage
    </Button>
  );

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-title-md text-text-primary">{stage.label}</h3>
            {stage.is_gate ? <Badge variant="role">Gate</Badge> : null}
            <StatusPill
              status={isCurrent && stage.status === "not_started" ? "progress" : status.family}
              label={isCurrent && stage.status === "not_started" ? "Up next" : status.label}
              kind="inline"
            />
          </div>
          <p className="mt-0.5 text-caption text-text-subtle">
            {stage.entered_at ? `Entered ${fmtDate(stage.entered_at)}` : "Not entered"}
            {stage.exited_at ? ` · left ${fmtDate(stage.exited_at)}` : ""}
          </p>
        </div>

        {isCurrent && canManage ? (
          <div className="flex items-center gap-2">
            {blockers.length > 0 ? (
              <Tooltip content="Clear the open checks first">
                <span>{completeButton}</span>
              </Tooltip>
            ) : (
              completeButton
            )}
            {canSendBack || canSkip ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="icon" aria-label="More stage actions">
                    <Icon name="more" className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {canSendBack ? (
                    <DropdownMenuItem onSelect={onSendBack}>Send back</DropdownMenuItem>
                  ) : null}
                  {canSkip ? (
                    <DropdownMenuItem onSelect={onSkip}>Skip stage</DropdownMenuItem>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </div>
        ) : null}
      </div>

      {complete ? (
        <Callout tone="success">
          Completed {fmtDate(stage.exited_at)}
          {blockers.length > 0
            ? `. ${blockers.length} ${blockers.length === 1 ? "check no longer holds" : "checks no longer hold"}.`
            : ""}
        </Callout>
      ) : skipped ? (
        <Callout tone="neutral">
          {stage.skipped_by_policy
            ? `Skipped by policy for this tier: ${stage.skipped_by_policy}`
            : `Skipped: ${stage.skipped_reason ?? "no reason recorded"}`}
        </Callout>
      ) : null}

      {children ? <div className="mt-4">{children}</div> : null}

      {checks.length > 0 ? (
        <div className="mt-5">
          <p className="type-overline">
            {isCurrent && blockers.length > 0 ? `${blockers.length} to clear` : "Checks"}
          </p>
          <ul className="mt-1 divide-y divide-border">
            {checks.map((check) => (
              <ExitCheckRow
                key={check.code}
                check={check}
                onGo={isCurrent && canManage ? onGo : undefined}
              />
            ))}
          </ul>
          {!isCurrent && !complete ? (
            <p className="mt-1 text-caption text-text-subtle">Checked when this stage starts.</p>
          ) : null}
        </div>
      ) : null}

      {isCurrent && canManage && nextStage && blockers.length === 0 && canAdvance ? (
        <NextActor
          stage={nextStage}
          reviewerRoles={reviewerRoles}
          reviewers={reviewerNames}
          ready={reviewersReady}
          onGo={onGo}
        />
      ) : null}

      {isCurrent && !canManage ? (
        <p className="mt-4 text-caption text-text-subtle">
          Moving this along needs the Manage vendors permission.
        </p>
      ) : null}
    </div>
  );
}

/**
 * Naming the next actor turns "the gate is open" into "Priya can decide now".
 * When nobody holds the role, say so: an unassigned reviewer is the commonest
 * reason a review stalls silently.
 */
function NextActor({
  stage,
  reviewerRoles,
  reviewers,
  ready,
  onGo,
}: {
  stage: StageRow;
  reviewerRoles: string[];
  reviewers: { role: string; names: string[] }[];
  ready: boolean;
  onGo: (target: string) => void;
}) {
  if (!ready) return <Skeleton className="mt-5 h-11 w-full" />;

  const relevant = stage.is_gate
    ? reviewers.filter((r) => r.role === "exec_approver" || reviewerRoles.includes(r.role))
    : reviewers;
  const named = relevant.filter((r) => r.names.length > 0);
  const unfilled = relevant.filter((r) => r.names.length === 0);
  const roleLabel = (role: string) => ROSTER_ROLE_META[role]?.label ?? role;

  return (
    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-md bg-surface-sunken px-3.5 py-2.5">
      <div className="min-w-0 text-body-sm text-text-secondary">
        <span className="type-overline mr-2">Next</span>
        <span className="font-semibold text-text-primary">{stage.label}</span>
        {named.length > 0 ? (
          <>
            {" goes to "}
            {named.map((r, i) => (
              <span key={r.role}>
                {i > 0 ? ", " : ""}
                <span className="font-semibold text-text-primary">{r.names.join(" and ")}</span>
                <span className="text-text-subtle"> ({roleLabel(r.role)})</span>
              </span>
            ))}
          </>
        ) : null}
        {unfilled.length > 0 ? (
          <span className="block text-status-warning-text">
            No {unfilled.map((r) => roleLabel(r.role)).join(", ")} on the roster
          </span>
        ) : null}
      </div>
      {unfilled.length > 0 ? (
        <Button variant="secondary" size="sm" onClick={() => onGo("roster")}>
          Open roster
        </Button>
      ) : named.length > 0 ? (
        <Button
          variant="secondary"
          size="sm"
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
          Notify
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
          <DialogTitle>Send back</DialogTitle>
          <DialogDescription>The stages in between reopen.</DialogDescription>
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
              label="What has to change"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="The SOC 2 period ended 14 months ago. We need a current report."
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
          <DialogDescription>Recorded against this vendor with your name.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (reason.trim()) onSubmit(reason.trim());
          }}
        >
          <DialogBody>
            <TextArea
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={4000}
              placeholder="The vendor works on site with no system access."
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
