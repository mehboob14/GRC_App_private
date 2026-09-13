import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextField,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { getAssessment, issueQuestionnaire, openReassessment, scoreAssessment } from "../api";
import type {
  Assessment,
  AssessmentResponse,
  AssessmentSummary,
  Contact,
  VendorDetail,
} from "../types";
import {
  ANSWER_META,
  ASSESSMENT_KIND_LABEL,
  ASSESSMENT_STATUS_META,
  fmtDate,
  GRADE_META,
} from "../tokens";
import { Panel } from "./panel";

/**
 * The questionnaire side of a vendor: send one, watch it come back, score it,
 * and — on a reassessment — read it as a diff against what they said last time.
 */
export function AssessmentsPanel({
  vendor,
  engagementId,
  canAssess,
  onApply,
}: {
  vendor: VendorDetail;
  engagementId: string | null;
  canAssess: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [issuing, setIssuing] = useState(false);
  const [issued, setIssued] = useState<{ url: string; email: string; count: number } | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  const engagement = vendor.engagements.find((e) => e.id === engagementId) ?? null;
  const tiered = vendor.tierings.some((t) => t.engagement_id === engagementId);
  const portalContact =
    vendor.contacts.find((c) => c.contact_type === "portal") ?? vendor.contacts[0] ?? null;

  const assessments = useMemo(
    () =>
      vendor.assessments.filter((a) => engagementId === null || a.engagement_id === engagementId),
    [vendor.assessments, engagementId],
  );

  /** The cycle before the one being opened, so a reassessment can be read as a diff. */
  const priorOf = (a: AssessmentSummary): AssessmentSummary | null =>
    assessments.find((other) => other.cycle === a.cycle - 1 && other.status === "scored") ?? null;

  const reassess = useMutation({
    mutationFn: () => openReassessment(vendor.id, engagementId!),
    onSuccess: (next) => {
      onApply(next);
      void queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast({ title: "Reassessment cycle opened", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "reassessment"), tone: "danger" }),
  });

  if (!engagement) {
    return (
      <Panel title="Assessments">
        <p className="text-body-md text-text-secondary">
          Add an engagement to send questionnaires.
        </p>
      </Panel>
    );
  }

  const opened = assessments.find((a) => a.id === openId) ?? null;

  return (
    <>
      <Panel
        title="Assessments"
        count={assessments.length || undefined}
        description={engagement.name}
        action={
          canAssess ? (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                loading={reassess.isPending}
                onClick={() => reassess.mutate()}
                disabled={!tiered || assessments.length === 0}
              >
                Reassess
              </Button>
              <Button
                size="sm"
                onClick={() => setIssuing(true)}
                disabled={!tiered || !portalContact}
              >
                <Icon name="upload" className="size-4" />
                Send questionnaire
              </Button>
            </div>
          ) : null
        }
      >
        {!tiered ? (
          <p className="text-body-md text-text-secondary">
            Tier the engagement first. The tier sets which questions apply.
          </p>
        ) : !portalContact ? (
          <div className="rounded-md border border-status-warning-border bg-status-warning-bg p-3.5">
            <p className="flex items-center gap-1.5 text-label-sm text-status-warning-text">
              <Icon name="alert" className="size-4 shrink-0" />
              No contact to send to
            </p>
            <p className="mt-1 text-body-sm text-text-secondary">
              Add a vendor contact with an email address first.
            </p>
          </div>
        ) : assessments.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            No questionnaires sent yet.
          </p>
        ) : (
          <ul className="space-y-2">
            {assessments.map((a) => (
              <li key={a.id}>
                <AssessmentRow
                  assessment={a}
                  prior={priorOf(a)}
                  onOpen={() => setOpenId(a.id)}
                />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <IssueDialog
        open={issuing}
        onOpenChange={setIssuing}
        vendorId={vendor.id}
        engagementId={engagement.id}
        contacts={vendor.contacts}
        defaultContactId={portalContact?.id ?? null}
        onIssued={(result) => {
          setIssued({
            url: result.portal_url,
            email: result.contact_email,
            count: result.question_count,
          });
          setIssuing(false);
          void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
        }}
      />

      <PortalLinkDialog issued={issued} onClose={() => setIssued(null)} />

      {opened ? (
        <AssessmentDialog
          vendorId={vendor.id}
          assessment={opened}
          prior={priorOf(opened)}
          canAssess={canAssess}
          onClose={() => setOpenId(null)}
        />
      ) : null}
    </>
  );
}

function AssessmentRow({
  assessment: a,
  prior,
  onOpen,
}: {
  assessment: AssessmentSummary;
  prior: AssessmentSummary | null;
  onOpen: () => void;
}) {
  const status = ASSESSMENT_STATUS_META[a.status] ?? {
    label: a.status,
    family: "neutral" as const,
  };
  const delta =
    prior && a.residual_score !== null && prior.residual_score !== null
      ? Math.round((a.residual_score - prior.residual_score) * 100) / 100
      : null;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full flex-wrap items-center gap-3 rounded-md border border-border bg-surface-primary p-3.5 text-left transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
    >
      <div className="min-w-0 flex-1">
        <p className="text-body-md font-semibold text-text-primary">
          {ASSESSMENT_KIND_LABEL[a.kind] ?? a.kind} · cycle {a.cycle}
        </p>
        <p className="mt-0.5 text-caption text-text-subtle">
          {a.answered_count} of {a.question_count} answered
          {a.due_date ? ` · due ${fmtDate(a.due_date)}` : ""}
          {a.submitted_at ? ` · submitted ${fmtDate(a.submitted_at)}` : ""}
        </p>
      </div>
      {delta !== null && delta !== 0 ? (
        // Residual risk: down is better, so a fall is the success colour.
        <span
          className={cn(
            "tabular inline-flex items-center gap-1 text-body-sm",
            delta < 0 ? "text-status-success-text" : "text-status-danger-text",
          )}
        >
          <Icon
            name="arrowup"
            className={cn("size-3.5", delta < 0 && "rotate-180")}
            aria-hidden
          />
          {Math.abs(delta)} vs cycle {prior!.cycle}
        </span>
      ) : null}
      <StatusPill status={status.family} label={status.label} kind="inline" />
      {a.grade ? (
        <StatusPill
          status={GRADE_META[a.grade]?.family ?? "neutral"}
          label={`Grade ${a.grade}${a.residual_score !== null ? ` · ${a.residual_score}` : ""}`}
        />
      ) : null}
      <Icon name="chevr" className="size-4 shrink-0 -rotate-90 text-text-subtle" />
    </button>
  );
}

function IssueDialog({
  open,
  onOpenChange,
  vendorId,
  engagementId,
  contacts,
  defaultContactId,
  onIssued,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  engagementId: string;
  contacts: Contact[];
  defaultContactId: string | null;
  onIssued: (result: { portal_url: string; contact_email: string; question_count: number }) => void;
}) {
  const { toast } = useToast();
  const [contactId, setContactId] = useState(defaultContactId ?? "");
  const [dueDate, setDueDate] = useState("");

  const issue = useMutation({
    mutationFn: () =>
      issueQuestionnaire(vendorId, engagementId, {
        contact_id: contactId || null,
        due_date: dueDate || null,
      }),
    onSuccess: onIssued,
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Send questionnaire</DialogTitle>
          <DialogDescription>No vendor sign-in needed. Resending revokes the old link.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            issue.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <SelectField label="Send to">
              <Select value={contactId} onValueChange={setContactId}>
                <SelectTrigger aria-label="Contact" />
                <SelectContent>
                  {contacts.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                      {c.email ? ` · ${c.email}` : " · No email"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextField
              label="Due date"
              optional
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              hint="Shown to the vendor. Does not close the link."
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={issue.isPending} disabled={!contactId}>
              Create link
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * The link is shown exactly once.
 *
 * Only a hash of the token is stored, so there is no second chance to read it —
 * which is why this dialog says plainly what happens if it is closed.
 */
function PortalLinkDialog({
  issued,
  onClose,
}: {
  issued: { url: string; email: string; count: number } | null;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  return (
    <Dialog open={issued !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Send this link to {issued?.email}</DialogTitle>
          <DialogDescription>
            {issued?.count} questions in scope. Anyone with the link can answer.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="rounded-md border border-border bg-surface-sunken p-3">
            <p className="break-all font-mono text-body-sm text-text-primary">{issued?.url}</p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                void navigator.clipboard
                  .writeText(issued?.url ?? "")
                  .then(() => {
                    setCopied(true);
                    toast({ title: "Link copied", tone: "success" });
                  })
                  .catch(() =>
                    toast({
                      title: "Copy blocked. Select the link and copy it manually.",
                      tone: "danger",
                    }),
                  );
              }}
            >
              <Icon name={copied ? "check" : "link"} className="size-4" />
              {copied ? "Copied" : "Copy link"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                const subject = encodeURIComponent("Security questionnaire");
                const body = encodeURIComponent(
                  `Please complete our security questionnaire:\n\n${issued?.url ?? ""}`,
                );
                window.location.href = `mailto:${issued?.email ?? ""}?subject=${subject}&body=${body}`;
              }}
            >
              Open in email
            </Button>
          </div>
          <p className="mt-3 flex items-start gap-1.5 rounded-md border border-status-warning-border bg-status-warning-bg p-3 text-body-sm text-status-warning-text">
            <Icon name="alert" className="mt-px size-4 shrink-0" />
            Shown only once. If lost, issue a new link, which revokes this one.
          </p>
        </DialogBody>
        <DialogFooter>
          <Button onClick={onClose}>I copied it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AssessmentDialog({
  vendorId,
  assessment,
  prior,
  canAssess,
  onClose,
}: {
  vendorId: string;
  assessment: AssessmentSummary;
  prior: AssessmentSummary | null;
  canAssess: boolean;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const key = ["vendor-assessment", assessment.id];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getAssessment(vendorId, assessment.id),
  });
  // The previous cycle's answers, so a reassessment reads as a diff rather than
  // a fresh form somebody has to compare by memory.
  const priorQuery = useQuery({
    queryKey: ["vendor-assessment", prior?.id],
    queryFn: () => getAssessment(vendorId, prior!.id),
    enabled: prior !== null,
  });

  const score = useMutation({
    mutationFn: () => scoreAssessment(vendorId, assessment.id),
    onSuccess: (next) => {
      queryClient.setQueryData(key, next);
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendorId] });
      void queryClient.invalidateQueries({ queryKey: ["vendor-findings"] });
      toast({ title: `Scored: grade ${next.grade ?? "none"}`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "assessment"), tone: "danger" }),
  });

  const a = query.data;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="lg" scrollBody>
        <DialogHeader>
          <DialogTitle>
            {ASSESSMENT_KIND_LABEL[assessment.kind] ?? assessment.kind} · cycle {assessment.cycle}
          </DialogTitle>
          <DialogDescription>
            {a
              ? `${a.answered_count} of ${a.question_count} answered · ${a.missing_evidence_count} still missing evidence`
              : "Loading answers…"}
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          {query.isError ? (
            <p className="text-body-md text-status-danger-text">
              {describeError(query.error, "assessment").message}
            </p>
          ) : !a ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <AssessmentBody assessment={a} prior={priorQuery.data ?? null} />
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          {a && canAssess && a.status !== "scored" ? (
            <Button
              loading={score.isPending}
              onClick={() => score.mutate()}
              disabled={a.answered_count === 0}
            >
              Score
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** A question whose answer moved between cycles, and which way it moved. */
type Change = {
  code: string;
  body: string;
  from: string | null;
  to: string | null;
  /** True when the new answer is a weaker one — the direction that costs score. */
  worse: boolean;
};

const ANSWER_RANK: Record<string, number> = { yes: 3, partial: 2, no: 1, na: 0 };

function diff(current: Assessment, prior: Assessment | null): Change[] {
  if (!prior) return [];
  const before = new Map(prior.responses.map((r) => [r.question_code, r]));
  return current.responses
    .filter((r) => {
      const was = before.get(r.question_code);
      return was !== undefined && was.answer !== r.answer;
    })
    .map((r) => {
      const was = before.get(r.question_code)!;
      return {
        code: r.question_code,
        body: r.body,
        from: was.answer,
        to: r.answer,
        worse: (ANSWER_RANK[r.answer ?? "na"] ?? 0) < (ANSWER_RANK[was.answer ?? "na"] ?? 0),
      };
    });
}

function AssessmentBody({
  assessment: a,
  prior,
}: {
  assessment: Assessment;
  prior: Assessment | null;
}) {
  const changes = useMemo(() => diff(a, prior), [a, prior]);
  const priorByCode = useMemo(
    () => new Map((prior?.responses ?? []).map((r) => [r.question_code, r])),
    [prior],
  );

  const byDomain = a.responses.reduce<Record<string, AssessmentResponse[]>>((acc, r) => {
    (acc[r.domain_label] ??= []).push(r);
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      {prior ? <WhatChanged current={a} prior={prior} changes={changes} /> : null}

      {a.score_steps.length > 0 ? (
        <div className="rounded-md border border-border bg-surface-sunken p-3.5">
          <p className="type-overline">Score breakdown</p>
          <ul className="mt-2 space-y-1.5">
            {a.score_steps.map((step) => (
              <li key={step.label} className="flex items-baseline justify-between gap-3">
                <span className="min-w-0">
                  <span className="text-body-sm text-text-primary">{step.label}</span>
                  {step.detail ? (
                    <span className="ml-1.5 text-caption text-text-subtle">{step.detail}</span>
                  ) : null}
                </span>
                <span className="tabular shrink-0 text-body-sm font-semibold text-text-primary">
                  {step.value}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {Object.entries(byDomain).map(([domain, rows]) => {
        const scores = a.domain_scores[rows[0].domain];
        return (
          <div key={domain}>
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-display text-title-sm text-text-primary">{domain}</h3>
              {scores ? (
                <span className="tabular text-caption text-text-subtle">
                  residual {scores.residual} · {scores.answered} answered
                </span>
              ) : null}
            </div>
            <ul className="mt-2 divide-y divide-border">
              {rows.map((r) => (
                <ResponseRow
                  key={r.id}
                  response={r}
                  previous={prior ? (priorByCode.get(r.question_code) ?? null) : undefined}
                />
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

/**
 * The reassessment read: what moved, which way, and what it cost.
 *
 * A reassessment that only shows this cycle's answers makes the reviewer do the
 * comparison in their head against a questionnaire they read a year ago. The
 * delta and its cause are the whole point of asking again.
 */
function WhatChanged({
  current,
  prior,
  changes,
}: {
  current: Assessment;
  prior: Assessment;
  changes: Change[];
}) {
  const delta =
    current.residual_score !== null && prior.residual_score !== null
      ? Math.round((current.residual_score - prior.residual_score) * 100) / 100
      : null;
  const worse = changes.filter((c) => c.worse);
  const better = changes.filter((c) => !c.worse);

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-3.5">
      <p className="type-overline">Changes since cycle {prior.cycle}</p>

      {delta === null ? (
        <p className="mt-2 text-body-sm text-text-subtle">
          {current.status === "scored"
            ? "The previous cycle was not scored."
            : "Score this cycle to compare."}
        </p>
      ) : (
        <p className="mt-2 text-body-md text-text-primary">
          Residual risk{" "}
          <span
            className={cn(
              "tabular font-semibold",
              delta === 0
                ? "text-text-primary"
                : delta < 0
                  ? "text-status-success-text"
                  : "text-status-danger-text",
            )}
          >
            {delta === 0 ? "did not move" : delta < 0 ? `fell ${Math.abs(delta)}` : `rose ${delta}`}
          </span>{" "}
          to {current.residual_score}
          {prior.grade && current.grade && prior.grade !== current.grade ? (
            <>
              , and the grade went from {prior.grade} to {current.grade}
            </>
          ) : null}
          .
        </p>
      )}

      {changes.length === 0 ? (
        <p className="mt-1 text-body-sm text-text-subtle">
          No answers changed.
        </p>
      ) : (
        <>
          <p className="mt-1 text-body-sm text-text-subtle">
            {changes.length} of {current.question_count} answers moved
            {worse.length > 0 ? `: ${worse.length} weaker` : ""}
            {better.length > 0 ? `${worse.length > 0 ? "," : ":"} ${better.length} stronger` : ""}.
          </p>
          <ul className="mt-2 space-y-1.5">
            {[...worse, ...better].slice(0, 8).map((c) => (
              <li key={c.code} className="flex items-start gap-2">
                <Icon
                  name="arrowup"
                  className={cn(
                    "mt-0.5 size-3.5 shrink-0",
                    c.worse ? "text-status-danger-base" : "rotate-180 text-status-success-base",
                  )}
                  aria-hidden
                />
                <span className="min-w-0 text-body-sm text-text-secondary">
                  <span className="font-mono text-caption text-text-subtle">{c.code}</span>{" "}
                  {c.body}
                  <span className="ml-1.5 whitespace-nowrap">
                    <span className="text-text-subtle line-through">
                      {c.from ? (ANSWER_META[c.from]?.label ?? c.from) : "unanswered"}
                    </span>{" "}
                    → <span className="font-semibold">{c.to ? (ANSWER_META[c.to]?.label ?? c.to) : "unanswered"}</span>
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {changes.length > 8 ? (
            <p className="mt-1.5 text-caption text-text-subtle">
              {changes.length - 8} more marked Changed below.
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

function ResponseRow({
  response: r,
  previous,
}: {
  response: AssessmentResponse;
  /** The same question last cycle. `undefined` means this is not a reassessment. */
  previous?: AssessmentResponse | null;
}) {
  const answer = r.answer ? ANSWER_META[r.answer] : null;
  const changed = previous !== undefined && previous !== null && previous.answer !== r.answer;

  return (
    <li className="py-2.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-body-md text-text-primary">{r.body}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-caption text-text-subtle">
            <span className="font-mono">{r.question_code}</span>
            {r.non_negotiable ? (
              <Tooltip content="A weak answer here caps the whole grade">
                <span>
                  <Badge variant="statusFail">Non-negotiable</Badge>
                </span>
              </Tooltip>
            ) : null}
            {r.critical_control ? <Badge variant="countWarn">Critical control</Badge> : null}
            {r.evidence_required ? (
              <Badge variant={r.evidence_id ? "statusPass" : "count"}>
                {r.evidence_id ? "Evidence attached" : "Evidence missing"}
              </Badge>
            ) : null}
            {r.framework_refs.map((ref) => (
              <Badge key={ref} variant="neutral">
                {ref}
              </Badge>
            ))}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {changed && previous ? (
            <span className="text-caption text-text-subtle line-through">
              {previous.answer ? (ANSWER_META[previous.answer]?.label ?? previous.answer) : "Unanswered"}
            </span>
          ) : null}
          {answer ? (
            <Badge variant={answer.variant}>{answer.label}</Badge>
          ) : (
            <span className="text-caption text-text-subtle">Unanswered</span>
          )}
          {changed ? <Badge variant="role">Changed</Badge> : null}
        </div>
      </div>
      {r.implementation_notes ? (
        <p className="mt-1.5 whitespace-pre-line text-body-sm text-text-secondary">
          {r.implementation_notes}
        </p>
      ) : null}
      {r.na_justification ? (
        <p className="mt-1.5 text-body-sm text-text-subtle">Not applicable: {r.na_justification}</p>
      ) : null}
    </li>
  );
}
