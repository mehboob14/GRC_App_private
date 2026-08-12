import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Icon, Skeleton } from "@/components/ui";
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

function StepMark({ status }: { status: StepStatus }) {
  if (status.kind === "done") {
    return (
      <span className="flex size-[18px] shrink-0 items-center justify-center rounded-full bg-pass text-text-inverse">
        <Icon name="check" className="size-3" strokeWidth={2.5} />
      </span>
    );
  }
  if (status.kind === "loading") {
    return <Skeleton className="size-[18px] shrink-0 rounded-full" />;
  }
  if (status.kind === "error") {
    return (
      <span className="flex size-[18px] shrink-0 items-center justify-center text-fail-fg">
        <Icon name="alert" className="size-4" />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "size-[18px] shrink-0 rounded-full border-2",
        status.kind === "todo" ? "border-accent" : "border-border-strong",
      )}
    />
  );
}

function StepRow({ step }: { step: Step }) {
  const muted = step.status.kind === "unavailable";
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-bg-elevated px-[18px] py-[14px]">
      <StepMark status={step.status} />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-body-lg font-semibold",
            muted ? "text-text-muted" : "text-text",
          )}
        >
          {step.title}
        </p>
        <p className="mt-0.5 text-body-sm text-text-faint">{step.why}</p>
        {step.status.kind === "error" ? (
          <p className="mt-1 text-body-sm text-fail-fg" role="alert">
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
          <p className="mt-1 text-body-sm text-text-faint">
            {step.status.note}
          </p>
        ) : null}
      </div>
      {step.status.kind === "done" ? (
        <span className="shrink-0 text-body-sm font-semibold text-pass-fg">
          Done
        </span>
      ) : step.cta && step.status.kind === "todo" ? (
        <Button asChild size="sm" className="ml-2 h-8 shrink-0 px-3">
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
      cta: { label: "View policy", to: "/settings/security" },
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
      cta: { label: "Create a group", to: "/settings/groups" },
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

  return (
    <div className="mx-auto max-w-[840px]">
      <p className="type-overline mb-2">Overview</p>
      <h1 className="font-display text-heading-xl text-text">Quick start</h1>
      <p className="mt-2 text-body-lg text-text-muted">
        First-run checklist for your workspace — {doneCount} of{" "}
        {completable.length} setup steps complete.
      </p>

      <div className="mt-6 space-y-[10px]">
        {steps.map((step) => (
          <StepRow key={step.id} step={step} />
        ))}
      </div>
    </div>
  );
}
