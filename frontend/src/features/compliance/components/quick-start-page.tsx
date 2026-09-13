import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button, ErrorState, Icon, PageHeader, Skeleton } from "@/components/ui";
import {
  controlsApi,
  engagementApi,
  iamApi,
  tenantApi,
} from "@/lib/api/endpoints";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";

/**
 * Get Started — grouped setup checklist.
 *
 * Every task here is decided by a real API response, and that constraint is the
 * design. A checklist is a claim about the workspace; in a compliance product a
 * claim that cannot be traced to data is worse than no claim. So:
 *
 *   * a task exists only if some endpoint can answer "is this done?" today;
 *   * work the platform does not ship yet (integrations, policies) is not a row
 *     with a permanent 0 — it sits below the checklist, uncounted;
 *   * a field the server pre-fills cannot prove a user did anything. The
 *     company-profile check reads website/headquarters/company_size, never
 *     legal_name: signup seeds legal_name from the company name, so it is
 *     non-null for a tenant that has never opened the form.
 */

type Task = {
  id: string;
  title: string;
  detail: string;
  done: boolean;
  to: string;
  cta: string;
};

type Section = {
  id: string;
  title: string;
  purpose: string;
  tasks: Task[];
};

function TaskRow({ task }: { task: Task }) {
  return (
    <div className="flex items-start gap-3 border-t border-border px-5 py-3.5 first:border-t-0">
      {task.done ? (
        <span className="mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded-full bg-status-success-base text-text-inverse">
          <Icon name="check" className="size-[11px]" />
        </span>
      ) : (
        <span className="mt-0.5 size-[18px] shrink-0 rounded-full border-1.5 border-border-strong" />
      )}
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-body-md font-semibold",
            task.done ? "text-text-subtle" : "text-text-primary",
          )}
        >
          {task.title}
        </span>
        <span className="mt-0.5 block text-body-sm text-text-secondary">
          {task.detail}
        </span>
      </span>
      {!task.done ? (
        <Button asChild variant="secondary" size="sm" className="shrink-0">
          <Link to={task.to}>{task.cta}</Link>
        </Button>
      ) : null}
    </div>
  );
}

function ProgressTrack({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <span
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={done}
      aria-label={`${done} of ${total} complete`}
      className="block h-[6px] w-full overflow-hidden rounded-full bg-surface-sunken"
    >
      <span
        className={cn(
          "block h-full rounded-full transition-[width] duration-300 ease-state",
          done === total ? "bg-status-success-base" : "bg-action-accent",
        )}
        style={{ width: `${pct}%` }}
      />
    </span>
  );
}

function SectionCard({
  section,
  open,
  onToggle,
}: {
  section: Section;
  open: boolean;
  onToggle: () => void;
}) {
  const done = section.tasks.filter((task) => task.done).length;
  const total = section.tasks.length;
  const panelId = `quickstart-${section.id}`;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface-primary">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
        className="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-surface-hover"
      >
        <span className="min-w-0 flex-1">
          <span className="block font-display text-title-md text-text-primary">
            {section.title}
          </span>
          <span className="mt-0.5 block text-body-sm text-text-secondary">
            {section.purpose}
          </span>
          <span className="mt-3 flex items-center gap-3">
            <ProgressTrack done={done} total={total} />
            <span className="shrink-0 text-caption tabular text-text-subtle">
              {done} of {total} completed
            </span>
          </span>
        </span>
        <Icon
          name="chevr"
          aria-hidden
          className={cn(
            "mt-1 size-4 shrink-0 text-text-subtle transition-transform duration-150",
            open && "rotate-90",
          )}
        />
      </button>
      {open ? (
        <div id={panelId} className="border-t border-border">
          {section.tasks.map((task) => (
            <TaskRow key={task.id} task={task} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function QuickStartPage() {
  const { principal } = useAuth();
  const tenantId = principal?.tenant_id;

  const [profileQ, securityQ, membersQ, engagementQ, controlsQ] = useQueries({
    queries: [
      {
        queryKey: ["company-profile", tenantId],
        queryFn: tenantApi.getCompanyProfile,
      },
      {
        queryKey: ["tenant-security", tenantId],
        queryFn: tenantApi.getSecurity,
      },
      { queryKey: ["members", tenantId], queryFn: () => iamApi.listMembers() },
      {
        queryKey: ["engagement", tenantId],
        queryFn: () => engagementApi.get(),
      },
      { queryKey: ["controls", tenantId], queryFn: () => controlsApi.list({}) },
    ],
  });

  const queries = [profileQ, securityQ, membersQ, engagementQ, controlsQ];
  const loading = queries.some((query) => query.isLoading);
  // Every tick here is a claim about the workspace. If any of the five reads
  // failed, the unticked rows would be a claim about the request instead, so
  // the checklist is withheld rather than shown wrong.
  const failed = queries.find((query) => query.isError);

  const profile = profileQ.data;
  const security = securityQ.data;
  const members = membersQ.data;
  const engagement = engagementQ.data;
  const controls = controlsQ.data;
  const mfaEnabled = principal?.user.mfa_enabled ?? false;

  const sections = useMemo<Section[]>(() => {
    const controlList = controls ?? [];
    const memberList = members ?? [];

    const scopeTasks: Task[] = [
      {
        id: "engagement",
        title: "Set up your audit engagement",
        detail:
          "Choose the framework and whether you are pursuing Type I or Type II.",
        done: Boolean(engagement),
        to: "/frameworks/scope",
        cta: "Set up",
      },
      {
        id: "categories",
        title: "Choose your Trust Services Criteria",
        detail:
          "Security is always in scope. Add Availability, Confidentiality, Processing Integrity or Privacy if you are claiming them.",
        done: (engagement?.categories_in_scope.length ?? 0) > 0,
        to: "/frameworks/scope",
        cta: "Choose",
      },
    ];
    // The observation window is a Type II concept. Showing it against a Type I
    // engagement would be a row that can never legitimately complete.
    if (engagement?.audit_type === "type_2") {
      scopeTasks.push({
        id: "window",
        title: "Set your observation window",
        detail: "The period your auditor tests evidence across.",
        done: Boolean(engagement.window_start && engagement.window_end),
        to: "/frameworks/scope",
        cta: "Set dates",
      });
    }

    return [
      {
        id: "workspace",
        title: "Set up your workspace",
        purpose: "The company details later steps depend on.",
        tasks: [
          {
            id: "profile",
            title: "Complete your company profile",
            detail: "Website, headquarters and company size.",
            done: Boolean(
              profile?.website &&
              profile?.headquarters &&
              profile?.company_size,
            ),
            to: "/settings/organization/profile",
            cta: "Complete",
          },
        ],
      },
      {
        id: "access",
        title: "Secure access to your workspace",
        purpose: "Who can get in, and what they have to prove to do it.",
        tasks: [
          {
            id: "own-mfa",
            title: "Turn on two-factor for your account",
            detail: "An authenticator app on your own sign-in.",
            done: mfaEnabled,
            to: "/settings/security/mfa",
            cta: "Turn on",
          },
          {
            id: "admin-mfa",
            title: "Require two-factor for admins",
            detail:
              "Every Admin-role member must enrol before they can sign in.",
            done: security?.require_admin_mfa ?? false,
            to: "/settings/security/mfa",
            cta: "Require",
          },
          {
            id: "invite",
            title: "Invite your team",
            detail:
              "Add the people who will own controls and collect evidence.",
            // Signup creates exactly one membership, so more than one proves an
            // invite was actually issued.
            done:
              memberList.filter((member) => member.status !== "disabled")
                .length > 1,
            to: "/settings/access/people",
            cta: "Invite",
          },
        ],
      },
      {
        id: "scope",
        title: "Scope your audit",
        purpose: "What you are audited against, and over what period.",
        tasks: scopeTasks,
      },
      {
        id: "controls",
        title: "Work your controls",
        purpose: "Your SOC 2 control library, owned and moving.",
        tasks: [
          {
            id: "owners",
            title: "Assign control owners",
            detail:
              "Adopted controls start unassigned. Give each one a person.",
            done: controlList.some(
              (control) => control.owner_membership_id !== null,
            ),
            to: "/controls",
            cta: "Assign",
          },
          {
            id: "progress",
            title: "Start working your controls",
            detail:
              "Move a control off Not started once you are implementing it.",
            done: controlList.some(
              (control) => control.status !== "not_started",
            ),
            to: "/controls",
            cta: "Open controls",
          },
        ],
      },
    ];
  }, [profile, security, members, engagement, controls, mfaEnabled]);

  const allTasks = sections.flatMap((section) => section.tasks);
  const doneCount = allTasks.filter((task) => task.done).length;

  // Open the first section with work left: opening everything is a wall,
  // opening nothing hides the next action. `""` means the user closed it.
  const firstIncomplete = sections.find((section) =>
    section.tasks.some((task) => !task.done),
  );
  const [openId, setOpenId] = useState<string | null>(null);
  const effectiveOpen = openId ?? firstIncomplete?.id ?? null;

  if (loading) {
    return (
      <div className="mx-auto w-4/5 space-y-3">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-28 w-full rounded-lg" />
        <Skeleton className="h-28 w-full rounded-lg" />
        <Skeleton className="h-28 w-full rounded-lg" />
      </div>
    );
  }

  if (failed) {
    const failure = describeError(failed.error, "checklist");
    return (
      <div className="mx-auto w-4/5">
        <PageHeader title="Get started" />
        <div className="mt-5">
          <ErrorState
            title={failure.title}
            description={failure.message}
            referenceId={failure.referenceId}
            onRetry={
              failure.retryable
                ? () => queries.forEach((query) => void query.refetch())
                : undefined
            }
          />
        </div>
      </div>
    );
  }

  return (
    // The checklist reads as a single column, so it is held to ~80% of the
    // content area rather than stretching the full width.
    <div className="mx-auto w-4/5">
      <PageHeader title="Get started" />

      {/* The progress row is the only place the numbers live now: the subtitle
          that restated them is gone. */}
      <div className="mt-5 flex items-center gap-3">
        <ProgressTrack done={doneCount} total={allTasks.length} />
        <span className="shrink-0 text-label-sm tabular text-text-secondary">
          {doneCount}/{allTasks.length}
        </span>
      </div>

      <div className="mt-6 space-y-3">
        {sections.map((section) => (
          <SectionCard
            key={section.id}
            section={section}
            open={effectiveOpen === section.id}
            onToggle={() =>
              setOpenId(effectiveOpen === section.id ? "" : section.id)
            }
          />
        ))}
      </div>

      {/* Deliberately outside the checklist and without a counter. There is no
          connectors API — `modules/connectors/` is an empty package and every
          provider renders "Not connected" from a static catalogue — so nothing
          here can report done. A counted row would sit at 0 forever and read as
          the workspace failing a step it cannot take. */}
      <div className="mt-3 rounded-lg border border-border bg-surface-primary px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-display text-title-md text-text-primary">
              Establish continuous compliance for your frameworks
            </p>
            <p className="mt-0.5 text-body-sm text-text-secondary">
              Connect the systems your controls run on.
            </p>
          </div>
          <Button asChild variant="secondary" className="shrink-0">
            <Link to="/connectors">View connections</Link>
          </Button>
        </div>
      </div>

      <p className="mt-4 text-body-sm text-text-subtle">
        Connecting systems arrives in a later phase, so it is not counted above.
      </p>
    </div>
  );
}
