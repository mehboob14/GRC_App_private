"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { cn } from "@/lib/cn";
import { demoPage } from "@/content/demo";
import {
  buildDemoPayload,
  checkDemoField,
  demoErrorMessage,
  demoFieldOrder,
  firstName,
  interestSentence,
  retryAfterSeconds,
  safeInterest,
  safeSource,
  validateDemoRequest,
  type DemoField,
  type DemoValues,
} from "@/lib/demo";
import { Icon } from "@/components/ui/icon";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "sent"; name: string; email: string } | { kind: "error"; message: string };

type Errors = Partial<Record<DemoField, string>>;

const TIMEOUT_MS = 15_000;

/** 16px text on purpose: anything smaller makes iOS zoom into the field on focus. */
const control = "block min-h-[46px] w-full rounded-lg border bg-surface px-3.5 py-2.5 text-base text-ink shadow-[0_1px_2px_rgb(16_24_40/0.04)] outline-none transition placeholder:text-faint focus:border-accent focus:shadow-focus disabled:cursor-not-allowed disabled:bg-subtle";
const labelClass = "mb-1.5 block text-[14px] font-medium text-ink";

/** The page where a visitor asks for a demo. It reads ?interest= and ?from= so the team knows what prompted the request. */
export function DemoRequestForm({ endpoint, privacyUrl }: { endpoint: string | null; privacyUrl: string | null }) {
  const params = useSearchParams();
  const interest = safeInterest(params.get("interest"));
  const source = safeSource(params.get("from"));
  // A new topic means a fresh form, so the preset message always matches the link that was followed.
  return <RequestForm key={`${interest ?? ""}|${source}`} endpoint={endpoint} privacyUrl={privacyUrl} interest={interest} source={source} />;
}

function RequestForm({ endpoint, privacyUrl, interest, source }: { endpoint: string | null; privacyUrl: string | null; interest: string | null; source: string }) {
  const id = useId();
  const [values, setValues] = useState<DemoValues>(() => ({ name: "", email: "", company: "", message: interestSentence(interest) }));
  const [errors, setErrors] = useState<Errors>({});
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [trap, setTrap] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);
  const companyInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (status.kind === "sent") heading.current?.focus();
  }, [status.kind]);

  function setError(field: DemoField, problem: string | null) {
    setErrors((current) => {
      const next = { ...current };
      if (problem) next[field] = problem;
      else delete next[field];
      return next;
    });
  }

  function change(field: keyof DemoValues) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value;
      setValues((current) => ({ ...current, [field]: value }));
      if (field === "message") return;
      // Once a field has been flagged, tell the visitor the moment it is right again.
      if (errors[field]) setError(field, checkDemoField(field, value));
    };
  }

  function leave(field: DemoField) {
    // An empty field is not an error yet, since the visitor may be tabbing past it; the submit says so.
    return () => {
      if (values[field] || errors[field]) setError(field, checkDemoField(field, values[field]));
    };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!endpoint || status.kind === "sending") return;
    const found = validateDemoRequest(values);
    setErrors(found);
    const first = demoFieldOrder.find((field) => found[field]);
    if (first) {
      const inputs = { name: nameInput, email: emailInput, company: companyInput };
      inputs[first].current?.focus();
      return;
    }

    setStatus({ kind: "sending" });
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "omit",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(buildDemoPayload(values, { interest, source, page: originPage(), website: trap })),
        signal: controller.signal,
      });
      if (!response.ok) {
        // The endpoint exposes Retry-After to this site, so a long wait can be told apart from a short one.
        setStatus({ kind: "error", message: demoErrorMessage(response.status, retryAfterSeconds(response.headers.get("Retry-After"))) });
        return;
      }
      setStatus({ kind: "sent", name: firstName(values.name), email: values.email.trim() });
    } catch {
      setStatus({ kind: "error", message: demoErrorMessage(null) });
    } finally {
      window.clearTimeout(timer);
    }
  }

  if (status.kind === "sent") {
    return (
      <div role="status" className="flex flex-col items-start gap-6 py-2">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-emerald-50 text-emerald-600">
          <Icon name={demoPage.success.icon} size={28} weight="fill" />
        </span>
        <div>
          <h2 ref={heading} tabIndex={-1} className="font-serif text-[28px] leading-tight outline-none">
            {demoPage.success.title(status.name)}
          </h2>
          <p className="mt-3 text-[16px] leading-relaxed text-dim">
            We will email <strong className="break-all font-semibold text-ink">{status.email}</strong> to find a time. {demoPage.success.text}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/" className="btn btn-outline">Back to the homepage</Link>
          <Link href="/docs/" className="btn btn-ghost">Browse the documentation</Link>
        </div>
      </div>
    );
  }

  const sending = status.kind === "sending";
  const disabled = !endpoint;
  const describe = (field: DemoField) => (errors[field] ? `${id}-${field}-error` : undefined);
  const problem = (field: DemoField) =>
    errors[field] && (
      <p id={`${id}-${field}-error`} className="mt-1.5 flex items-start gap-1.5 text-[13.5px] leading-snug text-red-700">
        <Icon name="warning" size={15} weight="fill" className="mt-px shrink-0" />
        {errors[field]}
      </p>
    );

  return (
    <form noValidate onSubmit={submit} aria-labelledby={`${id}-title`} aria-busy={sending} className="relative flex flex-col gap-5">
      <div>
        <h2 id={`${id}-title`} className="font-serif text-[26px] leading-tight">{demoPage.formTitle}</h2>
        <p className="mt-1 text-[14.5px] text-dim">{demoPage.formNote}</p>
      </div>

      {disabled && (
        <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-[13.5px] leading-snug text-amber-900">
          <Icon name="info" size={18} className="mt-px shrink-0" />
          <p>Online requests are not connected on this preview, so nothing can be sent from here.</p>
        </div>
      )}

      <div>
        <label className={labelClass} htmlFor={`${id}-name`}>Full name</label>
        <input
          ref={nameInput}
          id={`${id}-name`}
          name="name"
          value={values.name}
          onChange={change("name")}
          onBlur={leave("name")}
          autoComplete="name"
          maxLength={120}
          aria-required="true"
          aria-invalid={Boolean(errors.name)}
          aria-describedby={describe("name")}
          className={cn(control, errors.name ? "border-red-600" : "border-line-strong")}
        />
        {problem("name")}
      </div>

      <div>
        <label className={labelClass} htmlFor={`${id}-email`}>Work email</label>
        <input
          ref={emailInput}
          id={`${id}-email`}
          name="email"
          type="email"
          value={values.email}
          onChange={change("email")}
          onBlur={leave("email")}
          autoComplete="email"
          inputMode="email"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          maxLength={254}
          aria-required="true"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={describe("email")}
          className={cn(control, errors.email ? "border-red-600" : "border-line-strong")}
        />
        {problem("email")}
      </div>

      <div>
        <label className={labelClass} htmlFor={`${id}-company`}>Company</label>
        <input
          ref={companyInput}
          id={`${id}-company`}
          name="company"
          value={values.company}
          onChange={change("company")}
          onBlur={leave("company")}
          autoComplete="organization"
          maxLength={160}
          aria-required="true"
          aria-invalid={Boolean(errors.company)}
          aria-describedby={describe("company")}
          className={cn(control, errors.company ? "border-red-600" : "border-line-strong")}
        />
        {problem("company")}
      </div>

      <div>
        <label className={labelClass} htmlFor={`${id}-message`}>
          {demoPage.messageLabel} <span className="font-normal text-dim">(optional)</span>
        </label>
        <textarea
          id={`${id}-message`}
          name="message"
          rows={3}
          maxLength={2000}
          value={values.message}
          onChange={change("message")}
          aria-describedby={`${id}-message-hint`}
          className={cn(control, "resize-y border-line-strong")}
        />
        <p id={`${id}-message-hint`} className="mt-1.5 text-[13px] text-dim">{demoPage.messageHint}</p>
      </div>

      {/* Honeypot: out of sight and out of the tab order. People leave it empty, and autofill has no field name to match. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor={`${id}-trap`}>Leave this field empty</label>
        <input id={`${id}-trap`} name="hp_field" tabIndex={-1} autoComplete="off" value={trap} onChange={(event) => setTrap(event.target.value)} />
      </div>

      {status.kind === "error" && (
        <p role="alert" className="flex gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-[14px] leading-snug text-red-800">
          <Icon name="warning" size={18} weight="fill" className="mt-px shrink-0" />
          {status.message}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <button type="submit" className="btn btn-dark btn-lg w-full sm:w-fit" disabled={disabled || sending} aria-disabled={disabled || sending} style={disabled ? { opacity: 0.45, cursor: "not-allowed" } : undefined}>
          {sending ? (
            <>
              <Spinner />
              Sending
            </>
          ) : (
            <>
              Request a demo
              <Icon name="arrow-right" size={16} weight="bold" className="btn-arrow" />
            </>
          )}
        </button>
        <p className="text-[13px] leading-relaxed text-dim">
          {demoPage.afterSubmit} {demoPage.consent}
          {privacyUrl && (
            <>
              {" "}
              <a href={privacyUrl} className="font-medium text-accent hover:text-accent-strong">Privacy policy</a>.
            </>
          )}
        </p>
      </div>
    </form>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** The page the visitor was on before this one, when it is ours; otherwise this page. */
function originPage(): string {
  try {
    const referrer = new URL(document.referrer);
    if (referrer.origin === window.location.origin) return referrer.pathname;
  } catch {
    // No referrer, or one that is not a URL: fall through.
  }
  return window.location.pathname;
}
