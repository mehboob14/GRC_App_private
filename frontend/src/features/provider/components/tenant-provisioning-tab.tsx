import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ErrorBanner,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  useToast,
} from "@/components/ui";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { tenantsApi } from "../api";
import { describeProviderError } from "../errors";
import { providerKeys, useTenantProvisioning } from "../hooks";
import { STEP_META, formatDateTime } from "../tokens";
import { useTenantOutlet } from "./tenant-outlet";

export function TenantProvisioningTab() {
  const { tenant } = useTenantOutlet();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useTenantProvisioning(tenant.id);

  const run = useMutation({
    mutationFn: () => tenantsApi.runProvisioning(tenant.id),
    onSuccess: (result) => {
      queryClient.setQueryData(providerKeys.provisioning(tenant.id), result);
      // Finishing the last step is what makes the tenant active.
      void queryClient.invalidateQueries({ queryKey: providerKeys.tenant(tenant.id) });
      void queryClient.invalidateQueries({ queryKey: providerKeys.tenantsRoot });
      toast({
        title:
          result.remaining.length === 0
            ? "Provisioning complete"
            : `Provisioning ran. ${result.remaining.length} still waiting`,
        tone: "success",
      });
    },
  });

  const failure = run.isError ? describeProviderError(run.error, "tenant") : null;
  const alertRef = useAlertFocus(Boolean(failure));

  if (query.isLoading) {
    return <Skeleton className="h-72 w-full max-w-[880px] rounded-lg" />;
  }
  if (query.isError || !query.data) {
    const problem = describeProviderError(query.error, "provisioning");
    return (
      <ErrorState
        title={problem.title}
        description={problem.message}
        referenceId={problem.referenceId}
        onRetry={problem.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const { steps, remaining } = query.data;

  return (
    <section className="max-w-[880px] rounded-lg border border-border bg-surface-primary p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-heading-sm text-text-primary">
            Provisioning
          </h2>
          <p className="mt-1 text-body-sm text-text-subtle">
            Running it again is safe. Finished steps are left alone.
          </p>
        </div>
        <Button
          variant={remaining.length === 0 ? "secondary" : "primary"}
          loading={run.isPending}
          disabled={remaining.length === 0}
          onClick={() => run.mutate()}
        >
          <Icon name="lightning" className="size-4" />
          Run provisioning
        </Button>
      </div>

      {failure ? (
        <ErrorBanner ref={alertRef} className="mt-4" title={failure.title}>
          {failure.message}
        </ErrorBanner>
      ) : null}

      <ol className="mt-5 divide-y divide-border rounded-md border border-border">
        {steps.map((step) => {
          const meta = STEP_META[step.step];
          const done = step.status === "done";
          return (
            <li key={step.step} className="flex items-center gap-4 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-body-md font-medium text-text-primary">
                  {meta.label}
                </p>
                <p className="text-body-sm text-text-subtle">
                  {done ? meta.done : meta.waiting}
                </p>
              </div>
              {done && step.completed_at ? (
                <span className="hidden text-caption text-text-subtle sm:block">
                  {formatDateTime(step.completed_at)}
                </span>
              ) : null}
              <StatusPill
                status={done ? "success" : "pending"}
                label={done ? "Done" : "Pending"}
              />
            </li>
          );
        })}
      </ol>
    </section>
  );
}
