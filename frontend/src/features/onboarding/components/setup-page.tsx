import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorState,
  SegmentedControl,
  Skeleton,
  useToast,
} from "@/components/ui";
import { addFramework } from "@/features/compliance/frameworks-api";
import { useWorkspaceFrameworks, WORKSPACE_FRAMEWORKS_KEY } from "@/features/compliance/use-frameworks";
import { ProfileQuestions } from "@/features/tenancy/profile-questions";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { tenantApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { onboardingApi } from "../api";
import { OwnershipPage } from "./ownership-page";
import { SuggestionsPage } from "./suggestions-page";

/**
 * Guided setup (part 3 section 3): six screens, resumable, ending on Get Started. Each screen
 * is the real screen or a short form over the same API, so nothing here is a second copy of a
 * rule. Where the flow stands is saved on every move.
 */

const TITLES: Record<string, string> = {
  start: "Where are you starting from",
  frameworks: "Choose your frameworks",
  import: "Bring what you already have",
  profile: "Tell us about your company",
  audit: "Your audit",
  owners: "Who owns what",
  suggestions: "Review suggestions",
};

export function SetupPage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "controls:manage");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const setup = useQuery({ queryKey: ["onboarding-setup", principal?.tenant_id], queryFn: onboardingApi.setup });
  const [step, setStep] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: onboardingApi.saveSetup,
    onSuccess: (view) => queryClient.setQueryData(["onboarding-setup", principal?.tenant_id], view),
    onError: (error: unknown) => toast({ title: errorToast(error, "setup"), tone: "danger" }),
  });

  useEffect(() => {
    if (step === null && setup.data) setStep(setup.data.setup_step ?? "start");
  }, [setup.data, step]);

  if (setup.isLoading || step === null) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (setup.isError || !setup.data) {
    const failure = describeError(setup.error, "setup");
    return <ErrorState title={failure.title} description={failure.message} referenceId={failure.referenceId} />;
  }
  const steps = setup.data.steps;
  const at = steps.indexOf(step);
  const go = (next: string) => {
    setStep(next);
    if (canManage) save.mutate({ setup_step: next });
  };
  const finish = async () => {
    if (canManage) await save.mutateAsync({ setup_step: "suggestions", complete: true });
    void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
    navigate("/quick-start");
  };

  return (
    <div className="mx-auto w-full max-w-[960px]">
      <ol className="mb-6 flex flex-wrap gap-2" aria-label="Setup steps">
        {steps.map((s, i) => (
          <li key={s}>
            <button
              type="button"
              onClick={() => go(s)}
              aria-current={s === step ? "step" : undefined}
              className={`rounded-full px-3 py-1 text-caption ${
                s === step
                  ? "bg-action-primary text-action-primary-fg"
                  : i < at
                    ? "bg-surface-sunken text-text-primary"
                    : "bg-surface-sunken text-text-subtle"
              }`}
            >
              {i + 1}. {TITLES[s] ?? s}
            </button>
          </li>
        ))}
      </ol>

      <h1 className="mb-4 font-display text-heading-md text-text-primary">{TITLES[step]}</h1>

      {step === "start" ? (
        <StartStep
          value={setup.data.start_point}
          onPick={(start_point) => {
            if (canManage) save.mutate({ start_point, setup_step: "frameworks" });
            setStep("frameworks");
          }}
        />
      ) : null}
      {step === "frameworks" ? <FrameworksStep canManage={canManage} /> : null}
      {step === "import" ? <ImportStep /> : null}
      {step === "profile" ? <ProfileStep /> : null}
      {step === "audit" ? <AuditStep /> : null}
      {step === "owners" ? <OwnershipPage /> : null}
      {step === "suggestions" ? <SuggestionsPage /> : null}

      <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-4">
        {at > 0 ? (
          <Button variant="secondary" onClick={() => go(steps[at - 1])}>
            Back
          </Button>
        ) : null}
        {at < steps.length - 1 ? (
          step !== "start" ? <Button onClick={() => go(steps[at + 1])}>Next</Button> : null
        ) : (
          <Button loading={save.isPending} onClick={() => void finish()}>
            Finish and open Get Started
          </Button>
        )}
        <Link to="/quick-start" className="self-center text-body-sm text-text-link">
          Leave for now
        </Link>
      </div>
    </div>
  );
}

function StartStep({
  value,
  onPick,
}: {
  value: string | null;
  onPick: (v: "fresh" | "existing") => void;
}) {
  const options = [
    { id: "fresh" as const, title: "Starting fresh", body: "No policies or audit yet. We build it with you." },
    {
      id: "existing" as const,
      title: "We already have a programme",
      body: "Bring your policies, past reports and certificates. We match them to your controls.",
    },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onPick(o.id)}
          className={`rounded-lg border p-5 text-left ${
            value === o.id ? "border-action-primary bg-action-accent-tint" : "border-border bg-surface-primary"
          }`}
        >
          <span className="block font-semibold text-text-primary">{o.title}</span>
          <span className="mt-1 block text-body-sm text-text-secondary">{o.body}</span>
        </button>
      ))}
    </div>
  );
}

type Answer = "yes" | "no" | "not_sure";
const YES_NO = [
  { id: "yes" as const, label: "Yes" },
  { id: "no" as const, label: "No" },
  { id: "not_sure" as const, label: "Not sure" },
];

/** "Help me choose" (task 3.2): three questions, one plain recommendation. Guidance only. */
function recommend(a: { report: Answer; certificate: Answer; financial: Answer }): string {
  const soc2 = a.report === "yes";
  const iso = a.certificate === "yes";
  const lines: string[] = [];
  if (soc2 && iso) lines.push("Run SOC 2 and ISO 27001 together. Most controls serve both.");
  else if (soc2) lines.push("Start with SOC 2.");
  else if (iso) lines.push("Start with ISO 27001. You do not need SOC 2 first.");
  else lines.push("Ask your largest customers which they expect. SOC 2 is common in North America, ISO 27001 elsewhere.");
  if (a.financial === "yes")
    lines.push("Your service touches customers' financial reporting, so they may also ask for SOC 1. See the SOC 1 guide.");
  return lines.join(" ");
}

function FrameworksStep({ canManage }: { canManage: boolean }) {
  const frameworks = useWorkspaceFrameworks();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [helping, setHelping] = useState(false);
  const [answers, setAnswers] = useState<{ report: Answer; certificate: Answer; financial: Answer }>({
    report: "not_sure",
    certificate: "not_sure",
    financial: "not_sure",
  });
  const add = useMutation({
    mutationFn: addFramework,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: WORKSPACE_FRAMEWORKS_KEY }),
    onError: (error: unknown) => toast({ title: errorToast(error, "framework"), tone: "danger" }),
  });
  if (frameworks.isLoading) return <Skeleton className="h-40 w-full rounded-lg" />;
  return (
    <div>
      <div className="rounded-lg border border-border bg-surface-primary">
        {(frameworks.data ?? []).map((f) => (
          <div key={f.framework_id} className="flex items-center gap-3 border-t border-border px-5 py-3 first:border-t-0">
            <span className="flex-1 font-semibold text-text-primary">{f.name}</span>
            {f.added ? (
              <span className="text-body-sm text-text-secondary">Added</span>
            ) : canManage ? (
              <Button
                size="sm"
                variant="secondary"
                loading={add.isPending && add.variables === f.framework_id}
                onClick={() => add.mutate(f.framework_id)}
              >
                Add
              </Button>
            ) : null}
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-4">
        <Button variant="ghost" size="sm" onClick={() => setHelping(true)}>
          Help me choose
        </Button>
        <Link to="/guides/soc1" className="self-center text-body-sm text-text-link">
          What about SOC 1?
        </Link>
      </div>
      <Dialog open={helping} onOpenChange={setHelping}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Help me choose</DialogTitle>
          </DialogHeader>
          <DialogBody>
            {(
              [
                ["report", "Do customers ask you for a SOC 2 report?"],
                ["certificate", "Do customers or tenders ask for an ISO 27001 certificate?"],
                ["financial", "Does your service affect your customers' financial statements?"],
              ] as const
            ).map(([key, question]) => (
              <div key={key} className="mb-3">
                <p className="mb-1 text-body-sm text-text-primary">{question}</p>
                <SegmentedControl
                  items={YES_NO}
                  value={answers[key]}
                  onChange={(v) => setAnswers({ ...answers, [key]: v })}
                  label={question}
                />
              </div>
            ))}
            <p className="mt-4 rounded-md bg-surface-sunken p-3 text-body-sm text-text-primary">
              {recommend(answers)}
            </p>
          </DialogBody>
          <DialogFooter>
            <Button onClick={() => setHelping(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ImportStep() {
  const cards = [
    {
      title: "Reports and certificates",
      body: "Record your last SOC 2 report or ISO certificate, with its findings.",
      link: "/frameworks/assurance",
      action: "Record them",
    },
    {
      title: "Your documents",
      body: "Upload the policies you have and match each to what your frameworks expect.",
      link: "/documents/required?import=1",
      action: "Import documents",
    },
    {
      title: "What is already in place",
      body: "Answer the baseline so your plan asks for evidence, not new policies.",
      link: "/quick-start/baseline",
      action: "Start the baseline",
    },
  ];
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {cards.map((c) => (
        <div key={c.title} className="rounded-lg border border-border bg-surface-primary p-5">
          <span className="block font-semibold text-text-primary">{c.title}</span>
          <span className="mt-1 block text-body-sm text-text-secondary">{c.body}</span>
          <Button asChild size="sm" variant="secondary" className="mt-3">
            <Link to={c.link}>{c.action}</Link>
          </Button>
        </div>
      ))}
    </div>
  );
}

function LawsLine() {
  const { principal } = useAuth();
  const laws = useQuery({
    queryKey: ["regulations", principal?.tenant_id],
    queryFn: () => apiFetch<{ regulations: unknown[] }>("/regulations"),
  });
  const count = laws.data?.regulations.length ?? 0;
  if (!count) return null;
  return (
    <p className="mt-4 text-body-sm text-text-secondary">
      From your answers, {count} laws may apply.{" "}
      <Link to="/regulations" className="text-text-link">
        See them
      </Link>
    </p>
  );
}

function ProfileStep() {
  const { principal } = useAuth();
  const query = useQuery({
    queryKey: ["company-profile", principal?.tenant_id],
    queryFn: () => tenantApi.getCompanyProfile(),
  });
  if (!query.data) return <Skeleton className="h-64 w-full rounded-lg" />;
  return (
    <>
      <ProfileQuestions profile={query.data} canManage={hasPermission(principal, "tenant:manage")} />
      <LawsLine />
    </>
  );
}

function AuditStep() {
  const frameworks = useWorkspaceFrameworks();
  const added = (frameworks.data ?? []).filter((f) => f.added);
  return (
    <div className="rounded-lg border border-border bg-surface-primary">
      {added.map((f) => (
        <div key={f.framework_id} className="flex items-center gap-3 border-t border-border px-5 py-3 first:border-t-0">
          <span className="flex-1 font-semibold text-text-primary">{f.name}</span>
          <Button asChild size="sm" variant="secondary">
            <Link to={`/frameworks/scope?framework=${f.code}`}>
              {f.scope_model === "categories" ? "Report type, period and auditor" : "Scope, dates and certification body"}
            </Link>
          </Button>
        </div>
      ))}
    </div>
  );
}
