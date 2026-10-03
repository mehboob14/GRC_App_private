import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  CodeChip,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  type StatusFamily,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { useRequirementChain } from "@/features/connectors/hooks";
import type { RequirementChain } from "@/features/connectors/api";
import {
  AVAILABILITY,
  CADENCE,
  EVIDENCE_STATE,
} from "@/features/connectors/components/composition-meta";
import {
  ModeBadge,
  SourceChip,
} from "@/features/connectors/components/composition-ui";
import { TEST_STATE } from "@/features/connectors/components/automation-meta";

const CRITERION_STATE: Record<
  RequirementChain["state"],
  { label: string; family: StatusFamily; detail: string }
> = {
  met: {
    label: "Met",
    family: "success",
    detail: "Every control that applies is implemented, evidenced and passing.",
  },
  partly: {
    label: "Partly met",
    family: "progress",
    detail: "Some controls are ready. Every one that applies has to be.",
  },
  not_started: {
    label: "Not met",
    family: "pending",
    detail: "No control that applies is ready yet.",
  },
  no_controls: {
    label: "No control",
    family: "warning",
    detail: "Nothing in this workspace answers this criterion.",
  },
};

const CONTROL_STATUS: Record<string, { label: string; family: StatusFamily }> =
  {
    not_started: { label: "Not started", family: "pending" },
    in_progress: { label: "In progress", family: "progress" },
    implemented: { label: "Implemented", family: "success" },
    not_applicable: { label: "Not applicable", family: "neutral" },
  };

type ChainControl = RequirementChain["controls"][number];

function ControlCard({ item }: { item: ChainControl }) {
  const [open, setOpen] = useState(false);
  const status = CONTROL_STATUS[item.status] ?? CONTROL_STATUS.not_started;
  const chain = item.chain;
  return (
    <li className="rounded-lg border border-border bg-surface-primary">
      <div className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <CodeChip code={item.code} />
          <Link
            to={`/controls/${item.control_id}`}
            className="min-w-0 flex-1 truncate text-body-md font-semibold text-text-link hover:underline"
          >
            {item.name}
          </Link>
          <StatusPill kind="inline" status={status.family} label={status.label} />
          {item.ready ? (
            <Badge variant="statusPass">Ready</Badge>
          ) : null}
          {item.coverage ? (
            <Badge variant="neutral">
              {item.coverage === "full" ? "Primary route" : "Supports"}
            </Badge>
          ) : (
            <Badge variant="neutral">Added by your workspace</Badge>
          )}
        </div>
        {item.rationale ? (
          <p className="mt-1.5 text-body-sm text-text-secondary">
            {item.rationale}
          </p>
        ) : null}
        {chain ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ModeBadge mode={chain.composition.mode} />
            {chain.composition.sources.map((source) => (
              <SourceChip key={source.key} source={source} />
            ))}
            {chain.composition.items_manual + chain.composition.items_planned >
            0 ? (
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-body-sm font-semibold text-text-primary">
                <Icon name="users" className="size-3.5 text-text-secondary" />
                People provide{" "}
                {chain.composition.items_manual + chain.composition.items_planned}
              </span>
            ) : null}
          </div>
        ) : null}
        {chain && (chain.checks.length > 0 || chain.evidence.length > 0) ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-3 inline-flex items-center gap-1 text-body-sm font-semibold text-action-accent hover:underline"
          >
            {open ? "Hide checks and evidence" : "Show checks and evidence"}
            <Icon
              name="chev"
              className={cn("size-3.5 transition-transform", open && "rotate-180")}
            />
          </button>
        ) : null}
      </div>

      {open && chain ? (
        <div className="space-y-4 border-t border-border px-4 py-4">
          {chain.checks.length > 0 ? (
            <div>
              <p className="type-overline mb-1.5">Checks</p>
              <ul className="space-y-1.5">
                {chain.checks.map((check) => {
                  const state = TEST_STATE[check.status];
                  return (
                    <li
                      key={check.key}
                      className="flex flex-wrap items-center gap-x-3 gap-y-1"
                    >
                      <StatusPill
                        kind="inline"
                        status={state.family}
                        label={state.label}
                      />
                      <span className="text-body-sm font-semibold text-text-primary">
                        {check.name}
                      </span>
                      <span className="text-caption text-text-subtle">
                        {check.source === "platform" ? "Verity" : "System"}.{" "}
                        {AVAILABILITY[check.availability]}
                      </span>
                      {check.evidence_kinds.length > 0 ? (
                        <span className="text-caption text-text-subtle">
                          Collects {check.evidence_kinds.join(", ").toLowerCase()}
                        </span>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          {chain.evidence.length > 0 ? (
            <div>
              <p className="type-overline mb-1.5">Evidence expected</p>
              <ul className="space-y-1.5">
                {chain.evidence.map((evidence) => {
                  const state = EVIDENCE_STATE[evidence.state];
                  return (
                    <li
                      key={evidence.key}
                      className="flex flex-wrap items-center gap-x-3 gap-y-1"
                    >
                      <StatusPill
                        kind="inline"
                        status={state.family}
                        label={state.label}
                      />
                      <span className="text-body-sm text-text-primary">
                        {evidence.name}
                      </span>
                      <span className="text-caption text-text-subtle">
                        {CADENCE[evidence.cadence]}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

/**
 * A criterion, read top down the way a buyer's auditor reads it: the controls that
 * answer it, why each one does, what checks and evidence stand behind each, and
 * whether the criterion is met. Whether it is met is the dashboard's rule, not a
 * second opinion computed here.
 */
export function RequirementChainDialog({
  requirementId,
  onClose,
}: {
  requirementId: string | null;
  onClose: () => void;
}) {
  const chain = useRequirementChain(requirementId);
  const data = chain.data;
  const state = data ? CRITERION_STATE[data.state] : null;
  const ready = data?.controls.filter((c) => c.ready).length ?? 0;

  return (
    <Dialog
      open={requirementId !== null}
      onOpenChange={(next) => (next ? undefined : onClose())}
    >
      <DialogContent size="xl" scrollBody className="max-h-[90vh] p-0">
        <DialogHeader className="border-b border-border px-6 pb-4 pt-5">
          <DialogTitle className="flex flex-wrap items-center gap-2">
            {data ? <CodeChip code={data.requirement.code} /> : null}
            <span>How this criterion is met</span>
            {state ? <StatusPill status={state.family} label={state.label} /> : null}
          </DialogTitle>
          <DialogDescription>
            {data?.requirement.name ?? "Loading the criterion"}
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {chain.isError ? (
            <ErrorState
              title="The criterion could not load"
              onRetry={() => void chain.refetch()}
            />
          ) : !data ? (
            <div className="space-y-3">
              <Skeleton className="h-24 w-full rounded-lg" />
              <Skeleton className="h-24 w-full rounded-lg" />
            </div>
          ) : (
            <>
              <p className="mb-4 text-body-sm text-text-subtle">
                {state?.detail} {ready} of {data.controls.length} controls are
                ready.
              </p>
              {data.controls.length === 0 ? null : (
                <ul className="space-y-3">
                  {data.controls.map((item) => (
                    <ControlCard key={item.control_id} item={item} />
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
