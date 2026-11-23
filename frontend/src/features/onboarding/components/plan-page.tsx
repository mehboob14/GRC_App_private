import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusPill,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { iamApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { onboardingApi } from "../api";

/**
 * Work plan (guided onboarding PL-7, PL-8, PL-11, PL-12): computed from the baseline. A control
 * not in place gets a task to put it in place; one in place with no current evidence gets an
 * evidence request. Approving raises the tasks once; approving again adds only what is new.
 */

export function PlanPage() {
  const { principal } = useAuth();
  const canApprove = hasPermission(principal, "controls:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [confirming, setConfirming] = useState(false);
  const query = useQuery({
    queryKey: ["onboarding-plan", principal?.tenant_id],
    queryFn: onboardingApi.plan,
  });
  const members = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
    enabled: hasPermission(principal, "members:read"),
  });
  const connections = useQuery({
    queryKey: ["onboarding-connections", principal?.tenant_id],
    queryFn: onboardingApi.connections,
    enabled: hasPermission(principal, "connectors:read"),
  });
  const approve = useMutation({
    mutationFn: onboardingApi.approvePlan,
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["onboarding-plan"] }),
        queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
      ]);
      setConfirming(false);
      toast({ title: `${result.raised} tasks raised`, tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "plan"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "plan");
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
  const names = new Map((members.data ?? []).map((m) => [m.membership_id, m.full_name]));
  const todo = data.items.filter((i) => !i.raised).length;

  if (!data.items.length) {
    return (
      <div className="mx-auto w-full max-w-[880px]">
        <PageHeader title="Work plan" />
        <div className="mt-6">
          <EmptyState
            title="No plan yet"
            description="Say what is already in place first. The plan is built from your answers."
            action={
              <Button asChild>
                <Link to="/quick-start/baseline">Start the baseline</Link>
              </Button>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[960px]">
      <PageHeader title="Work plan" />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <p className="text-body-sm text-text-secondary">
          {data.items.length} items, {data.raised} raised as tasks.
          {data.due_label ? ` Due by ${data.due_on}, before ${data.due_label}.` : " No date planned yet."}
        </p>
        {canApprove && todo ? (
          <Button onClick={() => setConfirming(true)}>Approve and raise {todo} tasks</Button>
        ) : null}
      </div>
      <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-surface-primary">
        <table className="w-full min-w-[640px] text-left text-body-sm">
          <thead className="border-b border-border text-caption text-text-subtle">
            <tr>
              <th className="px-4 py-2.5 font-normal">Task</th>
              <th className="px-4 py-2.5 font-normal">Owner</th>
              <th className="px-4 py-2.5 font-normal">State</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((i) => (
              <tr key={i.key} className="border-b border-border last:border-b-0">
                <td className="px-4 py-3 text-text-primary">{i.title}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {i.owner_membership_id ? (names.get(i.owner_membership_id) ?? "Assigned") : "Nobody yet"}
                </td>
                <td className="px-4 py-3">
                  <StatusPill
                    status={i.raised ? "success" : "neutral"}
                    label={i.raised ? "Raised" : i.kind === "evidence" ? "Evidence request" : "To do"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Snapshots />
      {connections.data?.length ? (
        <section className="mt-5 rounded-lg border border-border bg-surface-primary">
          <h2 className="border-b border-border px-5 py-3 font-display text-title-md text-text-primary">
            Connect these to file evidence for you
          </h2>
          {connections.data.map((c) => (
            <div key={c.key} className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-3 first:border-t-0">
              <span className="font-semibold text-text-primary">{c.name}</span>
              <span className="flex-1 text-body-sm text-text-secondary">{c.because}</span>
              {c.connected ? (
                <StatusPill status="success" label="Connected" />
              ) : c.status === "available" ? (
                <Button asChild size="sm" variant="secondary">
                  <Link to="/connectors">Connect</Link>
                </Button>
              ) : (
                <StatusPill status="neutral" label="Coming soon" />
              )}
            </div>
          ))}
        </section>
      ) : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Raise the plan as tasks"
        consequence={`${todo} tasks will be created and assigned. Items already raised are left alone.`}
        confirmLabel="Raise tasks"
        loading={approve.isPending}
        onConfirm={() => approve.mutate()}
      />
    </div>
  );
}

type Snapshot = {
  id: string;
  label: string;
  created_at: string;
  figures: { frameworks?: Record<string, { requirements_total: number; requirements_met: number }> };
};

/** Progress since the baseline (PL-9): figures frozen at the baseline and at each milestone. */
function Snapshots() {
  const { principal } = useAuth();
  const query = useQuery({
    queryKey: ["onboarding-snapshots", principal?.tenant_id],
    queryFn: () => apiFetch<Snapshot[]>("/onboarding/snapshots"),
  });
  const rows = query.data ?? [];
  if (!rows.length) return null;
  return (
    <section className="mt-5 rounded-lg border border-border bg-surface-primary">
      <h2 className="border-b border-border px-5 py-3 font-display text-title-md text-text-primary">
        Progress since the baseline
      </h2>
      {rows.map((r) => (
        <div key={r.id} className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-2.5 first:border-t-0 text-body-sm">
          <span className="min-w-[160px] font-semibold text-text-primary">{r.label}</span>
          <span className="tabular text-text-secondary">{new Date(r.created_at).toLocaleDateString()}</span>
          <span className="flex-1 text-text-secondary">
            {Object.entries(r.figures.frameworks ?? {})
              .map(([code, f]) => `${code}: ${f.requirements_met} of ${f.requirements_total} met`)
              .join(", ")}
          </span>
        </div>
      ))}
    </section>
  );
}
