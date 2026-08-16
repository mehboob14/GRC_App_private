import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
} from "@/components/ui";
import { complianceApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import type { Framework } from "@/lib/api/types";

function FrameworkCard({ framework }: { framework: Framework }) {
  const current =
    framework.versions.find((version) => version.is_current) ??
    framework.versions[0];

  return (
    <Card asChild className="transition-colors duration-80 ease-state hover:border-action-accent-border hover:bg-surface-hover">
      <Link
        to={`/frameworks/${framework.id}`}
        className="flex flex-col gap-3 p-5"
      >
        <span className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-action-accent-tint text-action-accent">
            <Icon name="shield" className="size-5" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-display text-title-md text-text-primary">
              {framework.name}
            </span>
            {current ? (
              <span className="mt-0.5 block text-body-sm text-text-subtle">
                {current.version}
              </span>
            ) : null}
          </span>
          {framework.built_in ? <Badge variant="neutral">Built-in</Badge> : null}
        </span>

        {framework.description ? (
          <span className="line-clamp-2 text-body-sm text-text-secondary">
            {framework.description}
          </span>
        ) : null}

        <span className="mt-1 flex items-center gap-2 border-t border-border pt-3 text-body-sm text-text-secondary">
          <Icon name="doc" className="size-4 text-text-subtle" aria-hidden />
          <span className="tabular font-semibold text-text-primary">
            {current?.requirement_count ?? 0}
          </span>
          criteria
          <Icon name="chevr" className="ml-auto size-4 text-text-faint" aria-hidden />
        </span>
      </Link>
    </Card>
  );
}

/** Frameworks — the shipped catalogue. Read-only global content: this screen
 *  shows what the platform ships, never a tenant's own readiness (nothing
 *  computes that until the control library and evidence land). */
export function FrameworksPage() {
  const query = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
  });

  return (
    <div>
      <h1 className="font-display text-heading-lg text-text-primary">
        Frameworks
      </h1>
      <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
        The compliance frameworks Verity ships, with their criteria and the
        control templates that satisfy them.
      </p>

      <div className="mt-5">
        {query.isLoading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[168px] w-full rounded-lg" />
            ))}
          </div>
        ) : query.isError ? (
          <ErrorState
            title="Couldn’t load frameworks"
            description={
              query.error instanceof ApiError
                ? query.error.message
                : "The request failed. Retry, or contact support if it keeps happening."
            }
            referenceId={
              query.error instanceof ApiError
                ? query.error.correlationId
                : undefined
            }
            onRetry={() => void query.refetch()}
          />
        ) : (query.data ?? []).length === 0 ? (
          <EmptyState
            icon="shield"
            title="No frameworks loaded"
            description="Shipped content has not been seeded into this environment yet."
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {(query.data ?? []).map((framework) => (
              <FrameworkCard key={framework.id} framework={framework} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
