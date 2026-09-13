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
import { isChoice, pickedKeys, visibleIds } from "../questionnaire-logic";
import type { AnswerValue, Portal, PortalQuestion } from "../types";
import { fmtDate } from "../tokens";
import { QuestionField } from "./question-field";

/** What the question holds right now, in its own shape. A bank row's value is its answer. */
const currentValue = (q: PortalQuestion): AnswerValue =>
  q.answered ? (q.value ?? q.answer) : null;

/** The server's rule: a document is owed once an answer that needs one is given. */
const owesDocument = (q: PortalQuestion) => {
  if (q.evidence !== "required" || q.answer_type === "file" || !q.answered || q.has_evidence) {
    return false;
  }
  if (q.evidence_on.length === 0) return true;
  return pickedKeys(currentValue(q)).some((k) => q.evidence_on.includes(k));
};

/** What the file store accepts. The server sniffs the bytes; this only filters the picker. */
const ACCEPT = ".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.xlsx,.pptx,.txt,.csv,.json";

/**
 * The page a third party sees.
 *
 * It is the only unauthenticated screen in the product, and it is written for
 * somebody who has never heard of Verity: no jargon, no navigation, no account.
 * Every failure (a bad link, an expired one, a revoked one, too many attempts)
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

  // Follow-ups open as the answers that lead to them are saved.
  const asked = useMemo(() => {
    const shown = visibleIds(
      portal.questions.map((q) => ({
        id: q.id,
        answer_type: q.answer_type,
        options: q.options,
        condition_question_id: q.condition_question_id,
        condition_option_keys: q.condition_option_keys,
      })),
      Object.fromEntries(portal.questions.map((q) => [q.id, currentValue(q)])),
    );
    return portal.questions.filter((q) => shown.has(q.id));
  }, [portal.questions]);

  const sections = useMemo(() => {
    const out: { name: string; questions: PortalQuestion[] }[] = [];
    for (const q of asked) {
      const last = out[out.length - 1];
      if (last && last.name === q.section) last.questions.push(q);
      else out.push({ name: q.section, questions: [q] });
    }
    return out;
  }, [asked]);

  const answered = asked.filter((q) => q.answered).length;
  const unanswered = asked.filter((q) => q.required && !q.answered).length;
  const missingDocs = asked.filter(owesDocument).length;
  const ready = unanswered === 0 && missingDocs === 0;
  // In page order, so "Next" walks down the page rather than jumping around it.
  const next = asked.find((q) => (q.required && !q.answered) || owesDocument(q));

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

  const percent = Math.round((answered / Math.max(1, asked.length)) * 100);
  return (
    <div>
      <div className="rounded-lg border border-border bg-surface-primary p-5">
        <h1 className="font-display text-heading-sm text-text-primary">
          {portal.organisation} has some questions about {portal.vendor_name}
        </h1>
        <p className="mt-2 text-body-md text-text-secondary">
          {asked.length} questions. Answers save as you go.
          {portal.due_date ? ` Due by ${fmtDate(portal.due_date)}.` : ""}
        </p>

        <div className="mt-4">
          <div className="flex items-baseline justify-between">
            <span className="text-label-sm text-text-secondary">
              {answered} of {asked.length} answered
            </span>
            <span className="tabular text-caption text-text-subtle">{percent}%</span>
          </div>
          <span className="mt-1.5 block h-2 rounded-full bg-surface-sunken">
            <span
              className="block h-2 rounded-full bg-action-accent transition-all duration-250 ease-state"
              style={{ width: `${percent}%` }}
            />
          </span>
        </div>
      </div>

      <div className="mt-5 space-y-5">
        {sections.map((section, index) => (
          <section
            key={`${section.name}-${index}`}
            className="rounded-lg border border-border bg-surface-primary p-5"
          >
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-display text-title-md text-text-primary">{section.name}</h2>
              <span className="tabular text-caption text-text-subtle">
                {section.questions.filter((q) => q.answered).length}/{section.questions.length}
              </span>
            </div>
            <ul className="mt-3 divide-y divide-border">
              {section.questions.map((q) => (
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
  // A pick that the server would refuse without its reason or note waits here,
  // with the box open, and saves once there is something to save with it.
  const [pending, setPending] = useState<AnswerValue | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fail = (e: unknown) =>
    setError(e instanceof PortalError ? e.message : "That did not save. Try again.");

  const shown = pending ?? currentValue(q);
  const picked = q.options.filter((o) => pickedKeys(shown).includes(o.key));
  const excluded = picked.some((o) => o.not_applicable);
  const needsNote = picked.some((o) => o.comment_required && !o.not_applicable);
  const choice = isChoice(q.answer_type);

  const answer = useMutation({
    mutationFn: (value: AnswerValue) =>
      answerPortalQuestion(token, {
        question_id: q.id,
        answer: q.answer_type === "single_choice" && typeof value === "string" ? value : null,
        value,
        implementation_notes: notes.trim() || null,
        na_justification: q.options.some((o) => o.not_applicable && pickedKeys(value).includes(o.key))
          ? naReason.trim() || null
          : null,
      }),
    onSuccess: (next) => {
      setError(null);
      setPending(null);
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

  const pick = (value: AnswerValue) => {
    setError(null);
    const opts = q.options.filter((o) => pickedKeys(value).includes(o.key));
    if (opts.some((o) => o.not_applicable) && !naReason.trim()) return setPending(value);
    if (opts.some((o) => o.comment_required && !o.not_applicable) && !notes.trim()) {
      return setPending(value);
    }
    setPending(null);
    answer.mutate(value);
  };

  // Blur on a reason or note: save the waiting pick, or update the saved one.
  const saveWithText = () => {
    const value = pending ?? currentValue(q);
    if (value === null) return;
    if (excluded && !naReason.trim()) return;
    if (needsNote && !notes.trim()) return;
    const changed =
      pending !== null ||
      notes.trim() !== (q.implementation_notes ?? "") ||
      naReason.trim() !== (q.na_justification ?? "");
    if (changed) answer.mutate(value);
  };

  return (
    <li id={`q-${q.id}`} className="scroll-mt-6 py-4">
      <p className="text-body-lg text-text-primary">
        {q.body}
        {q.required ? null : <span className="ml-1.5 text-caption text-text-faint">Optional</span>}
      </p>
      {q.help_text ? <p className="mt-0.5 text-body-sm text-text-subtle">{q.help_text}</p> : null}

      {q.answer_type === "file" ? (
        <DocumentDrop
          question={q}
          owed={q.required && !q.has_evidence}
          optional={!q.required}
          asAnswer
          busy={upload.isPending}
          onFile={(file) => upload.mutate(file)}
        />
      ) : (
        <div className="mt-2.5">
          <QuestionField
            label={q.body}
            type={q.answer_type}
            options={q.options}
            value={shown}
            disabled={answer.isPending}
            onCommit={(value) => (choice ? pick(value) : answer.mutate(value))}
          />
        </div>
      )}

      {excluded ? (
        <div className="mt-3">
          <TextArea
            label="Why this does not apply to you"
            value={naReason}
            onChange={(e) => setNaReason(e.target.value)}
            onBlur={saveWithText}
            autoFocus={pending !== null}
            rows={2}
            maxLength={4000}
          />
        </div>
      ) : needsNote ? (
        <div className="mt-3">
          <TextArea
            label="Explain your answer"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={saveWithText}
            autoFocus={pending !== null}
            rows={2}
            maxLength={8000}
          />
        </div>
      ) : choice && q.answered ? (
        <div className="mt-3">
          <TextArea
            label="How you do this"
            optional
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={saveWithText}
            rows={2}
            maxLength={8000}
          />
        </div>
      ) : null}

      {q.evidence !== "none" && q.answer_type !== "file" ? (
        <DocumentDrop
          question={q}
          owed={owesDocument(q)}
          optional={
            q.evidence === "optional" ||
            (q.answered &&
              q.evidence_on.length > 0 &&
              !pickedKeys(currentValue(q)).some((k) => q.evidence_on.includes(k)))
          }
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
 * Where a vendor attaches proof, or uploads the document a question asks for.
 * Shown before any answer is picked, so the ask and the way to meet it sit
 * together. Drop a file on it or browse; either way the server checks the file.
 */
function DocumentDrop({
  question: q,
  owed,
  optional,
  asAnswer = false,
  busy,
  onFile,
}: {
  question: PortalQuestion;
  /** Still needed before the questionnaire can be sent. */
  owed: boolean;
  /** Welcome but not needed for the answer given. */
  optional: boolean;
  /** The upload is the answer, not evidence for one. */
  asAnswer?: boolean;
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
              ? "border-status-warning-border bg-status-warning-bg"
              : "border-border bg-surface-sunken",
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
          {attached ? "Document attached" : asAnswer ? "Your document" : "Supporting document"}
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
        aria-label={`Upload a document for ${q.body}`}
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
