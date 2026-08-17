import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Icon, Skeleton, StatusPill } from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";

type StepStatus =
  | { kind: "done" }
  | { kind: "todo" }
  | { kind: "loading" }
  | { kind: "error"; message: string; retry: () => void }
  | { kind: "unavailable"; note: string };

type Step = {
  id: string;
  title: string;
  why: string;
  status: StepStatus;
  cta?: { label: string; to: string };
};

function messageFrom(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

/** 22px circle: solid success check when done, numbered outline otherwise. */
function StepMark({
  status,
  index,
  isNext,
}: {
  status: StepStatus;
  index: number;
  isNext: boolean;
}) {
  if (status.kind === "done") {
    return (
      <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-status-success-base text-text-inverse">
        <Icon name="check" className="size-[13px]" strokeWidth={2.5} />
      </span>
    );
  }
  if (status.kind === "loading") {
    return <Skeleton className="size-[22px] shrink-0 rounded-full" />;
  }
  if (status.kind === "error") {
    return (
      <span className="flex size-[22px] shrink-0 items-center justify-center text-status-danger-text">
        <Icon name="alert" className="size-4" />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "flex size-[22px] shrink-0 items-center justify-center rounded-full border-1.5 font-sans text-caption font-bold tabular",
        isNext
          ? "border-action-accent text-action-accent"
          : "border-border-strong text-text-subtle",
      )}
    >
      {index}
    </span>
  );
}

function StepRow({
  step,
  index,
  isNext,
}: {
  step: Step;
  index: number;
  isNext: boolean;
}) {
  const muted = step.status.kind === "unavailable";
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-primary px-4 py-3">
      <StepMark status={step.status} index={index} isNext={isNext} />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-body-lg font-semibold",
            muted ? "text-text-secondary" : "text-text-primary",
          )}
        >
          {step.title}
        </p>
        <p className="mt-0.5 text-body-sm text-text-subtle">{step.why}</p>
        {step.status.kind === "error" ? (
          <p className="mt-1 text-body-sm text-status-danger-text" role="alert">
            {step.status.message}{" "}
            <button
              type="button"
              className="font-semibold underline underline-offset-2"
              onClick={step.status.retry}
            >
              Retry
            </button>
          </p>
        ) : null}
        {step.status.kind === "unavailable" ? (
          <p className="mt-1 text-body-sm text-text-subtle">
            {step.status.note}
          </p>
        ) : null}
      </div>
      {step.status.kind === "done" ? (
        <StatusPill status="success" label="Complete" className="shrink-0" />
      ) : step.cta && step.status.kind === "todo" ? (
        // One primary on the page: the next incomplete step's CTA. Later
        // steps stay reachable as secondary actions.
        <Button
          asChild
          variant={isNext ? "primary" : "secondary"}
          size="sm"
          className="ml-2 shrink-0"
        >
          <Link to={step.cta.to}>{step.cta.label}</Link>
        </Button>
      ) : null}
    </div>
  );
}

/**
 * First-run checklist driven only by real Week 1 endpoints — no invented
 * numbers. Steps that need a permission the viewer lacks say so instead of
 * guessing.
 */
export function QuickStartPage() {
  const { principal } = useAuth();
  const tenantId = principal?.tenant_id;
  const canReadMembers = principal?.permissions.includes("members:read");
  const canReadGroups = principal?.permissions.includes("groups:read");
  const canReadRoles = principal?.permissions.includes("roles:read");
  const canReadAudit = principal?.permissions.includes("audit:read");

  const membersQuery = useQuery({
    queryKey: ["members", tenantId],
    queryFn: () => iamApi.listMembers(),
    enabled: Boolean(principal) && Boolean(canReadMembers),
  });
  const groupsQuery = useQuery({
    queryKey: ["groups", tenantId],
    queryFn: () => iamApi.listGroups(),
    enabled: Boolean(principal) && Boolean(canReadGroups),
  });
  const rolesQuery = useQuery({
    queryKey: ["roles", tenantId],
    queryFn: () => iamApi.listRoles(),
    enabled: Boolean(principal) && Boolean(canReadRoles),
  });

  // Prefer the live member row (fresher than the session snapshot); fall back
  // to the principal's own flag when members aren't readable.
  const selfMember = membersQuery.data?.find(
    (m) => m.membership_id === principal?.membership_id,
  );
  const mfaEnrolled =
    selfMember?.mfa_enabled ?? principal?.user.mfa_enabled ?? false;

  const inviteStatus: StepStatus = !canReadMembers
    ? {
        kind: "unavailable",
        note: "Needs the members:read permission — ask a workspace Admin.",
      }
    : membersQuery.isLoading
      ? { kind: "loading" }
      : membersQuery.isError
        ? {
            kind: "error",
            message: messageFrom(membersQuery.error, "Couldn't load members."),
            retry: () => void membersQuery.refetch(),
          }
        : (membersQuery.data?.length ?? 0) > 1
          ? { kind: "done" }
          : { kind: "todo" };

  const hasCustomGroupOrRole =
    (groupsQuery.data?.length ?? 0) > 0 ||
    (rolesQuery.data?.some((role) => !role.built_in) ?? false);

  const accessStatus: StepStatus =
    !canReadGroups && !canReadRoles
      ? {
          kind: "unavailable",
          note: "Needs the groups:read or roles:read permission — ask a workspace Admin.",
        }
      : hasCustomGroupOrRole
        ? { kind: "done" }
        : groupsQuery.isLoading || rolesQuery.isLoading
          ? { kind: "loading" }
          : groupsQuery.isError || rolesQuery.isError
            ? {
                kind: "error",
                message: messageFrom(
                  groupsQuery.error ?? rolesQuery.error,
                  "Couldn't load groups and roles.",
                ),
                retry: () => {
                  if (groupsQuery.isError) void groupsQuery.refetch();
                  if (rolesQuery.isError) void rolesQuery.refetch();
                },
              }
            : { kind: "todo" };

  const steps: Step[] = [
    {
      id: "workspace",
      title: "Workspace created",
      why: "Your isolated workspace exists — you're in it right now.",
      status: { kind: "done" },
    },
    {
      id: "mfa",
      title: "Enroll MFA",
      why: "Required for Admin roles, always — you'll be prompted at sign-in until it's on.",
      status: mfaEnrolled ? { kind: "done" } : { kind: "todo" },
      cta: { label: "View policy", to: "/settings/security/mfa" },
    },
    {
      id: "invite",
      title: "Invite your first teammate",
      why: "Compliance is shared work — hand each invitee their one-time accept link.",
      status: inviteStatus,
      cta: { label: "Invite", to: "/people" },
    },
    {
      id: "access",
      title: "Organise access",
      why: "Groups and custom roles keep permissions reviewable when the team grows.",
      status: accessStatus,
      cta: { label: "Create a group", to: "/settings/access/groups" },
    },
    {
      id: "audit",
      title: "Review your audit trail",
      why: "Every state change lands here append-only — it's what your auditor reads.",
      status: canReadAudit
        ? { kind: "todo" }
        : {
            kind: "unavailable",
            note: "Needs the audit:read permission — ask a workspace Admin.",
          },
      cta: { label: "Open audit log", to: "/audit-log" },
    },
  ];

  const completable = steps.filter((step) => step.id !== "audit");
  const doneCount = completable.filter(
    (step) => step.status.kind === "done",
  ).length;
  const nextStepId = steps.find((step) => step.status.kind === "todo")?.id;

  return (
    <div className="mx-auto max-w-[840px]">
      <p className="type-overline mb-2">Overview</p>
      <h1 className="font-display text-heading-lg text-text-primary">
        Quick start
      </h1>
      <p className="mt-2 text-body-lg text-text-secondary">
        First-run checklist for your workspace — every step reflects live
        workspace data.
      </p>

      {/* DS §6.4 progress pattern: 150×7 track + tabular value */}
      <div className="mt-5 flex items-center gap-3">
        <span className="font-display text-numeral-sm tabular text-text-primary">
          {doneCount}
          <span className="text-text-subtle">/{completable.length}</span>
        </span>
        <span
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={completable.length}
          aria-valuenow={doneCount}
          aria-label="Setup steps complete"
          className="h-[7px] w-[150px] overflow-hidden rounded-full border border-border bg-surface-sunken"
        >
          <span
            className="block h-full rounded-full bg-status-success-base"
            style={{ width: `${(doneCount / completable.length) * 100}%` }}
          />
        </span>
        <span className="text-label-sm text-text-secondary">
          setup steps complete
        </span>
      </div>

      <Link
        to="/settings/organization/profile"
        className="mt-6 flex items-center gap-3 rounded-lg border border-border bg-surface-primary px-4 py-3.5 transition-colors hover:border-action-accent hover:bg-action-accent-tint/40"
      >
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-action-accent-tint text-action-accent">
          <Icon name="box" className="size-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-body-md font-semibold text-text-primary">
            Complete your company profile
          </span>
          <span className="block text-body-sm text-text-subtle">
            Name, industry, website, description and policy URLs — feeds reports
            and evidence.
          </span>
        </span>
        <Icon name="arrowr" className="size-4 shrink-0 text-text-subtle" />
      </Link>

      <div className="mt-6 space-y-2">
        {steps.map((step, index) => (
          <StepRow
            key={step.id}
            step={step}
            index={index + 1}
            isNext={step.id === nextStepId}
          />
        ))}
      </div>
    </div>
  );
}
