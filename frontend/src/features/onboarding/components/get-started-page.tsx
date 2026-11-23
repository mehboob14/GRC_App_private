import { useState, type ReactNode } from "react";
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
  ErrorState,
  Icon,
  PageHeader,
  Skeleton,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { cn } from "@/lib/cn";
import { useEntryState } from "@/lib/nav/entry-state";
import {
  ONBOARDING_STATUS_KEY,
  onboardingApi,
  type FrameworkFigures,
  type OnboardingStatus,
  type OnboardingStep,
  type PlanMilestone,
  type StepPhase,
} from "../api";

/**
 * Get Started: the programme home for every framework the workspace runs.
 *
 * The server computes every state from records (`/onboarding/status`), so nothing
 * here ticks on a click. Steps shared by several frameworks appear once with a chip
 * per framework; steps for one framework sit in that framework's lane. A step the
 * caller's role cannot read says so in one line instead of failing the page.
 * Plan: docs/product/guided-onboarding/03-experience.md, section 4.
 */

const PHASE_LABEL: Record<StepPhase, string> = {
  describe: "Describe",
  organise: "Organise",
  assess: "Assess",
  build: "Build",
  operate: "Operate",
  check: "Check",
  audit: "Audit",
};

const SHORT_NAME: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

function shortName(code: string, frameworks: FrameworkFigures[] | null): string {
  return SHORT_NAME[code] ?? frameworks?.find((f) => f.code === code)?.name ?? code;
}

function formatDay(value: string | null): string | null {
  if (!value) return null;
  // A date with no time is a calendar day; parse it as local midnight, or a
  // timezone west of UTC shows the day before.
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function frameworkSummary(framework: FrameworkFigures): string {
  const parts: string[] = [];
  if (framework.scope_model === "categories") {
    if (!framework.scope_set || !framework.audit_type) {
      parts.push("No report type yet");
    } else if (framework.audit_type === "type_2") {
      const from = formatDay(framework.window_start);
      const to = formatDay(framework.window_end);
      parts.push(from && to ? `Type 2, period ${from} to ${to}` : "Type 2");
    } else {
      const asOf = formatDay(framework.as_of_date);
      parts.push(asOf ? `Type 1 as of ${asOf}` : "Type 1");
    }
  } else {
    const audit = formatDay(framework.audit_on);
    parts.push(audit ? `Audit on ${audit}` : "No audit date yet");
  }
  if (framework.assessor === "chosen" && framework.certification_body) {
    parts.push(framework.certification_body);
  } else if (framework.assessor === "undecided") {
    parts.push("auditor still deciding");
  }
  const needed = formatDay(framework.target_date);
  if (needed) parts.push(`needed by ${needed}`);
  return parts.join(", ");
}

function isOpen(step: OnboardingStep): boolean {
  return step.state === "not_started" || step.state === "in_progress";
}

// ---------------------------------------------------------------------------

function Meter({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <span
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={done}
      aria-label={`${done} of ${total}`}
      className="block h-[5px] w-24 shrink-0 overflow-hidden rounded-full bg-surface-sunken"
    >
      <span
        className={cn(
          "block h-full rounded-full transition-[width] duration-300 ease-state",
          done >= total ? "bg-status-success-base" : "bg-action-accent",
        )}
        style={{ width: `${pct}%` }}
      />
    </span>
  );
}

function FrameworkChips({
  codes,
  frameworks,
}: {
  codes: string[];
  frameworks: FrameworkFigures[] | null;
}) {
  if (codes.length === 0) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {codes.map((code) => (
        <span
          key={code}
          className="rounded-sm bg-surface-sunken px-1.5 py-px text-caption font-medium text-text-secondary"
        >
          {shortName(code, frameworks)}
        </span>
      ))}
    </span>
  );
}

function StateMark({ step }: { step: OnboardingStep }) {
  if (step.state === "done") {
    return (
      <span className="mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded-full bg-status-success-base text-text-inverse">
        <Icon name="check" className="size-[11px]" aria-hidden />
      </span>
    );
  }
  if (step.state === "not_permitted") {
    return <Icon name="lock" aria-hidden className="mt-0.5 size-[18px] shrink-0 text-text-subtle" />;
  }
  return (
    <span
      className={cn(
        "mt-0.5 size-[18px] shrink-0 rounded-full border-1.5",
        step.state === "skipped" ? "border-dashed border-border-strong" : "border-border-strong",
        step.state === "in_progress" && "border-action-accent",
      )}
    />
  );
}

function stepLine(step: OnboardingStep): string | null {
  if (step.state === "not_permitted") return "Your role cannot see this step.";
  if (step.state === "skipped" && step.skip) {
    const when = new Date(step.skip.at).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    return `Skipped by ${step.skip.by_name ?? "a former member"} on ${when}: ${step.skip.reason}`;
  }
  return step.detail;
}

function StepRow({
  step,
  frameworks,
  canSkip,
  onSkip,
  onReopen,
  reopening,
}: {
  step: OnboardingStep;
  frameworks: FrameworkFigures[] | null;
  canSkip: boolean;
  onSkip: (step: OnboardingStep) => void;
  onReopen: (step: OnboardingStep) => void;
  reopening: boolean;
}) {
  const line = stepLine(step);
  const counted = step.total_count !== null && step.done_count !== null && step.total_count > 0;
  return (
    <div className="flex items-start gap-3 border-t border-border px-5 py-3.5 first:border-t-0">
      <StateMark step={step} />
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={cn(
              "text-body-md font-semibold",
              step.state === "done" || step.state === "not_permitted"
                ? "text-text-subtle"
                : "text-text-primary",
            )}
          >
            {step.title}
          </span>
          {step.framework_code === null ? (
            <FrameworkChips codes={step.frameworks} frameworks={frameworks} />
          ) : null}
        </span>
        {line ? <span className="mt-0.5 block text-body-sm text-text-secondary">{line}</span> : null}
        {counted && step.state !== "done" ? (
          <span className="mt-2 block">
            <Meter done={step.done_count ?? 0} total={step.total_count ?? 0} />
          </span>
        ) : null}
      </span>
      <span className="flex shrink-0 items-center gap-1">
        {step.state === "skipped" && canSkip ? (
          <Button variant="ghost" size="sm" loading={reopening} onClick={() => onReopen(step)}>
            Reopen
          </Button>
        ) : null}
        {isOpen(step) && canSkip ? (
          <Button variant="ghost" size="sm" onClick={() => onSkip(step)}>
            Skip
          </Button>
        ) : null}
        {step.state !== "done" && step.state !== "not_permitted" ? (
          <Button asChild variant="secondary" size="sm">
            <Link to={step.link}>{step.can_act ? "Open" : "View"}</Link>
          </Button>
        ) : null}
      </span>
    </div>
  );
}

function StepGroup({
  title,
  steps,
  open,
  onToggle,
  children,
}: {
  title: string;
  steps: OnboardingStep[];
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const done = steps.filter((s) => s.state === "done").length;
  const id = `get-started-${title.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface-primary">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-5 py-3.5 text-left hover:bg-surface-hover"
      >
        <span className="flex-1 font-display text-title-md text-text-primary">{title}</span>
        <span className="text-caption tabular text-text-subtle">
          {done} of {steps.length} done
        </span>
        <Icon
          name="chevr"
          aria-hidden
          className={cn(
            "size-4 shrink-0 text-text-subtle transition-transform duration-150",
            open && "rotate-90",
          )}
        />
      </button>
      {open ? (
        <div id={id} className="border-t border-border">
          {children}
        </div>
      ) : null}
    </div>
  );
}

function Figure({ label, done, total }: { label: string; done: number; total: number }) {
  return (
    <div className="min-w-0">
      <p className="text-caption text-text-subtle">{label}</p>
      <p className="mt-0.5 text-body-md font-semibold tabular text-text-primary">
        {done} <span className="font-normal text-text-secondary">of {total}</span>
      </p>
    </div>
  );
}

function WhereYouStand({ frameworks }: { frameworks: FrameworkFigures[] }) {
  if (frameworks.length === 0) return null;
  return (
    <section aria-labelledby="where-you-stand" className="mt-6">
      <h2 id="where-you-stand" className="font-display text-title-md text-text-primary">
        Where you stand
      </h2>
      <div className="mt-3 space-y-3">
        {frameworks.map((f) => (
          <div
            key={f.code}
            className="grid grid-cols-2 gap-4 rounded-lg border border-border bg-surface-primary px-5 py-4 md:grid-cols-5"
          >
            <div className="col-span-2 md:col-span-1">
              <p className="text-body-md font-semibold text-text-primary">{shortName(f.code, frameworks)}</p>
              <Link
                to={`/frameworks/dashboard?framework=${encodeURIComponent(f.code)}`}
                className="text-caption text-action-accent hover:underline"
              >
                Open dashboard
              </Link>
            </div>
            <Figure
              label={f.scope_model === "categories" ? "Criteria with a control" : "Requirements with a control"}
              done={f.requirements_supported}
              total={f.requirements_total}
            />
            <Figure
              label={f.scope_model === "categories" ? "Criteria met" : "Requirements met"}
              done={f.requirements_met}
              total={f.requirements_total}
            />
            <Figure label="Controls with current evidence" done={f.controls_evidenced} total={f.controls_total} />
            {f.checks_passing + f.checks_failing > 0 ? (
              <Figure
                label="Controls passing checks"
                done={f.checks_passing}
                total={f.checks_passing + f.checks_failing}
              />
            ) : (
              <div>
                <p className="text-caption text-text-subtle">Automated checks</p>
                <p className="mt-0.5 text-body-sm text-text-secondary">None running yet</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Timeline({
  milestones,
  frameworks,
}: {
  milestones: Record<string, PlanMilestone[]>;
  frameworks: FrameworkFigures[];
}) {
  const [asTable, setAsTable] = useState(false);
  const rows = frameworks
    .map((f) => ({
      code: f.code,
      points: (milestones[f.code] ?? [])
        .map((m) => ({ ...m, on: m.actual_on ?? m.planned_on }))
        .filter((m): m is PlanMilestone & { on: string } => Boolean(m.on)),
    }))
    .filter((r) => r.points.length > 0);
  if (rows.length === 0) return null;
  const today = new Date().toISOString().slice(0, 10);
  const all = [...rows.flatMap((r) => r.points.map((p) => p.on)), today].sort();
  const start = new Date(`${all[0]}T00:00:00`).getTime();
  const end = new Date(`${all[all.length - 1]}T00:00:00`).getTime();
  const span = Math.max(end - start, 1);
  const at = (value: string) => ((new Date(`${value}T00:00:00`).getTime() - start) / span) * 100;

  return (
    <section aria-labelledby="timeline" className="mt-6">
      <div className="flex items-center justify-between">
        <h2 id="timeline" className="font-display text-title-md text-text-primary">
          Timeline
        </h2>
        <Button variant="ghost" size="sm" onClick={() => setAsTable((v) => !v)}>
          {asTable ? "Show as timeline" : "Show as table"}
        </Button>
      </div>
      <div className="mt-3 rounded-lg border border-border bg-surface-primary px-5 py-4">
        {asTable ? (
          <table className="w-full text-left text-body-sm">
            <thead className="text-caption text-text-subtle">
              <tr>
                <th className="py-1 font-normal">Framework</th>
                <th className="py-1 font-normal">Milestone</th>
                <th className="py-1 font-normal">Date</th>
                <th className="py-1 font-normal">State</th>
              </tr>
            </thead>
            <tbody>
              {rows.flatMap((r) =>
                r.points.map((p) => (
                  <tr key={`${r.code}-${p.kind}`} className="border-t border-border">
                    <td className="py-1.5">{shortName(r.code, frameworks)}</td>
                    <td className="py-1.5">{p.label}</td>
                    <td className="py-1.5 tabular">{formatDay(p.on)}</td>
                    <td className="py-1.5">{p.actual_on ? "Done" : "Planned"}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        ) : (
          <div className="space-y-5">
            {rows.map((r) => (
              <div key={r.code} className="grid grid-cols-[96px_1fr] items-center gap-3">
                <span className="text-body-sm font-semibold text-text-primary">{shortName(r.code, frameworks)}</span>
                <div className="relative h-8">
                  <div className="absolute inset-x-0 top-1/2 h-px bg-border" />
                  <div
                    className="absolute top-0 h-full w-px bg-action-accent"
                    style={{ left: `${at(today)}%` }}
                    aria-hidden
                  />
                  {r.points.map((p) => (
                    <span
                      key={p.kind}
                      tabIndex={0}
                      title={`${p.label}: ${formatDay(p.on)}${p.actual_on ? ", done" : ""}`}
                      aria-label={`${p.label}, ${formatDay(p.on)}${p.actual_on ? ", done" : ", planned"}`}
                      className={cn(
                        "absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent",
                        p.actual_on
                          ? "border-status-success-base bg-status-success-base"
                          : "border-action-accent bg-surface-primary",
                      )}
                      style={{ left: `${at(p.on)}%` }}
                    />
                  ))}
                </div>
              </div>
            ))}
            <p className="text-caption text-text-subtle">
              Filled dots are done, hollow dots are planned. The line marks today. Focus a dot for its date.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function SkipDialog({
  step,
  onClose,
}: {
  step: OnboardingStep | null;
  onClose: () => void;
}) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [reason, setReason] = useState("");
  const skip = useMutation({
    mutationFn: () => onboardingApi.skip(step?.key ?? "", reason.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [ONBOARDING_STATUS_KEY, principal?.tenant_id] });
      toast({ title: "Step skipped", tone: "neutral" });
      setReason("");
      onClose();
    },
  });
  const failure = skip.isError ? describeError(skip.error, "skip") : null;
  return (
    <Dialog
      open={step !== null}
      onOpenChange={(next) => {
        if (!next) {
          setReason("");
          skip.reset();
          onClose();
        }
      }}
    >
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Skip this step</DialogTitle>
          <DialogDescription>
            Everyone sees who skipped it and why. You can reopen it at any time.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <p className="mb-3 text-body-md font-semibold text-text-primary">{step?.title}</p>
          <TextArea
            label="Reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={500}
            rows={3}
            error={failure?.message}
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!reason.trim()} loading={skip.isPending} onClick={() => skip.mutate()}>
            Skip step
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------

function useStatus() {
  const { principal } = useAuth();
  return useQuery({
    queryKey: [ONBOARDING_STATUS_KEY, principal?.tenant_id],
    queryFn: onboardingApi.status,
  });
}

export function GetStartedPage() {
  const { principal } = useAuth();
  const canSkip = hasPermission(principal, "controls:manage");
  const canAddFramework = hasPermission(principal, "controls:manage");
  const queryClient = useQueryClient();
  const status = useStatus();
  const [skipping, setSkipping] = useState<OnboardingStep | null>(null);
  // Which groups are open, per history entry, so Back restores the page as it was.
  const [openGroups, setOpenGroups] = useEntryState<Record<string, boolean>>(
    "get-started.open",
    {},
  );
  const reopen = useMutation({
    mutationFn: (step: OnboardingStep) => onboardingApi.reopen(step.key),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: [ONBOARDING_STATUS_KEY, principal?.tenant_id] }),
  });

  const actions = canAddFramework ? (
    <>
      <Button asChild variant="secondary">
        <Link to="/setup">Guided setup</Link>
      </Button>
      <Button asChild variant="secondary">
        <Link to="/frameworks/list">Add a framework</Link>
      </Button>
    </>
  ) : undefined;

  if (status.isLoading) {
    return (
      <div className="mx-auto w-full max-w-[1040px] space-y-3">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-28 w-full rounded-lg" />
        <Skeleton className="h-28 w-full rounded-lg" />
      </div>
    );
  }

  if (status.isError || !status.data) {
    const failure = describeError(status.error, "Get Started");
    return (
      <div className="mx-auto w-full max-w-[1040px]">
        <PageHeader title="Get started" actions={actions} />
        <div className="mt-5">
          <ErrorState
            title={failure.title}
            description={failure.message}
            referenceId={failure.referenceId}
            onRetry={failure.retryable ? () => void status.refetch() : undefined}
          />
        </div>
      </div>
    );
  }

  const data: OnboardingStatus = status.data;
  const frameworks = data.frameworks;
  const shared = data.steps.filter((s) => s.framework_code === null);
  const next = data.steps.find((s) => s.key === data.next_key) ?? null;
  const lanes = (frameworks ?? [])
    .map((f) => ({ framework: f, steps: data.steps.filter((s) => s.framework_code === f.code) }))
    .filter((lane) => lane.steps.length > 0);

  // The first phase with open work is open by default; the user's own choice wins.
  const firstOpenPhase = data.phases.find((phase) =>
    shared.some((s) => s.phase === phase && isOpen(s)),
  );
  const isGroupOpen = (id: string, fallback: boolean) => openGroups[id] ?? fallback;
  const toggle = (id: string, fallback: boolean) =>
    setOpenGroups({ ...openGroups, [id]: !isGroupOpen(id, fallback) });

  const row = (step: OnboardingStep) => (
    <StepRow
      key={step.key}
      step={step}
      frameworks={frameworks}
      canSkip={canSkip}
      onSkip={setSkipping}
      onReopen={(s) => reopen.mutate(s)}
      reopening={reopen.isPending && reopen.variables?.key === step.key}
    />
  );

  return (
    <div className="mx-auto w-full max-w-[1040px]">
      <PageHeader title="Get started" actions={actions} />
      <YourPart />

      {frameworks && frameworks.length > 0 ? (
        <ul className="mt-5 flex flex-wrap gap-2" aria-label="Frameworks in your programme">
          {frameworks.map((f) => (
            <li key={f.code}>
              <Link
                to={`/frameworks/scope?framework=${encodeURIComponent(f.code)}`}
                className="flex items-center gap-2 rounded-md border border-border bg-surface-primary px-3 py-1.5 hover:bg-surface-hover"
              >
                <span className="text-body-sm font-semibold text-text-primary">
                  {shortName(f.code, frameworks)}
                </span>
                <span className="text-body-sm text-text-secondary">{frameworkSummary(f)}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-5 rounded-lg border border-border bg-surface-primary px-5 py-4">
        {next ? (
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-caption font-medium uppercase tracking-wide text-text-subtle">Next</p>
              <p className="mt-1 flex flex-wrap items-center gap-2 font-display text-title-md text-text-primary">
                {next.title}
                {next.framework_code ? (
                  <FrameworkChips codes={[next.framework_code]} frameworks={frameworks} />
                ) : null}
              </p>
              {next.detail ? <p className="mt-0.5 text-body-sm text-text-secondary">{next.detail}</p> : null}
            </div>
            <Button asChild>
              <Link to={next.link}>{next.can_act ? "Open" : "View"}</Link>
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <StatusPill status="success" label="Nothing open" />
            <p className="text-body-sm text-text-secondary">Every step you can see is done or skipped.</p>
          </div>
        )}
      </div>

      <section aria-labelledby="shared-steps" className="mt-6">
        <h2 id="shared-steps" className="sr-only">
          Steps for your whole programme
        </h2>
        <div className="space-y-3">
          {data.phases.map((phase) => {
            const steps = shared.filter((s) => s.phase === phase);
            if (steps.length === 0) return null;
            const id = `phase:${phase}`;
            const fallback = phase === firstOpenPhase;
            return (
              <StepGroup
                key={phase}
                title={PHASE_LABEL[phase]}
                steps={steps}
                open={isGroupOpen(id, fallback)}
                onToggle={() => toggle(id, fallback)}
              >
                {steps.map(row)}
              </StepGroup>
            );
          })}
        </div>
      </section>

      {lanes.length > 0 ? (
        <section aria-labelledby="framework-steps" className="mt-6">
          <h2 id="framework-steps" className="font-display text-title-md text-text-primary">
            For each framework
          </h2>
          <div className={cn("mt-3 grid items-start gap-3", lanes.length > 1 && "lg:grid-cols-2")}>
            {lanes.map(({ framework, steps }) => {
              const id = `lane:${framework.code}`;
              const fallback = steps.some(isOpen);
              return (
                <StepGroup
                  key={framework.code}
                  title={shortName(framework.code, frameworks)}
                  steps={steps}
                  open={isGroupOpen(id, fallback)}
                  onToggle={() => toggle(id, fallback)}
                >
                  {steps.map(row)}
                </StepGroup>
              );
            })}
          </div>
        </section>
      ) : null}

      {frameworks ? <Timeline milestones={data.milestones ?? {}} frameworks={frameworks} /> : null}

      {frameworks ? <WhereYouStand frameworks={frameworks} /> : null}

      <SkipDialog step={skipping} onClose={() => setSkipping(null)} />
    </div>
  );
}

const PART_TITLE: Record<string, string> = {
  approve: "Waiting for your approval",
  acknowledge: "Waiting for you to read and sign",
  task: "Assigned to you",
};

/** Your part (GS-12): the open items assigned to you, grouped, above the programme. */
function YourPart() {
  const { principal } = useAuth();
  const query = useQuery({
    queryKey: ["my-part", principal?.tenant_id],
    queryFn: () => apiFetch<{ items: { kind: string; title: string; link: string }[] }>("/onboarding/my-part"),
  });
  const items = query.data?.items ?? [];
  if (!items.length) return null;
  const kinds = ["approve", "acknowledge", "task"].filter((k) => items.some((i) => i.kind === k));
  return (
    <section className="mt-5 rounded-lg border border-border bg-surface-primary px-5 py-4">
      <h2 className="font-display text-title-md text-text-primary">Your part</h2>
      <div className="mt-2 grid gap-4 md:grid-cols-3">
        {kinds.map((k) => (
          <div key={k}>
            <h3 className="text-caption text-text-subtle">{PART_TITLE[k]}</h3>
            <ul className="mt-1 space-y-1">
              {items
                .filter((i) => i.kind === k)
                .slice(0, 6)
                .map((i) => (
                  <li key={i.link + i.title}>
                    <Link to={i.link} className="text-body-sm text-text-link">
                      {i.title}
                    </Link>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
