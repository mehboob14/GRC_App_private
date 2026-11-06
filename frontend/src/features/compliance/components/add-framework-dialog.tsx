import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
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
  Skeleton,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { addFramework, frameworkOverlap, type WorkspaceFramework } from "../frameworks-api";
import { WORKSPACE_FRAMEWORKS_KEY } from "../use-frameworks";

function Figure({ value, label, hint }: { value: number; label: string; hint: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-2.5" title={hint}>
      <p className="font-display text-numeral-sm tabular text-text-primary">{value}</p>
      <p className="text-caption text-text-subtle">{label}</p>
    </div>
  );
}

/**
 * Add a framework to the workspace. Before anything is written it says what the
 * framework would reuse and what it would bring, counted from the controls the
 * workspace already runs: one library, so a control that answers both frameworks
 * is worked and evidenced once.
 */
export function AddFrameworkDialog({
  framework,
  onClose,
}: {
  framework: WorkspaceFramework | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { toast } = useToast();

  const overlap = useQuery({
    queryKey: ["framework-overlap", framework?.framework_id],
    queryFn: () => frameworkOverlap(framework!.framework_id),
    enabled: framework !== null,
  });

  const add = useMutation({
    mutationFn: () => addFramework(framework!.framework_id),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: WORKSPACE_FRAMEWORKS_KEY }),
        queryClient.invalidateQueries({ queryKey: ["controls"] }),
        queryClient.invalidateQueries({ queryKey: ["compliance-dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["engagement"] }),
        queryClient.invalidateQueries({ queryKey: ["engagement-coverage"] }),
        queryClient.invalidateQueries({ queryKey: ["framework-overlap"] }),
        queryClient.invalidateQueries({ queryKey: ["requirements"] }),
      ]);
      toast({
        title:
          result.controls_adopted > 0
            ? `${result.framework.name} added with ${result.controls_adopted} new controls`
            : `${result.framework.name} added`,
        tone: "success",
      });
      onClose();
      // Scope is the next thing a framework needs.
      navigate(`/frameworks/scope?framework=${encodeURIComponent(result.framework.code)}`);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "framework"), tone: "danger" }),
  });

  const data = overlap.data;
  const unit = framework?.scope_model === "applicability" ? "requirements" : "criteria";

  return (
    <Dialog open={framework !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent size="lg" scrollBody className="max-h-[88vh]">
        <DialogHeader>
          <DialogTitle>Add {framework?.name}</DialogTitle>
          <DialogDescription>
            One control library. {framework?.name} reuses the controls you already run and adds only
            the ones it needs.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          {overlap.isLoading ? (
            <Skeleton className="h-40 w-full rounded-lg" />
          ) : overlap.isError || !data ? (
            <ErrorState
              title={describeError(overlap.error, "framework").title}
              description={describeError(overlap.error, "framework").message}
              onRetry={() => void overlap.refetch()}
            />
          ) : (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                <Figure value={data.requirements_total} label={`Total ${unit}`} hint={`${data.version}`} />
                <Figure
                  value={data.covered + data.partly}
                  label="Already answered"
                  hint={`${data.covered} have a control you run as the main route, ${data.partly} are answered in part.`}
                />
                <Figure
                  value={data.needs_new}
                  label="Need a new control"
                  hint="Nothing you run answers it; adding the framework brings the controls that do."
                />
                <Figure
                  value={data.controls_to_adopt.length}
                  label="New controls to add"
                  hint="Controls the library has that this workspace does not run yet."
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-md border border-border p-3.5">
                  <p className="text-label-md text-text-primary">
                    {data.controls_in_use} controls you run already count here
                  </p>
                  <p className="mt-1 text-body-sm text-text-secondary">
                    They gain links to {framework?.name}. Their evidence, owners and status carry over,
                    and nothing about them changes for the frameworks you already use.
                  </p>
                </div>
                <div className="rounded-md border border-border p-3.5">
                  <p className="text-label-md text-text-primary">
                    {data.controls_to_adopt.length} new controls to add
                  </p>
                  {data.controls_to_adopt.length > 0 ? (
                    <ul className="mt-1.5 max-h-36 space-y-1 overflow-y-auto pr-1">
                      {data.controls_to_adopt.map((control) => (
                        <li key={control.code} className="flex gap-2 text-body-sm">
                          <span className="tabular w-14 shrink-0 font-semibold text-text-primary">
                            {control.code}
                          </span>
                          <span className="min-w-0 text-text-secondary">{control.name}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-body-sm text-text-secondary">None, the library already has them.</p>
                  )}
                </div>
              </div>

              <div>
                <p className="mb-1.5 text-label-sm text-text-secondary">By section</p>
                <div className="divide-y divide-border rounded-md border border-border">
                  {data.groups.map((g) => (
                    <div key={g.group} className="flex items-center gap-3 px-3 py-2 text-body-sm">
                      <span className="min-w-0 flex-1 truncate text-text-primary">{g.group}</span>
                      <span className="tabular w-12 text-right text-text-subtle">{g.total}</span>
                      <span className="tabular w-24 text-right text-status-success-text">
                        {g.covered + g.partly} answered
                      </span>
                      <span className="tabular w-16 text-right text-text-subtle">{g.needs_new} new</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!data || data.added} loading={add.isPending} onClick={() => add.mutate()}>
            Add {framework?.name}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
