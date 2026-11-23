import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  TextArea,
  useToast,
} from "@/components/ui";
import { engagementApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { WorkspaceFramework } from "../frameworks-api";
import { frameworkSearch, useWorkspaceFrameworks } from "../use-frameworks";
import { AddFrameworkDialog } from "./add-framework-dialog";

function FrameworkCard({
  framework,
  canAdd,
  onAdd,
  onTurnOff,
}: {
  framework: WorkspaceFramework;
  canAdd: boolean;
  onAdd: (framework: WorkspaceFramework) => void;
  onTurnOff: (framework: WorkspaceFramework) => void;
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
            <span className="flex items-center gap-3">
              {canAdd ? (
                <button
                  type="button"
                  onClick={() => onTurnOff(framework)}
                  className="text-body-sm text-text-subtle hover:text-text-primary"
                >
                  Turn off
                </button>
              ) : null}
              <Link
                to={`/frameworks/dashboard${frameworkSearch(framework.code)}`}
                className="font-semibold text-text-link"
              >
                Open dashboard
              </Link>
            </span>
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
  const [turningOff, setTurningOff] = useState<WorkspaceFramework | null>(null);
  const [reason, setReason] = useState("");
  const [onlyHere, setOnlyHere] = useState<string[] | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const turnOff = useMutation({
    mutationFn: () => engagementApi.deactivateFramework(turningOff?.framework_id ?? "", reason.trim()),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries();
      setOnlyHere(result.controls_only_here);
      setReason("");
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "framework"), tone: "danger" }),
  });
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
            <FrameworkCard
              key={framework.framework_id}
              framework={framework}
              canAdd={canAdd}
              onAdd={setAdding}
              onTurnOff={setTurningOff}
            />
          ))}
        </div>
      )}
      <AddFrameworkDialog framework={adding} onClose={() => setAdding(null)} />
      <Dialog
        open={turningOff !== null}
        onOpenChange={(open) => {
          if (!open) {
            setTurningOff(null);
            setOnlyHere(null);
            setReason("");
          }
        }}
      >
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>{onlyHere ? `${turningOff?.name} is off` : `Turn off ${turningOff?.name}`}</DialogTitle>
            <DialogDescription>
              {onlyHere
                ? "Nothing was deleted. You can add it again at any time."
                : "Its records are kept and it disappears from your pages. Controls stay as they are."}
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            {onlyHere ? (
              onlyHere.length ? (
                <p className="text-body-sm text-text-secondary">
                  {onlyHere.length} controls were only needed by it: {onlyHere.slice(0, 12).join(", ")}
                  {onlyHere.length > 12 ? ` and ${onlyHere.length - 12} more` : ""}. Decide on the
                  Controls page whether to keep running them.
                </p>
              ) : (
                <p className="text-body-sm text-text-secondary">Every control it used is still needed by another framework.</p>
              )
            ) : (
              <TextArea label="Reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
            )}
          </DialogBody>
          <DialogFooter>
            {onlyHere ? (
              <Button onClick={() => setTurningOff(null)}>Done</Button>
            ) : (
              <>
                <Button variant="secondary" onClick={() => setTurningOff(null)}>
                  Cancel
                </Button>
                <Button disabled={!reason.trim()} loading={turnOff.isPending} onClick={() => turnOff.mutate()}>
                  Turn off
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
