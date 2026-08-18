import { Link } from "react-router-dom";
import { Button, Icon, StatusPill } from "@/components/ui";
import { IDENTITY_CONNECTORS_PATH } from "@/features/connectors/connector-catalogue";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";

/** `soon` is a step the platform does not ship yet: shown, never counted. */
type StepStatus = "done" | "todo" | "soon";

type Step = {
  id: string;
  title: string;
  why: string;
  status: StepStatus;
  cta?: { label: string; to: string };
};

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
  if (status === "done") {
    return (
      <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-status-success-base text-text-inverse">
        <Icon name="check" className="size-[13px]" strokeWidth={2.5} />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "flex size-[22px] shrink-0 items-center justify-center rounded-full border-1.5 font-sans text-caption font-bold tabular",
        status === "soon"
          ? "border-border text-text-faint"
          : isNext
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
  const soon = step.status === "soon";
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-border px-4 py-3",
        // Dashed on sunken is how this app already draws a not-yet-built row
        // (evidence detail's Risks/Assets/Policies placeholders).
        soon ? "border-dashed bg-surface-sunken" : "bg-surface-primary",
      )}
    >
      <StepMark status={step.status} index={index} isNext={isNext} />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-body-lg font-semibold",
            soon ? "text-text-secondary" : "text-text-primary",
          )}
        >
          {step.title}
        </p>
        <p className="mt-0.5 text-body-sm text-text-subtle">{step.why}</p>
      </div>
      {step.status === "done" ? (
        <StatusPill status="success" label="Complete" className="shrink-0" />
      ) : soon ? (
        // The app's existing quiet "Soon" tag (sidebar, settings tabs, evidence
        // detail). Longhand, not `.type-overline`: that utility resolves to
        // text-faint, which is decorative-only and too low-contrast for a label
        // that carries meaning.
        <span className="shrink-0 font-sans text-overline uppercase text-text-subtle">
          Soon
        </span>
      ) : step.cta ? (
        // One primary on the page: the next incomplete step's CTA. Later steps
        // stay reachable as secondary actions.
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
 * First-run checklist. Every live step reads real session state; steps the
 * platform does not ship yet are marked `soon` and stay out of the count, so
 * the progress figure never claims work the product cannot do.
 */
export function QuickStartPage() {
  const { principal } = useAuth();
  // Enrollment happens at sign-in (`/mfa/enroll`), never mid-session, so the
  // session principal is authoritative here and no members fetch is needed.
  const mfaEnrolled = principal?.user.mfa_enabled ?? false;

  const steps: Step[] = [
    {
      id: "workspace",
      title: "Workspace created",
      why: "Your isolated workspace is live.",
      status: "done",
    },
    {
      id: "mfa",
      title: "Enroll MFA",
      why: "Required for every Admin role.",
      status: mfaEnrolled ? "done" : "todo",
      cta: { label: "View policy", to: "/settings/security/mfa" },
    },
    {
      id: "identity",
      title: "Connect your identity provider",
      why: "Sync people and access from Okta, Entra ID or Google Workspace.",
      status: "todo",
      cta: { label: "Connect", to: IDENTITY_CONNECTORS_PATH },
    },
    {
      id: "frameworks",
      title: "Review frameworks and controls",
      why: "Check the SOC 2 control set against how you operate.",
      status: "soon",
    },
    {
      id: "policies",
      title: "Review policies",
      why: "Publish the policies your auditor asks for.",
      status: "soon",
    },
  ];

  const actionable = steps.filter((step) => step.status !== "soon");
  const doneCount = actionable.filter((step) => step.status === "done").length;
  const nextStepId = steps.find((step) => step.status === "todo")?.id;

  return (
    <div className="mx-auto max-w-[840px]">
      <p className="type-overline mb-2">Overview</p>
      <h1 className="font-display text-heading-lg text-text-primary">
        Quick start
      </h1>
      <p className="mt-2 text-body-lg text-text-secondary">
        First-run checklist for your workspace.
      </p>

      {/* DS §6.4 progress pattern: 150×7 track + tabular value */}
      <div className="mt-5 flex items-center gap-3">
        <span className="font-display text-numeral-sm tabular text-text-primary">
          {doneCount}
          <span className="text-text-subtle">/{actionable.length}</span>
        </span>
        <span
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={actionable.length}
          aria-valuenow={doneCount}
          aria-label="Setup steps complete"
          className="h-[7px] w-[150px] overflow-hidden rounded-full border border-border bg-surface-sunken"
        >
          <span
            className="block h-full rounded-full bg-status-success-base"
            style={{ width: `${(doneCount / actionable.length) * 100}%` }}
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
            Name, industry, website and policy URLs.
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
