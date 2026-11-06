import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { WorkspaceFramework } from "../frameworks-api";
import { frameworkSearch, useWorkspaceFrameworks } from "../use-frameworks";
import { AddFrameworkDialog } from "./add-framework-dialog";

function FrameworkCard({
  framework,
  canAdd,
  onAdd,
}: {
  framework: WorkspaceFramework;
  canAdd: boolean;
  onAdd: (framework: WorkspaceFramework) => void;
}) {
  const unit = framework.scope_model === "applicability" ? "requirements" : "criteria";

  return (
    <Card className="flex flex-col transition-colors duration-80 ease-state hover:border-action-accent-border">
      <Link
        to={`/frameworks/${framework.framework_id}`}
        className="flex flex-1 flex-col gap-3 rounded-t-lg p-5 hover:bg-surface-hover"
      >
        <span className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-action-accent-tint text-action-accent">
            <Icon name="shield" className="size-5" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-display text-title-md text-text-primary">{framework.name}</span>
            {framework.version ? (
              <span className="mt-0.5 block text-body-sm text-text-subtle">{framework.version}</span>
            ) : null}
          </span>
          {framework.added ? <Badge variant="statusPass">Added</Badge> : null}
        </span>
        {framework.description ? (
          <span className="line-clamp-3 text-body-sm text-text-secondary">{framework.description}</span>
        ) : null}
      </Link>

      <div className="flex items-center gap-2 border-t border-border px-5 py-3 text-body-sm text-text-secondary">
        <Icon name="doc" className="size-4 text-text-subtle" aria-hidden />
        <span className="tabular font-semibold text-text-primary">{framework.requirement_count}</span>
        {unit}
        <span className="ml-auto">
          {framework.added ? (
            <Link
              to={`/frameworks/dashboard${frameworkSearch(framework.code)}`}
              className="font-semibold text-text-link"
            >
              Open dashboard
            </Link>
          ) : canAdd ? (
            <Button size="sm" onClick={() => onAdd(framework)}>
              <Icon name="plus" className="size-4" />
              Add to workspace
            </Button>
          ) : (
            <span className="text-text-subtle">Not added</span>
          )}
        </span>
      </div>
    </Card>
  );
}

/** Frameworks: the catalogue, and which of them this workspace has added. Adding
 *  one shows what it would reuse first (one control library, so a control that
 *  answers two frameworks is worked and evidenced once). */
export function FrameworksPage() {
  const { principal } = useAuth();
  const canAdd = Boolean(principal?.permissions.includes("controls:manage"));
  const query = useWorkspaceFrameworks();
  const [adding, setAdding] = useState<WorkspaceFramework | null>(null);
  const failure = query.isError ? describeError(query.error, "framework catalogue") : null;

  return (
    <div>
      {query.isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[190px] w-full rounded-lg" />
          ))}
        </div>
      ) : failure ? (
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          onRetry={failure.retryable ? () => void query.refetch() : undefined}
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
            <FrameworkCard key={framework.framework_id} framework={framework} canAdd={canAdd} onAdd={setAdding} />
          ))}
        </div>
      )}
      <AddFrameworkDialog framework={adding} onClose={() => setAdding(null)} />
    </div>
  );
}
