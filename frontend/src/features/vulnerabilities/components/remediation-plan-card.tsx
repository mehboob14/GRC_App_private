import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Icon, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  applyRemediationPlan,
  approveRemediationPlan,
  cancelRemediationPlan,
  generateRemediationPlan,
  getRemediationPlan,
  verifyRemediationPlan,
} from "../api";
import type { BadgeVariant } from "@/components/ui";
import type { RemediationPlan, RemediationStatus } from "../types";
import { ReasonDialog } from "./reason-dialog";

const STATUS: Record<RemediationStatus, { label: string; variant: BadgeVariant }> = {
  preview: { label: "Preview", variant: "neutral" },
  recommended: { label: "Recommended", variant: "statusReview" },
  approved: { label: "Approved", variant: "statusPending" },
  applied: { label: "Applied", variant: "statusPending" },
  verified: { label: "Verified", variant: "statusPass" },
  failed: { label: "Failed", variant: "statusFail" },
  cancelled: { label: "Cancelled", variant: "neutral" },
};

const FIX_LABEL: Record<string, string> = {
  patch: "Patch",
  config: "Config change",
  script: "Script",
  mitigation: "Mitigation",
};

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "No date";

export function RemediationPlanCard({ instanceId }: { instanceId: string }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const key = ["remediation-plan", instanceId];
  const planQuery = useQuery({
    queryKey: key,
    queryFn: () => getRemediationPlan(instanceId),
  });
  const { data: plan, isLoading } = planQuery;
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [showSteps, setShowSteps] = useState(false);

  // apply/verify change the finding's state, so refresh the instance + lists too.
  const settle = (next: RemediationPlan, touchesInstance = false) => {
    queryClient.setQueryData(key, next);
    if (touchesInstance) {
      queryClient.invalidateQueries({ queryKey: ["vulnerability", instanceId] });
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      queryClient.invalidateQueries({ queryKey: ["vuln-kpis"] });
    }
  };

  const fail = (e: unknown) =>
    toast({ title: errorToast(e, "remediation plan"), tone: "danger" });

  const generate = useMutation({
    mutationFn: () => generateRemediationPlan(instanceId),
    onSuccess: (p) => {
      settle(p);
      toast({ title: "Remediation plan generated", tone: "success" });
    },
    onError: fail,
  });
  const approve = useMutation({
    mutationFn: () => approveRemediationPlan(instanceId),
    onSuccess: (p) => settle(p),
    onError: fail,
  });
  const applyPlan = useMutation({
    mutationFn: () => applyRemediationPlan(instanceId),
    onSuccess: (p) => {
      settle(p, true);
      toast({ title: "Applied (simulated), finding moved to pending retest", tone: "success" });
    },
    onError: fail,
  });
  const verify = useMutation({
    mutationFn: (evidence: string) => verifyRemediationPlan(instanceId, evidence),
    onSuccess: (p) => {
      settle(p, true);
      toast({ title: "Verified, finding closed as fixed", tone: "success" });
    },
    onError: fail,
  });
  const cancel = useMutation({
    mutationFn: (reason: string) => cancelRemediationPlan(instanceId, reason),
    onSuccess: (p) => settle(p),
    onError: fail,
  });

  const busy =
    generate.isPending ||
    approve.isPending ||
    applyPlan.isPending ||
    verify.isPending ||
    cancel.isPending;

  // A failed load must not sit on "Loading…" forever, so check isError first.
  if (planQuery.isError) {
    const e = describeError(planQuery.error, "remediation plan");
    return (
      <div className="rounded-lg border border-border bg-surface-primary p-5">
        <h2 className="font-display text-title-sm text-text-primary">Remediation plan</h2>
        <p className="mt-2 text-body-sm text-status-danger-text">{e.message}</p>
        {e.retryable ? (
          <Button
            variant="secondary"
            size="sm"
            className="mt-3"
            onClick={() => void planQuery.refetch()}
          >
            Try again
          </Button>
        ) : null}
      </div>
    );
  }

  if (isLoading || !plan) {
    return (
      <div className="rounded-lg border border-border bg-surface-primary p-5">
        <h2 className="font-display text-title-sm text-text-primary">Remediation plan</h2>
        <p className="mt-2 text-body-sm text-text-subtle">Loading…</p>
      </div>
    );
  }

  const s = STATUS[plan.status];
  const isPreview = plan.status === "preview";
  const closed = plan.status === "verified" || plan.status === "cancelled" || plan.status === "failed";

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon name="shield" className="size-4 text-text-subtle" />
          <h2 className="font-display text-title-sm text-text-primary">Remediation plan</h2>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant="neutral">{FIX_LABEL[plan.fix_type] ?? plan.fix_type}</Badge>
          <Badge variant={s.variant}>{s.label}</Badge>
          {plan.source === "ai" ? <Badge variant="role">AI draft</Badge> : null}
        </div>
      </div>

      {isPreview ? (
        <p className="mb-3 text-caption text-text-subtle">
          A suggested plan from what we know. Generate it to start the approve → apply → verify
          workflow.
        </p>
      ) : null}

      <p className="text-body-sm text-text-secondary">{plan.summary}</p>

      {plan.triggers.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {plan.triggers.map((t) => (
            <span
              key={t}
              className="rounded-full bg-status-danger-bg px-2 py-0.5 text-caption text-status-danger-text"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setShowSteps((v) => !v)}
        className="mt-3 flex items-center gap-1 text-body-sm text-text-link"
      >
        <Icon name={showSteps ? "chev" : "chevr"} className="size-4" />
        {showSteps ? "Hide steps" : "Show fix steps"}
      </button>
      {showSteps ? (
        <div className="mt-2 space-y-3">
          <pre className="whitespace-pre-wrap rounded-md border border-border bg-surface-hover px-3 py-2.5 font-mono text-caption text-text-secondary">
            {plan.fix_artifact}
          </pre>
          <div>
            <p className="text-caption font-semibold text-text-subtle">Why now</p>
            <p className="mt-0.5 text-body-sm text-text-secondary">{plan.rationale}</p>
          </div>
          {plan.rollback_plan ? (
            <div>
              <p className="text-caption font-semibold text-text-subtle">Rollback</p>
              <p className="mt-0.5 text-body-sm text-text-secondary">{plan.rollback_plan}</p>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* lifecycle status detail */}
      {plan.status === "approved" && plan.change_window_end ? (
        <p className="mt-3 text-caption text-text-subtle">
          Approved{plan.approved_by_name ? ` by ${plan.approved_by_name}` : ""} · change window
          closes {fmt(plan.change_window_end)}
        </p>
      ) : null}
      {plan.status === "applied" && plan.execution_log ? (
        <p className="mt-3 rounded-md bg-surface-hover px-3 py-2 text-caption text-text-secondary">
          {plan.execution_log}
        </p>
      ) : null}
      {plan.status === "verified" ? (
        <div className="mt-3 rounded-md bg-status-success-bg px-3 py-2">
          <p className="text-caption font-semibold text-status-success-text">
            Verified{plan.verified_by_name ? ` by ${plan.verified_by_name}` : ""} · {fmt(plan.verified_at)}
          </p>
          {plan.verification_evidence ? (
            <p className="mt-0.5 text-caption text-text-secondary">{plan.verification_evidence}</p>
          ) : null}
        </div>
      ) : null}
      {plan.status === "cancelled" && plan.cancelled_reason ? (
        <p className="mt-3 text-caption text-text-subtle">Cancelled: {plan.cancelled_reason}</p>
      ) : null}
      {plan.status === "failed" && plan.failure_reason ? (
        <p className="mt-3 text-caption text-status-danger-text">{plan.failure_reason}</p>
      ) : null}

      {/* actions */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {isPreview || plan.status === "cancelled" || plan.status === "failed" ? (
          <Button variant="primary" size="sm" loading={generate.isPending} onClick={() => generate.mutate()}>
            Generate plan
          </Button>
        ) : null}
        {plan.status === "recommended" ? (
          <>
            <Button variant="primary" size="sm" loading={approve.isPending} onClick={() => approve.mutate()}>
              Approve
            </Button>
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => generate.mutate()}>
              Regenerate
            </Button>
          </>
        ) : null}
        {plan.status === "approved" ? (
          <Button variant="primary" size="sm" loading={applyPlan.isPending} onClick={() => applyPlan.mutate()}>
            <Icon name="shield" className="size-4" />
            Apply (simulated)
          </Button>
        ) : null}
        {plan.status === "applied" ? (
          <Button
            variant="primary"
            size="sm"
            loading={verify.isPending}
            onClick={() => setVerifyOpen(true)}
          >
            <Icon name="check" className="size-4" />
            Verify fixed
          </Button>
        ) : null}
        {!isPreview && !closed ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={() => setCancelOpen(true)}
          >
            Cancel plan
          </Button>
        ) : null}
        {plan.status === "verified" ? (
          <Button variant="secondary" size="sm" loading={generate.isPending} onClick={() => generate.mutate()}>
            New plan
          </Button>
        ) : null}
      </div>
      <ReasonDialog
        open={verifyOpen}
        onOpenChange={setVerifyOpen}
        title="Verify the fix"
        label="Evidence the fix worked"
        placeholder="Retest result, scan output, ticket reference…"
        confirmLabel="Mark verified"
        required
        loading={verify.isPending}
        onConfirm={(note) => {
          if (note) verify.mutate(note);
          setVerifyOpen(false);
        }}
      />

      <ReasonDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title="Cancel this plan"
        label="Why is it being cancelled?"
        placeholder="e.g. superseded by a vendor patch"
        confirmLabel="Cancel plan"
        required
        loading={cancel.isPending}
        onConfirm={(note) => {
          if (note) cancel.mutate(note);
          setCancelOpen(false);
        }}
      />

    </div>
  );
}
