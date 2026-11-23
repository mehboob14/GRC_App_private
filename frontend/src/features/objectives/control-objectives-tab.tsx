import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  SearchableSelect,
  Skeleton,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { objectivesApi, OUTCOME, REASON, type Objective } from "./api";

/**
 * A control's assessment objectives (AO-2, AO-4): what an auditor checks, whether it is shown,
 * and the one next step for each objective not met. A person can mark an objective not
 * applicable with a reason, and say which uploaded evidence is which record.
 */
export function ControlObjectivesTab({
  controlId,
  evidence,
  canManage,
}: {
  controlId: string;
  evidence: { id: string; title: string }[];
  canManage: boolean;
}) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["control-objectives", principal?.tenant_id, controlId],
    queryFn: () => objectivesApi.forControl(controlId),
  });
  const [declining, setDeclining] = useState<Objective | null>(null);
  const [reason, setReason] = useState("");
  const [tagging, setTagging] = useState<{ artifact: string; name: string } | null>(null);
  const [pick, setPick] = useState<string | null>(null);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["control-objectives"] }),
      queryClient.invalidateQueries({ queryKey: ["objectives"] }),
    ]);
  const decline = useMutation({
    mutationFn: (code: string) => objectivesApi.notApplicable(code, reason),
    onSuccess: async () => {
      await refresh();
      setDeclining(null);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "objective"), tone: "danger" }),
  });
  const again = useMutation({
    mutationFn: objectivesApi.appliesAgain,
    onSuccess: () => void refresh(),
    onError: (e: unknown) => toast({ title: errorToast(e, "objective"), tone: "danger" }),
  });
  const tag = useMutation({
    mutationFn: () => objectivesApi.tag(tagging?.artifact ?? "", pick ?? ""),
    onSuccess: async () => {
      await refresh();
      setTagging(null);
      toast({ title: "Marked as this record", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "evidence"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-64 w-full rounded-lg" />;
  const data = query.data;
  if (!data) {
    return (
      <EmptyState
        title="No objectives written for this control yet"
        description="Objectives arrive in waves. This control is in a later one."
      />
    );
  }

  const groups: { title: string; items: Objective[] }[] = [
    { title: "Design", items: data.objectives.filter((o) => o.assurance === "design") },
    { title: "Operation", items: data.objectives.filter((o) => o.assurance === "operating") },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-body-sm text-text-secondary">
        <StatusPill status={data.design_ready ? "success" : "pending"} label={data.design_ready ? "Design shown" : "Design not shown yet"} />
        <StatusPill
          status={data.operating_ready ? "success" : "pending"}
          label={data.operating_ready ? "Operation shown" : "Operation not shown yet"}
        />
        {data.review_status !== "reviewed" ? <span>Drafted by Verity, not yet independently reviewed.</span> : null}
      </div>
      {groups.map((g) =>
        g.items.length ? (
          <section key={g.title} className="rounded-lg border border-border bg-surface-primary">
            <h3 className="border-b border-border px-5 py-3 font-display text-title-sm text-text-primary">{g.title}</h3>
            {g.items.map((o) => {
              const outcome = OUTCOME[o.outcome];
              return (
                <div key={o.code} className="space-y-2 border-t border-border px-5 py-3 first:border-t-0">
                  <div className="flex flex-wrap items-start gap-3">
                    <span className="min-w-[64px] font-mono text-body-sm text-text-primary">{o.code}</span>
                    <p className="min-w-0 flex-1 text-body-sm text-text-primary">{o.statement}</p>
                    <StatusPill status={outcome.family} label={outcome.label} />
                  </div>
                  {o.not_applicable_reason ? (
                    <p className="pl-[76px] text-body-sm text-text-secondary">Not applicable: {o.not_applicable_reason}</p>
                  ) : (
                    <ul className="space-y-1 pl-[76px]">
                      {o.artifacts.map((a) => (
                        <li key={a.key} className="flex flex-wrap items-center gap-2 text-body-sm">
                          <span className={a.state === "satisfied" ? "text-text-secondary" : "text-text-primary"}>{a.name}</span>
                          <span className="text-caption text-text-subtle">
                            {a.state === "satisfied" ? "Shown" : (REASON[a.reason ?? "missing"] ?? a.reason)}
                          </span>
                          {canManage && a.state !== "satisfied" && a.sources.includes("person") && evidence.length ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setPick(null);
                                setTagging({ artifact: a.key, name: a.name });
                              }}
                            >
                              This is in my evidence
                            </Button>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                  {o.interview_with.length ? (
                    <p className="pl-[76px] text-caption text-text-subtle">
                      An auditor may also talk to your {o.interview_with.join(" and ").toLowerCase()}.
                    </p>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-2 pl-[76px]">
                    {o.next_step ? (
                      <Button asChild size="sm" variant="secondary">
                        <Link to={o.next_step.link}>{o.next_step.label}</Link>
                      </Button>
                    ) : null}
                    {canManage && o.outcome !== "not_applicable" && o.outcome !== "satisfied" ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setReason("");
                          setDeclining(o);
                        }}
                      >
                        Does not apply
                      </Button>
                    ) : null}
                    {canManage && o.outcome === "not_applicable" ? (
                      <Button size="sm" variant="ghost" loading={again.isPending} onClick={() => again.mutate(o.code)}>
                        Applies again
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </section>
        ) : null,
      )}

      <Dialog open={declining !== null} onOpenChange={(v) => (v ? null : setDeclining(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Why does {declining?.code} not apply?</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <TextArea label="Reason" rows={4} value={reason} onChange={(e) => setReason(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDeclining(null)}>
              Cancel
            </Button>
            <Button
              disabled={!reason.trim()}
              loading={decline.isPending}
              onClick={() => declining && decline.mutate(declining.code)}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={tagging !== null} onOpenChange={(v) => (v ? null : setTagging(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>{tagging?.name}</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <SearchableSelect
              aria-label="Evidence"
              value={pick}
              onChange={setPick}
              placeholder="Choose the evidence that is this record"
              options={evidence.map((e) => ({ value: e.id, label: e.title }))}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setTagging(null)}>
              Cancel
            </Button>
            <Button disabled={!pick} loading={tag.isPending} onClick={() => tag.mutate()}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
