import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Badge, Button, useToast } from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { evidenceApi } from "@/lib/api/endpoints";
import type { MappingSuggestion } from "@/lib/api/types";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * Suggested control mappings for a piece of evidence.
 *
 * The engine SUGGESTS; a person links. Nothing here writes a mapping — each row
 * is a draft the reviewer approves or dismisses (rule 11). When a model key is
 * configured the backend uses it ("AI"); otherwise a deterministic matcher stands
 * in, and the source badge says which so a reviewer knows what produced the list.
 */
export function SuggestedMappings({
  evidenceId,
  onApproved,
  autoRun = false,
}: {
  evidenceId: string;
  /** Ask for suggestions as soon as the panel opens (right after an upload). */
  autoRun?: boolean;
  /** Called after a suggestion is linked, so the parent can refresh its controls. */
  onApproved: () => void | Promise<void>;
}) {
  const { toast } = useToast();
  const [rows, setRows] = useState<MappingSuggestion[] | null>(null);
  const [source, setSource] = useState<"ai" | "heuristic" | null>(null);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const suggest = useMutation({
    mutationFn: () => evidenceApi.suggestMappings(evidenceId),
    onSuccess: (r) => {
      setRows(r.suggestions);
      setSource(r.source);
      setDismissed(new Set());
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "suggestion list"), tone: "danger" }),
  });

  const { mutate: run } = suggest;
  useEffect(() => {
    if (autoRun) run();
  }, [autoRun, run]);

  const approve = useMutation({
    mutationFn: (controlId: string) => evidenceApi.approveMapping(evidenceId, controlId),
    onSuccess: async (_data, controlId) => {
      setDismissed((prev) => new Set(prev).add(controlId));
      await onApproved();
      toast({ title: "Control linked", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  const visible = (rows ?? []).filter((r) => !dismissed.has(r.control_id));

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-title-md text-text-primary">Suggested control mappings</h2>
          <p className="mt-1 text-body-sm text-text-secondary">
            Controls this evidence may also satisfy, across every framework you carry. Review each,
            then link the ones that fit. Nothing is linked without you saying so.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {source ? <Badge variant="role">{source === "ai" ? "AI" : "Suggested"}</Badge> : null}
          <Button size="sm" variant="secondary" loading={suggest.isPending} onClick={() => suggest.mutate()}>
            {rows ? "Refresh" : "Suggest mappings"}
          </Button>
        </div>
      </div>

      {rows === null ? (
        <p className="mt-4 text-body-sm text-text-subtle">
          Ask the mapping engine which of your controls this evidence supports.
        </p>
      ) : visible.length === 0 ? (
        <p className="mt-4 text-body-sm text-text-subtle">
          {rows.length === 0
            ? "No further controls look like a match. The relevant ones may already be linked."
            : "All suggestions handled."}
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {visible.map((r) => (
            <li key={r.control_id} className="flex items-start gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-body-md text-text-primary">
                  <span className="mr-2 font-display text-caption font-bold text-text-link">{r.code}</span>
                  {r.name}
                </p>
                <p className="mt-0.5 flex flex-wrap items-center gap-2 text-caption text-text-subtle">
                  <Badge variant={r.coverage === "full" ? "count" : "countWarn"}>{cap(r.coverage)}</Badge>
                  <span className="tabular">{Math.round(r.confidence * 100)}% match</span>
                  {r.maturity !== null ? (
                    <Badge variant={r.maturity >= 70 ? "count" : "countWarn"}>
                      Maturity {r.maturity}/100
                    </Badge>
                  ) : null}
                  <span className="min-w-0 truncate">· {r.rationale}</span>
                </p>
                {r.requirements.length > 0 ? (
                  <p className="mt-1 text-caption text-text-subtle">
                    Requirements: {r.requirements.join(" · ")}
                  </p>
                ) : null}
                {r.gaps ? (
                  <p className="mt-0.5 text-caption text-status-warning-text">Gap: {r.gaps}</p>
                ) : null}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="sm"
                  loading={approve.isPending && approve.variables === r.control_id}
                  onClick={() => approve.mutate(r.control_id)}
                >
                  Link
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDismissed((prev) => new Set(prev).add(r.control_id))}
                >
                  Dismiss
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
