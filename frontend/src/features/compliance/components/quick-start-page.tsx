import { Button, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";

type StepState = "done" | "available" | "blocked";

type PathStep = {
  id: string;
  title: string;
  detail: string;
  owner: string;
  eta?: string;
  state: StepState;
  cta?: string;
  blockedBy?: string;
};

const STEPS: PathStep[] = [
  {
    id: "idp",
    title: "Connect your identity provider",
    detail: "Unlocked personnel sync, role assignment, access reviews",
    owner: "Jordan Park",
    state: "done",
  },
  {
    id: "infra",
    title: "Connect infrastructure",
    detail: "Unlocked 34 automated checks",
    owner: "Sam Iyer",
    state: "done",
  },
  {
    id: "vcs",
    title: "Connect version control",
    detail: "Unlocks 12 checks · branch protection evidence",
    owner: "Sam Iyer",
    eta: "~10 min",
    state: "available",
    cta: "Connect",
  },
  {
    id: "tickets",
    title: "Connect ticketing",
    detail: "Unlocks remediation tasks pushed to Jira",
    owner: "Riya Mehta",
    eta: "~10 min",
    state: "available",
    cta: "Connect",
  },
  {
    id: "scope",
    title: "Scope your framework",
    detail: "Unlocks 136 controls · defines what the audit covers",
    owner: "Alex Okafor",
    eta: "~30 min",
    state: "available",
    cta: "Scope",
  },
  {
    id: "roles",
    title: "Assign roles to your team",
    detail: "Unlocks ownership routing on findings and tasks",
    owner: "Alex Okafor",
    eta: "~15 min",
    state: "available",
    cta: "Assign",
  },
  {
    id: "personnel",
    title: "Onboard personnel",
    detail: "Unlocks MFA, background check and policy tracking for 51 people",
    owner: "Riya Mehta",
    eta: "~45 min",
    state: "blocked",
    blockedBy: "Blocked by · Scope your framework",
  },
  {
    id: "policies",
    title: "Publish policies",
    detail: "Unlocks 22 policy templates and acceptance tracking",
    owner: "Lena Cho",
    eta: "~2 hours",
    state: "blocked",
    blockedBy: "Blocked by · Assign roles",
  },
  {
    id: "gaps",
    title: "Review gaps and plan remediation",
    detail: "Unlocks your audit-readiness score",
    owner: "Alex Okafor",
    eta: "~90 min",
    state: "blocked",
    blockedBy: "Blocked by · Scope your framework",
  },
];

const UNLOCKS = [
  { label: "Controls monitorable", value: 34, total: 136 },
  { label: "Checks running", value: 46, total: 218 },
  { label: "Evidence auto-collected", value: 128, total: 842 },
  { label: "People tracked", value: 0, total: 51 },
];

/** Figma A1 · Quick Start (121:5770) — Readiness path. */
export function QuickStartPage() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-[28px] font-extrabold leading-8 tracking-[-0.56px] text-text">
        Readiness path
      </h1>
      <p className="mt-2 text-[14px] leading-5 text-text-muted">
        Dependency-aware setup. Each step shows what blocks it and what it unlocks.
      </p>

      <div className="mt-6 flex gap-4">
        <div className="min-w-0 flex-1 space-y-[10px]">
          <div className="flex items-center gap-8 rounded-xl border border-border bg-bg-elevated px-[22px] py-[18px]">
            <div>
              <p className="font-display text-[24px] font-bold leading-7 text-text">
                ~6 hours
              </p>
              <p className="mt-1 text-[12px] text-text-faint">of work remaining</p>
            </div>
            <div>
              <p className="font-display text-[24px] font-bold leading-7 text-text">4</p>
              <p className="mt-1 text-[12px] text-text-faint">owners involved</p>
            </div>
            <div>
              <p className="font-display text-[24px] font-bold leading-7 text-text">
                55 days
              </p>
              <p className="mt-1 text-[12px] text-text-faint">until window closes</p>
            </div>
            <div className="ml-auto text-right">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-text-faint">
                Next up
              </p>
              <p className="mt-1 text-[14px] font-semibold text-accent">
                Connect version control
              </p>
            </div>
          </div>

          {STEPS.map((step) => (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-3 rounded-xl border border-border bg-bg-elevated px-[18px] py-[14px]",
                step.state === "blocked" && "opacity-70",
              )}
            >
              <StepMark state={step.state} />
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "text-[14px] font-semibold leading-5",
                    step.state === "blocked" ? "text-text-muted" : "text-text",
                  )}
                >
                  {step.title}
                </p>
                <p className="mt-0.5 text-[12px] leading-4 text-text-faint">
                  {step.detail}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2.5 text-[12px] text-text-faint">
                <span>{step.owner}</span>
                {step.eta ? <span>{step.eta}</span> : null}
              </div>
              {step.state === "available" && step.cta ? (
                <Button size="sm" className="ml-2 h-8 shrink-0 px-3">
                  {step.cta}
                </Button>
              ) : null}
              {step.state === "blocked" && step.blockedBy ? (
                <span className="ml-2 shrink-0 rounded-md border border-border bg-bg-sunken px-3 py-1.5 text-[12px] text-text-faint">
                  {step.blockedBy}
                </span>
              ) : null}
            </div>
          ))}
        </div>

        <aside className="w-[300px] shrink-0 space-y-3">
          <div className="rounded-xl border border-border bg-bg-sunken p-4">
            <p className="text-[13px] font-semibold text-text">
              What setup has unlocked
            </p>
            <div className="mt-4 space-y-3.5">
              {UNLOCKS.map((row) => (
                <div key={row.label}>
                  <div className="mb-1.5 flex justify-between text-[12px]">
                    <span className="text-text-muted">{row.label}</span>
                    <span className="tabular text-text">
                      {row.value} / {row.total}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-border">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{
                        width: `${Math.max(2, (row.value / row.total) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-border bg-bg-elevated p-4">
            <p className="text-[13px] font-semibold text-text">Why order matters</p>
            <p className="mt-2 text-[12px] leading-4 text-text-muted">
              Three steps below are waiting on framework scope. Doing it next
              unblocks the most work.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function StepMark({ state }: { state: StepState }) {
  if (state === "done") {
    return (
      <span className="flex size-[18px] shrink-0 items-center justify-center rounded-full bg-pass text-white">
        <Icon name="check" className="size-3" strokeWidth={2.5} />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "size-[18px] shrink-0 rounded-full border-2",
        state === "available" ? "border-accent" : "border-border-strong",
      )}
    />
  );
}
