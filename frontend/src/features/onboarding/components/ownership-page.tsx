import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  ErrorState,
  PersonSelect,
  Skeleton,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { iamApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";

/**
 * Who owns what (guided onboarding OW-1 to OW-4): eight functions, each given to a member once.
 * Applying them proposes an owner for every control from its function; owners a person already
 * set are kept unless the user says otherwise, in a confirm popup that states the numbers.
 */

type OwnerFunction = {
  key: string;
  label: string;
  membership_id: string | null;
  member_name: string | null;
  controls: number;
};

type Ownership = {
  functions: OwnerFunction[];
  controls_total: number;
  controls_unowned: number;
  would_change: number;
  warnings: string[];
  reassign: string[];
};

const api = {
  get: () => apiFetch<Ownership>("/onboarding/owner-functions"),
  assign: (key: string, membershipId: string | null) =>
    apiFetch<void>(`/onboarding/owner-functions/${key}`, {
      method: "PUT",
      body: JSON.stringify({ membership_id: membershipId }),
    }),
  apply: (keepExisting: boolean) =>
    apiFetch<{ changed: number }>("/onboarding/owner-functions/apply", {
      method: "POST",
      body: JSON.stringify({ keep_existing: keepExisting }),
    }),
};

export function OwnershipPage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "controls:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const ownership = useQuery({ queryKey: ["owner-functions", principal?.tenant_id], queryFn: api.get });
  const members = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
    enabled: hasPermission(principal, "members:read"),
  });
  const [confirming, setConfirming] = useState(false);
  const [keepExisting, setKeepExisting] = useState(true);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["owner-functions"] }),
      queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
      queryClient.invalidateQueries({ queryKey: ["controls"] }),
    ]);
  const assign = useMutation({
    mutationFn: (args: { key: string; membershipId: string | null }) => api.assign(args.key, args.membershipId),
    onSuccess: () => void refresh(),
    onError: (error: unknown) => toast({ title: errorToast(error, "owner"), tone: "danger" }),
  });
  const apply = useMutation({
    mutationFn: () => api.apply(keepExisting),
    onSuccess: async (result) => {
      await refresh();
      setConfirming(false);
      toast({ title: `${result.changed} controls now have an owner from their function`, tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "owners"), tone: "danger" }),
  });

  if (ownership.isLoading) return <Skeleton className="h-80 w-full max-w-[820px] rounded-lg" />;
  if (ownership.isError || !ownership.data) {
    const failure = describeError(ownership.error, "owners");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void ownership.refetch() : undefined}
      />
    );
  }
  const data = ownership.data;
  const people = (members.data ?? [])
    .filter((m) => m.status === "active")
    .map((m) => ({ id: m.membership_id, name: m.full_name, email: m.email }));

  return (
    <div className="max-w-[820px]">
      <h2 className="font-display text-heading-sm text-text-primary">Who owns what</h2>
      <p className="mb-5 mt-1 text-body-md text-text-secondary">
        Name a person for each function once. Every control, document and task can take its owner
        from here.
      </p>

      {data.reassign.length ? (
        <ErrorBanner className="mb-4" title="Someone has left">
          <ul className="space-y-1">
            {data.reassign.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </ErrorBanner>
      ) : null}
      {data.warnings.map((w) => (
        <ErrorBanner key={w} className="mb-4" title="Check the internal audit">
          {w}
        </ErrorBanner>
      ))}

      <div className="rounded-lg border border-border bg-surface-primary">
        <div className="hidden grid-cols-[1fr_260px_90px] gap-3 border-b border-border px-5 py-2.5 text-caption text-text-subtle sm:grid">
          <span>Function</span>
          <span>Person</span>
          <span className="text-right">Controls</span>
        </div>
        {data.functions.map((f) => (
          <div
            key={f.key}
            className="grid items-center gap-3 border-b border-border px-5 py-3 last:border-b-0 sm:grid-cols-[1fr_260px_90px]"
          >
            <span className="text-body-md font-semibold text-text-primary">{f.label}</span>
            {canManage && people.length ? (
              <PersonSelect
                people={people}
                value={f.membership_id}
                onChange={(id) => assign.mutate({ key: f.key, membershipId: id })}
                placeholder="Choose a person"
                clearLabel="Nobody yet"
                aria-label={f.label}
              />
            ) : (
              <span className="text-body-sm text-text-secondary">{f.member_name ?? "Nobody yet"}</span>
            )}
            <span className="text-right text-body-sm tabular text-text-secondary">{f.controls}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {canManage ? (
          <Button onClick={() => setConfirming(true)} disabled={data.functions.every((f) => !f.membership_id)}>
            Apply to controls
          </Button>
        ) : null}
        <span className="text-body-sm text-text-secondary">
          {data.controls_unowned} of {data.controls_total} controls have no owner.{" "}
          <Link to="/controls?owner=unassigned" className="text-text-link">
            See them
          </Link>
        </span>
        {!hasPermission(principal, "members:invite") ? null : (
          <Link to="/settings/access/people?invite=1" className="text-body-sm text-text-link">
            Invite someone
          </Link>
        )}
      </div>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Apply owners to controls</DialogTitle>
            <DialogDescription>
              {data.would_change} controls with no owner will get the person of their function.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <label className="flex items-center gap-2 text-body-md text-text-primary">
              <Checkbox checked={keepExisting} onCheckedChange={(v) => setKeepExisting(v === true)} />
              Keep owners already set by a person
            </label>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button loading={apply.isPending} onClick={() => apply.mutate()}>
              Apply
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
