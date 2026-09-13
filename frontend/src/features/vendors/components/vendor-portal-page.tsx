import { useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, BrandMark, Button, Icon, Skeleton, TextArea } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  answerPortalQuestion,
  getPortal,
  PortalError,
  submitPortal,
  uploadPortalEvidence,
} from "../api";
import type { Portal, PortalQuestion } from "../types";
import { fmtDate } from "../tokens";

const ANSWERS = [
  { value: "yes", label: "Yes" },
  { value: "partial", label: "Partially" },
  { value: "no", label: "No" },
  { value: "na", label: "Not applicable" },
];

/** The server's rule: a yes or a partial claims the control, so it owes its document. */
const CLAIMS_A_CONTROL = new Set(["yes", "partial"]);
const owesDocument = (q: PortalQuestion) =>
  q.evidence_required && q.answer !== null && CLAIMS_A_CONTROL.has(q.answer) && !q.has_evidence;

/** What the file store accepts. The server sniffs the bytes; this only filters the picker. */
const ACCEPT = ".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.xlsx,.pptx,.txt,.csv,.json";

/**
 * The page a third party sees.
 *
 * It is the only unauthenticated screen in the product, and it is written for
 * somebody who has never heard of Verity: no jargon, no navigation, no account.
 * Every failure — a bad link, an expired one, a revoked one, too many attempts —
 * comes back from the API as one indistinguishable error on purpose, so this
 * page never tries to explain which.
 *
 * It lives outside `RequireAuth` and never calls `apiFetch`: that client
 * attaches whatever bearer token is in storage and clears the session on a 401,
 * so an internal user opening a portal link would be signed out by somebody
 * else's expired token.
 */
export function VendorPortalPage() {
  const { token = "" } = useParams();
  const queryClient = useQueryClient();
  const key = ["vendor-portal", token];

  const query = useQuery({
    queryKey: key,
    queryFn: () => getPortal(token),
    retry: false,
  });

  const apply = (next: Portal) => queryClient.setQueryData(key, next);

  if (query.isLoading) {
    return (
      <PortalShell>
        <Skeleton className="h-64 w-full" />
      </PortalShell>
    );
  }

  if (query.isError) {
    const message =
      query.error instanceof PortalError
        ? query.error.message
        : "This questionnaire link is no longer valid. Ask your contact to send a new one.";
    return (
      <PortalShell>
        <div className="rounded-lg border border-border bg-surface-primary p-8 text-center">
          <Icon name="alert" className="mx-auto size-8 text-status-warning-base" />
          <h1 className="mt-3 font-display text-heading-sm text-text-primary">
            We could not open this questionnaire
          </h1>
          <p className="mx-auto mt-2 max-w-md text-body-md text-text-secondary">{message}</p>
        </div>
      </PortalShell>
    );
  }

  const portal = query.data!;
  return (
    <PortalShell>
      <PortalBody token={token} portal={portal} onApply={apply} />
    </PortalShell>
  );
}

function PortalShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-page">
      <header className="border-b border-border bg-surface-primary">
        <div className="mx-auto flex max-w-3xl items-center gap-2.5 px-5 py-3.5">
          <BrandMark size={26} />
          <span className="font-display text-title-md text-text-primary">Security review</span>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-6">{children}</main>
      <footer className="mx-auto max-w-3xl px-5 pb-8">
        <p className="text-caption text-text-subtle">
          Only the sender sees your answers. Anyone with this link can answer for you, so do not
          forward it.
        </p>
      </footer>
    </div>
  );
}

function PortalBody({
  token,
  portal,
  onApply,
}: {
  token: string;
  portal: Portal;
  onApply: (next: Portal) => void;
}) {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const submitted = portal.submitted_at !== null;

  const byDomain = useMemo(() => {
    return portal.questions.reduce<Record<string, PortalQuestion[]>>((acc, q) => {
      (acc[q.domain_label] ??= []).push(q);
      return acc;
    }, {});
  }, [portal.questions]);

  const unanswered = portal.question_count - portal.answered_count;
  const missingDocs = portal.questions.filter(owesDocument).length;
  const ready = unanswered === 0 && missingDocs === 0;
  // In page order, so "Next" walks down the page rather than jumping around it.
  const next = Object.values(byDomain)
    .flat()
    .find((q) => q.answer === null || owesDocument(q));

  const goTo = (id: string) =>
    document.getElementById(`q-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });

  const submit = useMutation({
    mutationFn: () => submitPortal(token),
    onSuccess: (next) => {
      setSubmitError(null);
      onApply(next);
    },
    onError: (e: unknown) =>
      setSubmitError(
        e instanceof PortalError ? e.message : "We could not submit your answers. Try again.",
      ),
  });

  if (submitted) {
    return (
      <div className="rounded-lg border border-status-success-border bg-status-success-bg p-8 text-center">
        <Icon name="check" className="mx-auto size-8 text-status-success-base" />
        <h1 className="mt-3 font-display text-heading-sm text-status-success-text">
          Thank you, your answers are in
        </h1>
        <p className="mx-auto mt-2 max-w-md text-body-md text-text-secondary">
          {portal.organisation} received {portal.answered_count} answers on{" "}
          {fmtDate(portal.submitted_at)}. You can close this page.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="rounded-lg border border-border bg-surface-primary p-5">
        <h1 className="font-display text-heading-sm text-text-primary">
          {portal.organisation} has some questions about {portal.vendor_name}
        </h1>
        <p className="mt-2 text-body-md text-text-secondary">
          {portal.question_count} questions. Answers save as you go.
          {portal.due_date ? ` Due by ${fmtDate(portal.due_date)}.` : ""}
        </p>

        <div className="mt-4">
          <div className="flex items-baseline justify-between">
            <span className="text-label-sm text-text-secondary">
              {portal.answered_count} of {portal.question_count} answered
            </span>
            <span className="tabular text-caption text-text-subtle">
              {Math.round((portal.answered_count / Math.max(1, portal.question_count)) * 100)}%
            </span>
          </div>
          <span className="mt-1.5 block h-2 rounded-full bg-surface-sunken">
            <span
              className="block h-2 rounded-full bg-action-accent transition-all duration-250 ease-state"
              style={{
                width: `${(portal.answered_count / Math.max(1, portal.question_count)) * 100}%`,
              }}
            />
          </span>
        </div>
      </div>

      <div className="mt-5 space-y-5">
        {Object.entries(byDomain).map(([domain, questions]) => (
          <section key={domain} className="rounded-lg border border-border bg-surface-primary p-5">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-display text-title-md text-text-primary">{domain}</h2>
              <span className="tabular text-caption text-text-subtle">
                {questions.filter((q) => q.answer !== null).length}/{questions.length}
              </span>
            </div>
            <ul className="mt-3 divide-y divide-border">
              {questions.map((q) => (
                <QuestionRow key={q.id} token={token} question={q} onApply={onApply} />
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* Stays in view: what is left, a way to reach it, and the send button,
          without scrolling back to the top of a forty question page. */}
      <div className="sticky bottom-3 z-sticky-page mt-5 rounded-lg border border-border bg-surface-primary p-3 shadow-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="min-w-0 flex-1">
            {ready ? (
              <p className="flex items-center gap-1.5 text-label-md text-status-success-text">
                <Icon name="check" className="size-4" />
                Ready to send
              </p>
            ) : (
              <p className="flex flex-wrap items-center gap-2 text-label-md text-text-primary">
                {unanswered > 0 ? (
                  <Badge variant="neutral">
                    {unanswered} {unanswered === 1 ? "question" : "questions"} left
                  </Badge>
                ) : null}
                {missingDocs > 0 ? (
                  <Badge variant="countWarn">
                    {missingDocs} {missingDocs === 1 ? "document" : "documents"} missing
                  </Badge>
                ) : null}
              </p>
            )}
            {submitError ? (
              <p role="alert" className="mt-1 text-body-sm text-status-danger-text">
                {submitError}
              </p>
            ) : (
              <p className="mt-1 text-caption text-text-subtle">Sending closes this link.</p>
            )}
          </div>
          {next ? (
            <Button variant="secondary" onClick={() => goTo(next.id)}>
              Next to do
              <Icon name="arrowr" className="size-4" />
            </Button>
          ) : null}
          <Button loading={submit.isPending} onClick={() => submit.mutate()} disabled={!ready}>
            Send answers
          </Button>
        </div>
      </div>
    </div>
  );
}

function QuestionRow({
  token,
  question: q,
  onApply,
}: {
  token: string;
  question: PortalQuestion;
  onApply: (next: Portal) => void;
}) {
  const [notes, setNotes] = useState(q.implementation_notes ?? "");
  const [naReason, setNaReason] = useState(q.na_justification ?? "");
  // "Not applicable" is refused without its reason, so picking it opens the
  // reason box first and the answer saves once there is a reason to save.
  const [naOpen, setNaOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fail = (e: unknown) =>
    setError(e instanceof PortalError ? e.message : "That did not save. Try again.");

  const answer = useMutation({
    mutationFn: (value: string) =>
      answerPortalQuestion(token, {
        question_id: q.id,
        answer: value,
        implementation_notes: notes.trim() || null,
        na_justification: value === "na" ? naReason.trim() || null : null,
      }),
    onSuccess: (next) => {
      setError(null);
      setNaOpen(false);
      onApply(next);
    },
    onError: fail,
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadPortalEvidence(token, q.id, file),
    onSuccess: (next) => {
      setError(null);
      onApply(next);
    },
    onError: fail,
  });

  const choice = naOpen ? "na" : q.answer;
  const saveNa = () => {
    const reason = naReason.trim();
    if (reason && (q.answer !== "na" || reason !== (q.na_justification ?? ""))) answer.mutate("na");
  };

  return (
    <li id={`q-${q.id}`} className="scroll-mt-6 py-4">
      <p className="text-body-lg text-text-primary">{q.body}</p>

      <div
        className="mt-2.5 flex flex-wrap gap-2"
        role="radiogroup"
        aria-label={`Answer for ${q.code}`}
      >
        {ANSWERS.map((option) => {
          const selected = choice === option.value;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={answer.isPending}
              onClick={() => {
                if (option.value !== "na") {
                  setNaOpen(false);
                  answer.mutate(option.value);
                } else if (naReason.trim()) {
                  answer.mutate("na");
                } else {
                  setError(null);
                  setNaOpen(true);
                }
              }}
              className={cn(
                "rounded-sm border px-3 py-1.5 text-label-md transition-colors duration-80 ease-state",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                selected
                  ? "border-action-accent bg-action-accent-tint text-action-accent"
                  : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {choice === "na" ? (
        <div className="mt-3">
          <TextArea
            label="Why this does not apply to you"
            value={naReason}
            onChange={(e) => setNaReason(e.target.value)}
            onBlur={saveNa}
            autoFocus={naOpen}
            rows={2}
            maxLength={4000}
          />
        </div>
      ) : q.answer !== null ? (
        <div className="mt-3">
          <TextArea
            label="How you do this"
            optional
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => {
              if (q.answer && notes !== (q.implementation_notes ?? "")) answer.mutate(q.answer);
            }}
            rows={2}
            maxLength={8000}
          />
        </div>
      ) : null}

      {q.evidence_required ? (
        <DocumentDrop
          question={q}
          owed={owesDocument(q)}
          optional={choice === "no" || choice === "na"}
          busy={upload.isPending}
          onFile={(file) => upload.mutate(file)}
        />
      ) : null}

      {error ? (
        <p role="alert" className="mt-2 text-body-sm text-status-danger-text">
          {error}
        </p>
      ) : null}
    </li>
  );
}

/**
 * Where a vendor attaches proof. Always shown on a question that asks for it,
 * before any answer is picked, so the ask and the way to meet it sit together.
 * Drop a file on it or browse; either way the server checks the file.
 */
function DocumentDrop({
  question: q,
  owed,
  optional,
  busy,
  onFile,
}: {
  question: PortalQuestion;
  /** The answer claims the control and nothing is attached yet. */
  owed: boolean;
  /** A "no" or "not applicable" claims nothing, so a document is welcome but not owed. */
  optional: boolean;
  busy: boolean;
  onFile: (file: File) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const attached = q.has_evidence;

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file && !busy) onFile(file);
      }}
      className={cn(
        "mt-3 flex items-center gap-3 rounded-md border px-3 py-2.5 transition-colors duration-80 ease-state",
        over
          ? "border-action-accent bg-action-accent-tint"
          : attached
            ? "border-status-success-border bg-status-success-bg"
            : owed
              ? "border-dashed border-status-warning-border bg-status-warning-bg"
              : "border-dashed border-border-strong bg-surface-sunken",
      )}
    >
      <Icon
        name={attached ? "check" : "doc"}
        className={cn(
          "size-5 shrink-0",
          attached
            ? "text-status-success-base"
            : owed
              ? "text-status-warning-base"
              : "text-text-subtle",
        )}
      />
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 text-label-md text-text-primary">
          {attached ? "Document attached" : "Supporting document"}
          {attached ? null : owed ? (
            <Badge variant="countWarn">Required</Badge>
          ) : (
            <Badge variant="neutral">{optional ? "Optional" : "Required"}</Badge>
          )}
        </p>
        <p className="mt-0.5 text-caption text-text-subtle">
          {attached
            ? "Sent to the reviewer. Replace it any time before you send."
            : "Drop a file or upload. PDF, Office, image or text, up to 25 MB."}
        </p>
      </div>
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        tabIndex={-1}
        aria-label={`Upload a document for ${q.code}`}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
      <Button
        variant="secondary"
        size="sm"
        className="shrink-0"
        loading={busy}
        onClick={() => input.current?.click()}
      >
        <Icon name="upload" className="size-4" />
        {attached ? "Replace" : "Upload"}
      </Button>
    </div>
  );
}
