import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  TextField,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { evidenceApi } from "@/lib/api/endpoints";
import type { LinkedTask } from "@/lib/api/types";
import { listTasks } from "@/features/tasks/api";

const humanStatus = (s: string) => s.replace(/_/g, " ");

/**
 * The tasks a piece of evidence supports — the remediation or work it evidences.
 * Links are the platform's `links` primitive, so the same edge shows on the task
 * too. Linking, not copying: the task stays owned by the tasks module.
 */
export function LinkedTasksSection({
  evidenceId,
  canManage,
}: {
  evidenceId: string;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = ["evidence-tasks", evidenceId];
  const [linking, setLinking] = useState(false);

  const tasksQuery = useQuery({ queryKey: key, queryFn: () => evidenceApi.linkedTasks(evidenceId) });
  const unlink = useMutation({
    mutationFn: (linkId: string) => evidenceApi.unlinkTask(evidenceId, linkId),
    onSuccess: (rows) => queryClient.setQueryData(key, rows),
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "task link"), tone: "danger" }),
  });

  const tasks = tasksQuery.data ?? [];
  // A panel inside a working page: one quiet line, not a full ErrorState.
  const loadFailure = tasksQuery.isError ? describeError(tasksQuery.error, "task list") : null;

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          Tasks
          {loadFailure ? null : (
            <span className="ml-2 tabular text-body-sm text-text-subtle">{tasks.length}</span>
          )}
        </h2>
        {canManage ? (
          <Button size="sm" variant="secondary" onClick={() => setLinking(true)}>
            Link task
          </Button>
        ) : null}
      </div>

      {loadFailure ? (
        // A failed load is not "no tasks linked": saying so would be a lie.
        <p className="text-body-sm text-status-danger-text">{loadFailure.message}</p>
      ) : tasks.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No tasks linked. Link the remediation or work this evidence supports so it shows on the task too.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {tasks.map((t) => (
            <li key={t.link_id} className="flex items-center gap-2.5 rounded-sm border border-border px-3 py-2">
              <Link to={`/tasks/${t.task_id}`} className="min-w-0 flex-1 truncate">
                <span className="mr-2 font-mono text-caption text-text-subtle">{t.code}</span>
                <span className="text-body-sm text-text-primary">{t.title}</span>
              </Link>
              <Badge variant="neutral">{humanStatus(t.status)}</Badge>
              {canManage ? (
                <button
                  type="button"
                  aria-label={`Unlink ${t.code}`}
                  onClick={() => unlink.mutate(t.link_id)}
                  className="text-text-subtle transition-colors hover:text-status-danger-text"
                >
                  <Icon name="x" className="size-4" />
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {linking ? (
        <LinkTaskDialog
          evidenceId={evidenceId}
          linkedTaskIds={tasks.map((t) => t.task_id)}
          onOpenChange={setLinking}
          onLinked={(rows) => queryClient.setQueryData(key, rows)}
        />
      ) : null}
    </div>
  );
}

function LinkTaskDialog({
  evidenceId,
  linkedTaskIds,
  onOpenChange,
  onLinked,
}: {
  evidenceId: string;
  linkedTaskIds: string[];
  onOpenChange: (open: boolean) => void;
  onLinked: (rows: LinkedTask[]) => void;
}) {
  const { toast } = useToast();
  const [search, setSearch] = useState("");

  const tasksQuery = useQuery({
    queryKey: ["evidence-link-picker", search],
    queryFn: () => listTasks({ search }, 1, 25),
  });
  const link = useMutation({
    mutationFn: (taskId: string) => evidenceApi.linkTask(evidenceId, taskId),
    onSuccess: (rows) => {
      onLinked(rows);
      toast({ title: "Task linked", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "task"), tone: "danger" }),
  });

  const items = (tasksQuery.data?.items ?? []).filter((t) => !linkedTaskIds.includes(t.id));
  const searchFailure = tasksQuery.isError ? describeError(tasksQuery.error, "task list") : null;

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Link a task</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <TextField
            label="Search tasks"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="By title or code…"
          />
          <div className="max-h-80 overflow-y-auto rounded-md border border-border">
            {searchFailure ? (
              // "No tasks match" for a failed search would send the reader
              // looking for a task that is there.
              <p className="p-4 text-body-sm text-status-danger-text">{searchFailure.message}</p>
            ) : items.length === 0 ? (
              <p className="p-4 text-body-sm text-text-subtle">
                {tasksQuery.isLoading ? "Loading…" : "No tasks match — everything found may already be linked."}
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {items.map((t) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      disabled={link.isPending}
                      onClick={() => link.mutate(t.id)}
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-surface-hover disabled:opacity-60"
                    >
                      <span className="min-w-0 flex-1 truncate">
                        <span className="mr-2 font-mono text-caption text-text-subtle">{t.code}</span>
                        <span className="text-body-sm text-text-primary">{t.title}</span>
                      </span>
                      <Badge variant="neutral">{humanStatus(t.status)}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
