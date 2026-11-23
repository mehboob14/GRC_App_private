import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  ErrorState,
  PageHeader,
  SegmentedControl,
  Skeleton,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { onboardingApi, type BaselineAnswer } from "../api";

/**
 * Baseline (guided onboarding PL-6): one control family per screen, asking what is already in
 * place. Answers are your own view and never change a control's status. Finishing freezes the
 * figures as the starting point the plan and later progress are measured from.
 */

const ANSWERS: { id: BaselineAnswer; label: string }[] = [
  { id: "in_place", label: "In place" },
  { id: "partly", label: "Partly" },
  { id: "not_in_place", label: "Not yet" },
  { id: "not_sure", label: "Not sure" },
];

export function BaselinePage() {
  const { principal } = useAuth();
  const canAnswer = hasPermission(principal, "controls:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["onboarding-baseline", principal?.tenant_id],
    queryFn: onboardingApi.baseline,
  });
  const [index, setIndex] = useState(0);
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["onboarding-baseline"] }),
      queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
    ]);
  const answer = useMutation({
    mutationFn: (a: { id: string; answer: BaselineAnswer }) => onboardingApi.answer(a.id, a.answer),
    onSuccess: () => void refresh(),
    onError: (error: unknown) => toast({ title: errorToast(error, "answer"), tone: "danger" }),
  });
  const complete = useMutation({
    mutationFn: onboardingApi.completeBaseline,
    onSuccess: async () => {
      await refresh();
      toast({ title: "Baseline saved as your starting point", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "baseline"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "baseline");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  const data = query.data;
  const done = data.status === "complete";
  const family = data.families[Math.min(index, data.families.length - 1)];
  const last = index >= data.families.length - 1;

  return (
    <div className="mx-auto w-full max-w-[880px]">
      <PageHeader title="What is already in place" />
      <p className="mt-2 text-body-sm text-text-secondary">
        {data.answered} of {data.total} answered.
        {done ? (
          <>
            {" "}Saved as your starting point.{" "}
            <Link to="/quick-start/plan" className="text-text-link">
              See your work plan
            </Link>
          </>
        ) : null}
      </p>

      {family ? (
        <section className="mt-4 rounded-lg border border-border bg-surface-primary">
          <header className="flex items-center justify-between border-b border-border px-5 py-3">
            <h2 className="font-display text-heading-sm text-text-primary">{family.family}</h2>
            <span className="text-body-sm tabular text-text-secondary">
              {index + 1} of {data.families.length}
            </span>
          </header>
          {family.controls.map((c) => (
            <div
              key={c.id}
              className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-3 first:border-t-0"
            >
              <span className="min-w-[72px] font-mono text-body-sm text-text-primary">{c.code}</span>
              <span className="min-w-0 flex-1 text-body-sm text-text-secondary">{c.name}</span>
              {canAnswer && !done ? (
                <SegmentedControl
                  items={ANSWERS}
                  value={(c.answer ?? "") as BaselineAnswer}
                  onChange={(id) => answer.mutate({ id: c.id, answer: id })}
                  label={`${c.code} answer`}
                />
              ) : (
                <span className="text-body-sm text-text-secondary">
                  {ANSWERS.find((a) => a.id === c.answer)?.label ?? "No answer"}
                </span>
              )}
            </div>
          ))}
        </section>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button variant="secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>
          Back
        </Button>
        {!last ? (
          <Button variant="secondary" onClick={() => setIndex(index + 1)}>
            Next family
          </Button>
        ) : null}
        {canAnswer && !done ? (
          <Button
            disabled={data.answered === 0}
            loading={complete.isPending}
            onClick={() => complete.mutate()}
          >
            Finish baseline
          </Button>
        ) : null}
      </div>
    </div>
  );
}
