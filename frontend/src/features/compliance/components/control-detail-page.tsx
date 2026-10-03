import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  CodeChip,
  DetailHeader,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  useToast,
  TabStrip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  auditApi,
  complianceApi,
  controlsApi,
  evidenceApi,
  iamApi,
} from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import {
  AttachEvidenceDialog,
  EditControlDialog,
} from "@/features/compliance/components/control-detail-dialogs";
// The evidence library owns the add-evidence form. Reused here rather than
// re-implemented, so the fields cannot drift between the two entry points.
import { AddEvidenceDialog } from "@/features/evidence/components/evidence-page";
import { OwnerSelect } from "@/features/iam/components/owner-select";
import { LinkedRecordsPanel } from "@/features/linkage/components/linked-records-panel";
import {
  AutomationHeaderButton,
  AutomationSummary,
} from "@/features/connectors/components/automation-panel";
import { ChecksPanel } from "@/features/connectors/components/checks-panel";
import { RequirementChainDialog } from "@/features/compliance/components/requirement-chain-dialog";
import { ago, type CriterionMapping } from "@/features/connectors/api";
import { useAutomation } from "@/features/connectors/hooks";
import { useLinkedRecords } from "@/features/linkage/hooks";
import type { Control, Evidence, EvidenceFreshness } from "@/lib/api/types";

const STATUS_LABEL: Record<string, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  implemented: "Implemented",
  not_applicable: "Not applicable",
};

const STATUS_FAMILY: Record<
  string,
  "success" | "progress" | "pending" | "neutral"
> = {
  not_started: "pending",
  in_progress: "progress",
  implemented: "success",
  not_applicable: "neutral",
};

const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
};

function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

/** A rail fact. `muted` marks a value the platform cannot measure yet, so it
 *  reads as absent rather than as a result. */
function Fact({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 last:border-0">
      <span className="shrink-0 text-body-sm text-text-subtle">{label}</span>
      <span
        className={cn(
          "min-w-0 text-right text-body-sm font-semibold",
          muted ? "text-text-faint" : "text-text-primary",
        )}
      >
        {value}
      </span>
    </div>
  );
}

/** Guidance arrives as prose that often contains sentence-per-step text. Split
 *  on newlines when the author supplied them; otherwise render one block rather
 *  than inventing bullets by splitting sentences. */
function Guidance({ text }: { text: string }) {
  const lines = text
    .split(/\n+/)
    .map((line) => line.replace(/^[-•*]\s*/, "").trim())
    .filter(Boolean);

  if (lines.length <= 1) {
    return (
      <p className="whitespace-pre-line text-body-md leading-relaxed text-text-secondary">
        {text}
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {lines.map((line) => (
        <li
          key={line}
          className="flex gap-2.5 text-body-md leading-relaxed text-text-secondary"
        >
          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-text-faint" />
          <span className="min-w-0">{line}</span>
        </li>
      ))}
    </ul>
  );
}

const FIELD_LABEL: Record<string, string> = {
  name: "Name",
  description: "Statement",
  implementation_guidance: "Guidance",
  category: "Type",
  sub_category: "Sub-type",
  control_type: "Design",
  control_sub_type: "Automation",
  status: "Status",
  owner_membership_id: "Owner",
  disabled_at: "Disabled",
  disabled_reason: "Reason",
};

/** The fields that actually moved between two audit snapshots. A raw JSON dump
 *  is technically the truth and practically unreadable, so this names the field
 *  and shows old → new. */
function ChangeSummary({
  before,
  after,
  names,
}: {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  /** membership id → person. An owner change must read as a name; a raw UUID
   *  tells a reader nothing about who now owns the control. */
  names: Map<string, string>;
}) {
  const changes = useMemo(() => {
    if (!after) return [];
    const keys = new Set([...Object.keys(before ?? {}), ...Object.keys(after)]);
    return [...keys]
      .filter(
        (key) => key !== "id" && key !== "evidence_linked" && FIELD_LABEL[key],
      )
      .map((key) => ({ key, from: before?.[key], to: after[key] }))
      .filter(
        (change) => JSON.stringify(change.from) !== JSON.stringify(change.to),
      );
  }, [before, after]);

  const linkedNow = after?.evidence_linked;
  const linkedBefore = before?.evidence_linked;
  if (linkedNow || linkedBefore) {
    return (
      <p className="mt-1.5 text-body-sm text-text-secondary">
        {linkedNow ? "Linked evidence" : "Unlinked evidence"}{" "}
        <span className="font-semibold text-text-primary">
          {String(linkedNow ?? linkedBefore)}
        </span>
      </p>
    );
  }

  if (changes.length === 0) return null;

  const render = (value: unknown) => {
    if (value === null || value === undefined || value === "")
      return "Unassigned";
    const text = String(value);
    return (names.get(text) ?? text).replace(/_/g, " ").slice(0, 60);
  };

  return (
    <ul className="mt-1.5 space-y-1">
      {changes.map((change) => (
        <li key={change.key} className="text-body-sm text-text-secondary">
          <span className="text-text-subtle">{FIELD_LABEL[change.key]}:</span>{" "}
          <span className="line-through decoration-text-faint">
            {render(change.from)}
          </span>
          <Icon
            name="arrowr"
            className="mx-1 inline size-3 text-text-faint"
            aria-hidden
          />
          <span className="font-semibold text-text-primary">
            {render(change.to)}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Why a control answers a criterion, and how much of it: the shipped mapping's own words. */
function MappingNote({
  mapping,
  onOpen,
}: {
  mapping: CriterionMapping | undefined;
  onOpen: () => void;
}) {
  if (!mapping) return null;
  const label =
    mapping.coverage === "full"
      ? "Primary route"
      : mapping.coverage === "partial"
        ? "Supports"
        : "Added by your workspace";
  return (
    <div className="mt-2.5 rounded-md bg-surface-sunken px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="neutral">{label}</Badge>
        <button
          type="button"
          onClick={onOpen}
          className="text-body-sm font-semibold text-action-accent hover:underline"
        >
          See how this criterion is met
        </button>
      </div>
      <p className="mt-1.5 text-body-sm text-text-secondary">
        {mapping.rationale ??
          "Your workspace linked this control to the criterion. No reason is recorded."}
      </p>
    </div>
  );
}

type TabId = "overview" | "evidence" | "tests" | "requirements" | "linked" | "history";

export function ControlDetailPage() {
  const { controlId = "" } = useParams();
  const { principal } = useAuth();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));
  const canReadAudit = Boolean(principal?.permissions.includes("audit:read"));
  const [tab, setTab] = useState<TabId>("overview");
  const linksQuery = useLinkedRecords("control", controlId);
  // Same query key as the Checks tab, so the rail and the tab share one fetch.
  const automation = useAutomation(controlId).data;
  const [editing, setEditing] = useState(false);
  const [linking, setLinking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [chainFor, setChainFor] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const controlQuery = useQuery({
    queryKey: ["control", controlId],
    queryFn: () => controlsApi.get(controlId),
    enabled: controlId.length > 0,
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence", "control", controlId],
    queryFn: () => evidenceApi.list({ control_id: controlId }),
    enabled: controlId.length > 0,
  });

  // Assigning an owner is the most common edit on this screen, so it happens in
  // place rather than through the edit dialog. `clear_owner` wins over
  // `owner_membership_id` server-side, so unassigning sends the flag alone.
  const ownerMutation = useMutation({
    mutationFn: (membershipId: string | null) =>
      controlsApi.update(
        controlId,
        membershipId === null
          ? { clear_owner: true }
          : { owner_membership_id: membershipId },
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["control", controlId] }),
        queryClient.invalidateQueries({ queryKey: ["controls"] }),
      ]);
      toast({ title: "Owner updated", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });
  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
  });
  const allControlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
  });
  // The audit trail, scoped to this control. Immutable by construction — the
  // table is append-only, so this is the record, not a reconstruction.
  const historyQuery = useQuery({
    queryKey: ["audit", "control", controlId],
    queryFn: () =>
      auditApi.list(undefined, false, { type: "control", id: controlId }),
    enabled: controlId.length > 0 && canReadAudit,
  });

  const control = controlQuery.data;
  const evidence = useMemo(
    () => evidenceQuery.data ?? [],
    [evidenceQuery.data],
  );

  const framework = frameworksQuery.data?.[0];
  const frameworkVersionId = framework?.versions.find((v) => v.is_current)?.id;

  const requirementsQuery = useQuery({
    queryKey: ["requirements", framework?.id],
    queryFn: () =>
      complianceApi.listRequirements(framework!.id, frameworkVersionId),
    enabled: Boolean(framework?.id),
  });

  // The criteria this control satisfies, with their full text — requirement_keys
  // look like "SOC2:CC6.2", and the criterion list is keyed on the bare code.
  const criteria = useMemo(() => {
    const byCode = new Map(
      (requirementsQuery.data ?? []).map((requirement) => [
        requirement.code,
        requirement,
      ]),
    );
    return (control?.requirement_keys ?? [])
      .map((key) => byCode.get(key.replace(/^[^:]+:/, "")))
      .filter((requirement): requirement is NonNullable<typeof requirement> =>
        Boolean(requirement),
      );
  }, [control?.requirement_keys, requirementsQuery.data]);

  // Related = other live controls sharing at least one criterion. That is the
  // relationship an auditor actually traces, and it needs no extra table.
  const related = useMemo(() => {
    if (!control) return [] as Control[];
    const mine = new Set(control.requirement_keys);
    return (allControlsQuery.data ?? [])
      .filter(
        (candidate) =>
          candidate.id !== control.id &&
          candidate.requirement_keys.some((key) => mine.has(key)),
      )
      .slice(0, 12);
  }, [control, allControlsQuery.data]);

  const history = useMemo(
    () => historyQuery.data?.items ?? [],
    [historyQuery.data],
  );
  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: tab === "history",
  });
  const memberNames = useMemo(
    () =>
      new Map(
        (membersQuery.data ?? []).map((member) => [
          member.membership_id,
          member.full_name,
        ]),
      ),
    [membersQuery.data],
  );
  const staleCount = evidence.filter(
    (item) => item.freshness === "stale",
  ).length;

  if (controlQuery.isError) {
    const failure = describeError(controlQuery.error, "control");
    return (
      <div className="w-full">
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          // A deleted control or a permission gap will not resolve on a retry.
          onRetry={
            failure.retryable ? () => void controlQuery.refetch() : undefined
          }
        />
      </div>
    );
  }

  if (controlQuery.isLoading || !control) {
    return (
      <div className="w-full space-y-4">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-10 w-[28rem]" />
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <Skeleton className="h-80 w-full rounded-lg" />
          <Skeleton className="h-60 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  const statusFamily = STATUS_FAMILY[control.status] ?? "neutral";
  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "evidence", label: "Evidence", count: evidence.length },
    { id: "tests", label: "Checks" },
    { id: "requirements", label: "Requirements", count: criteria.length },
    { id: "linked", label: "Linked records", count: linksQuery.data?.records.length },
    { id: "history", label: "History", count: history.length },
  ];

  return (
    <div className="w-full">
      <DetailHeader
        icon="controls"
        backTo="/controls"
        backLabel="Back to controls"
        title={control.name}
        chips={
          <>
            <CodeChip code={control.code} />
            <StatusPill
              status={statusFamily}
              label={STATUS_LABEL[control.status] ?? control.status}
            />
            {control.disabled_at ? (
              <Badge variant="neutral">Disabled</Badge>
            ) : null}
            {control.origin === "custom" ? (
              <Badge variant="role">Custom</Badge>
            ) : null}
          </>
        }
        meta={
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            {/* Framework controls carry no Preventive/Detective classification,
                so the chip is absent rather than empty. */}
            {control.control_type ? (
              <span
                className="inline-flex items-center gap-1.5"
                title="Design"
              >
                <span className="size-1.5 rounded-full bg-action-accent" />
                {control.control_type}
              </span>
            ) : null}
            {control.control_sub_type ? (
              <span
                className="inline-flex items-center gap-1.5"
                title="Automation"
              >
                <Icon
                  name="activity"
                  className="size-3.5 text-text-subtle"
                  aria-hidden
                />
                {control.control_sub_type}
              </span>
            ) : null}
            <span className="inline-flex items-center gap-1.5">
              <Icon
                name="users"
                className="size-3.5 text-text-subtle"
                aria-hidden
              />
              {control.owner_name ?? "Unassigned"}
            </span>
            <Badge variant="neutral">{control.category}</Badge>
            {control.sub_category ? (
              <Badge variant="neutral">{control.sub_category}</Badge>
            ) : null}
          </div>
        }
        actions={
          <>
            {canManage ? (
              <Button variant="secondary" onClick={() => setEditing(true)}>
                <Icon name="gear" className="size-4" />
                Edit
              </Button>
            ) : null}
            <AutomationHeaderButton
              controlId={controlId}
              onOpen={() => setTab("tests")}
            />
          </>
        }
      />

      <TabStrip
        label="Control sections"
        items={tabs}
        value={tab}
        onSelect={(id) => setTab(id as TabId)}
        className="mb-5 mt-5"
        inline
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-4">
          {tab === "overview" ? (
            <>
              <Panel title="Control statement">
                <p className="text-body-md leading-relaxed text-text-secondary">
                  {control.description}
                </p>
                {control.implementation_guidance ? (
                  <>
                    <h3 className="mb-2 mt-5 font-display text-title-sm text-text-primary">
                      Implementation guidance
                    </h3>
                    <Guidance text={control.implementation_guidance} />
                  </>
                ) : null}
              </Panel>

              {control.disabled_at ? (
                <Panel title="Disabled">
                  <p className="text-body-md text-text-secondary">
                    {control.disabled_reason}
                  </p>
                  <p className="mt-2 text-caption text-text-subtle">
                    Retired, not deleted. The justification is on the audit
                    trail.
                  </p>
                </Panel>
              ) : null}

              <AutomationSummary
                controlId={controlId}
                onOpen={() => setTab("tests")}
              />
            </>
          ) : null}

          {tab === "evidence" || tab === "overview" ? (
            <Panel
              title={tab === "overview" ? "Linked evidence" : "Evidence"}
              action={
                canManage ? (
                  <span className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setLinking(true)}
                    >
                      Link existing
                    </Button>
                    <Button size="sm" onClick={() => setUploading(true)}>
                      <Icon name="plus" className="size-4" />
                      Add evidence
                    </Button>
                  </span>
                ) : (
                  <Link
                    to="/evidence"
                    className="text-body-sm font-semibold text-text-link"
                  >
                    Evidence library →
                  </Link>
                )
              }
            >
              {evidenceQuery.isLoading ? (
                <Skeleton className="h-24 w-full rounded-md" />
              ) : evidenceQuery.isError ? (
                // "No evidence linked yet" on a failed read would be a
                // fabricated compliance finding about this control.
                <p className="text-body-sm text-status-danger-text">
                  {describeError(evidenceQuery.error, "evidence list").message}
                </p>
              ) : evidence.length === 0 ? (
                <EmptyState
                  icon="doc"
                  title="No evidence linked yet"
                  description="A control with no evidence cannot be shown to operate. Attach a file or link from the evidence library."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {(tab === "overview" ? evidence.slice(0, 6) : evidence).map(
                    (item: Evidence) => (
                      <li
                        key={item.id}
                        className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0"
                      >
                        <Icon
                          name={item.kind === "file" ? "doc" : "globe"}
                          className="size-4 shrink-0 text-text-subtle"
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-body-md text-text-primary">
                            {item.title}
                          </span>
                          <span className="block truncate text-caption text-text-subtle">
                            {item.source_label ??
                              item.evidence_type.replace(/_/g, " ")}
                          </span>
                        </span>
                        <StatusPill
                          kind="inline"
                          status={FRESHNESS[item.freshness].family}
                          label={FRESHNESS[item.freshness].label}
                        />
                      </li>
                    ),
                  )}
                </ul>
              )}
              {tab === "overview" && evidence.length > 6 ? (
                <button
                  type="button"
                  onClick={() => setTab("evidence")}
                  className="mt-3 text-body-sm font-semibold text-text-link"
                >
                  View all {evidence.length} items
                </button>
              ) : null}
            </Panel>
          ) : null}

          {tab === "tests" ? (
            <ChecksPanel
              controlId={controlId}
              onOpenEvidence={() => setTab("evidence")}
            />
          ) : null}

          {tab === "linked" ? <LinkedRecordsPanel anchorType="control" anchorId={controlId} /> : null}

          {tab === "history" ? (
            <Panel title="History">
              {!canReadAudit ? (
                <EmptyState
                  icon="audit"
                  title="You cannot view the audit trail"
                  description="Viewing history needs the audit:read permission. An Admin can grant it."
                />
              ) : historyQuery.isLoading ? (
                <Skeleton className="h-32 w-full rounded-md" />
              ) : historyQuery.isError ? (
                <p className="text-body-sm text-status-danger-text">
                  {describeError(historyQuery.error, "audit trail").message}
                </p>
              ) : history.length === 0 ? (
                <EmptyState
                  icon="audit"
                  title="No changes recorded yet"
                  description="Every edit to this control is written to the audit trail as it happens."
                />
              ) : (
                <ol className="relative space-y-4 border-l border-border pl-5">
                  {history.map((entry) => (
                    <li key={entry.id} className="relative">
                      <span className="absolute -left-[1.6rem] top-1.5 size-2 rounded-full bg-action-accent" />
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="text-body-md font-semibold text-text-primary">
                          {entry.actor_label || "System"}
                        </span>
                        <span className="text-body-sm text-text-secondary">
                          {entry.action === "create"
                            ? "created this control"
                            : entry.after?.evidence_linked
                              ? "attached evidence"
                              : entry.before?.evidence_linked
                                ? "removed evidence"
                                : "updated this control"}
                        </span>
                        <span className="ml-auto tabular text-caption text-text-subtle">
                          {new Date(entry.occurred_at).toLocaleString()}
                        </span>
                      </div>
                      {/* What actually changed — the before/after snapshot the
                          audit row carries, reduced to the fields that moved. */}
                      <ChangeSummary
                        before={entry.before}
                        after={entry.after}
                        names={memberNames}
                      />
                    </li>
                  ))}
                </ol>
              )}
            </Panel>
          ) : null}

          {tab === "requirements" ? (
            <Panel
              title={`${framework?.name ?? "Framework"} requirements`}
              action={
                <span className="text-caption text-text-subtle">
                  The criterion text this control is written against
                </span>
              }
            >
              {/* The criterion text comes from the framework, so a failure
                  there must not read as "this control maps to nothing" —
                  that is a coverage claim, not a loading state. */}
              {requirementsQuery.isError || frameworksQuery.isError ? (
                <p className="text-body-sm text-status-danger-text">
                  {
                    describeError(
                      requirementsQuery.error ?? frameworksQuery.error,
                      "criteria list",
                    ).message
                  }
                </p>
              ) : criteria.length === 0 ? (
                <EmptyState
                  icon="shield"
                  title="Not mapped to any criterion"
                  description="A control satisfying no criterion contributes nothing to coverage."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {criteria.map((requirement) => (
                    <li
                      key={requirement.id}
                      className="py-4 first:pt-0 last:pb-0"
                    >
                      <div className="mb-1.5 flex flex-wrap items-center gap-2">
                        <CodeChip code={requirement.code} />
                        <Badge variant="neutral">
                          {requirement.trust_services_category}
                        </Badge>
                        {requirement.is_always_in_scope ? (
                          <span className="text-caption text-text-subtle">
                            always in scope
                          </span>
                        ) : null}
                      </div>
                      <p className="text-body-md font-semibold text-text-primary">
                        {requirement.name}
                      </p>
                      {/* The framework's own words. An auditor reads this, so it
                          is quoted verbatim rather than paraphrased. */}
                      {requirement.description ? (
                        <p className="mt-1 border-l-2 border-border pl-3 text-body-sm leading-relaxed text-text-secondary">
                          {requirement.description}
                        </p>
                      ) : null}
                      <MappingNote
                        mapping={automation?.mappings.find(
                          (m) => m.code === requirement.code,
                        )}
                        onOpen={() => setChainFor(requirement.id)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          ) : null}
        </div>

        {/* ── Right rail ─────────────────────────────────────────────────── */}
        <aside className="space-y-4">
          <section className="rounded-lg border border-border bg-surface-primary p-5">
            <h2 className="mb-1 font-display text-title-md text-text-primary">
              Status
            </h2>
            <Fact
              label="Implementation"
              value={
                <StatusPill
                  kind="inline"
                  status={statusFamily}
                  label={STATUS_LABEL[control.status] ?? control.status}
                />
              }
            />
            <Fact
              label="Owner"
              value={
                canManage && !control.disabled_at ? (
                  <div className="w-48">
                    <OwnerSelect
                      value={control.owner_membership_id}
                      valueLabel={control.owner_name}
                      onChange={(membershipId) =>
                        ownerMutation.mutate(membershipId)
                      }
                      disabled={ownerMutation.isPending}
                    />
                  </div>
                ) : (
                  (control.owner_name ?? "Unassigned")
                )
              }
            />
            <Fact label="Type" value={control.category} />
            <Fact
              label="Sub-type"
              value={control.sub_category || "Not set"}
              muted={!control.sub_category}
            />
            {control.control_type ? (
              <Fact label="Design" value={control.control_type} />
            ) : null}
            <Fact
              label="Automation"
              value={control.control_sub_type ?? "Not set"}
              muted={!control.control_sub_type}
            />
            <Fact
              label="Source"
              value={control.origin === "custom" ? "Custom" : "Template"}
            />
            <Fact
              label="Evidence"
              value={
                staleCount > 0 ? (
                  <span className="text-status-warning-text">
                    {evidence.length} · {staleCount} stale
                  </span>
                ) : (
                  `${evidence.length} linked`
                )
              }
            />
            {/* Measured by the connected systems; muted while nothing runs. */}
            <Fact
              label="Last tested"
              value={
                automation?.last_run_at ? ago(automation.last_run_at) : "Not tested"
              }
              muted={!automation?.last_run_at}
            />
            <Fact
              label="Test frequency"
              value={automation?.tests_running ? "Daily" : "Manual"}
              muted={!automation?.tests_running}
            />
          </section>

          <section className="rounded-lg border border-border bg-surface-primary p-5">
            <h2 className="mb-3 font-display text-title-md text-text-primary">
              Framework mappings
            </h2>
            {criteria.length === 0 ? (
              <p className="text-body-sm text-status-warning-text">
                Not mapped to any criterion
              </p>
            ) : (
              <ul className="space-y-2.5">
                {criteria.map((requirement) => (
                  <li key={requirement.id} className="flex items-start gap-2.5">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-action-accent-tint font-display text-caption font-bold text-text-link">
                      {framework?.code ?? "SOC"}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-body-sm font-semibold text-text-primary">
                        {framework?.name ?? "SOC 2"}
                      </span>
                      <span className="block truncate text-caption text-text-subtle">
                        {requirement.code} · {requirement.name}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 border-t border-border pt-3 text-caption text-text-subtle">
              ISO 27001 and HIPAA mappings arrive with those content packs.
            </p>
          </section>

          {related.length > 0 ? (
            <section className="rounded-lg border border-border bg-surface-primary p-5">
              <h2 className="mb-1 font-display text-title-md text-text-primary">
                Related controls
              </h2>
              <p className="mb-3 text-caption text-text-subtle">
                Also satisfying a criterion this control covers.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {related.map((item) => (
                  <Link
                    key={item.id}
                    to={`/controls/${item.id}`}
                    title={item.name}
                  >
                    <CodeChip
                      code={item.code}
                      className="transition-colors duration-80 ease-state hover:bg-action-accent hover:text-text-inverse"
                    />
                  </Link>
                ))}
              </div>
            </section>
          ) : null}
        </aside>
      </div>

      <RequirementChainDialog
        requirementId={chainFor}
        onClose={() => setChainFor(null)}
      />
      <EditControlDialog
        control={control}
        open={editing}
        onOpenChange={setEditing}
        onSaved={async () => {
          await queryClient.invalidateQueries({
            queryKey: ["control", controlId],
          });
          await queryClient.invalidateQueries({ queryKey: ["controls"] });
          await queryClient.invalidateQueries({
            queryKey: ["audit", "control", controlId],
          });
          toast({ title: "Control updated", tone: "success" });
        }}
      />

      {/* The library's own dialog, with this control pre-attached. */}
      <AddEvidenceDialog
        open={uploading}
        onOpenChange={setUploading}
        presetControlIds={[controlId]}
      />

      <AttachEvidenceDialog
        controlId={controlId}
        open={linking}
        onOpenChange={setLinking}
        onDone={async () => {
          await queryClient.invalidateQueries({ queryKey: ["evidence"] });
          await queryClient.invalidateQueries({
            queryKey: ["audit", "control", controlId],
          });
          toast({ title: "Evidence attached", tone: "success" });
        }}
      />
    </div>
  );
}
