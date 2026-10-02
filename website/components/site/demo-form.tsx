"use client";

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export interface InterestOption {
  value: string;
  label: string;
  soon?: boolean;
}

/** Areas a visitor can ask about. Values match module slugs so module pages can preselect them. */
export const interestOptions: InterestOption[] = [
  { value: "compliance-automation", label: "Frameworks and controls" },
  { value: "evidence-management", label: "Evidence" },
  { value: "policy-management", label: "Policies" },
  { value: "risk-management", label: "Risk register" },
  { value: "third-party-risk", label: "Third-party risk" },
  { value: "asset-inventory", label: "Assets" },
  { value: "vulnerability-management", label: "Vulnerabilities" },
  { value: "integrations", label: "Integrations" },
  { value: "trust-center", label: "Trust Center", soon: true },
  { value: "ai-assistant", label: "AI assistant", soon: true },
  { value: "pricing", label: "Pricing" },
];

const countries = ["Pakistan", "United Arab Emirates", "Australia", "United States", "Saudi Arabia", "Qatar", "United Kingdom", "Other"];
const sizes = ["1–50", "51–200", "201–1,000", "1,001–5,000", "More than 5,000"];
const MIN_FILL_MS = 2500;

type State = { kind: "idle" } | { kind: "sending" } | { kind: "sent" } | { kind: "error"; message: string };

/** Accepts a module slug, "pricing", or "pricing:<tier>" and returns the interests and tier to preselect. */
export function parseInterest(raw: string | null | undefined): { interests: string[]; tier?: string } {
  if (!raw) return { interests: [] };
  const [value, tier] = raw.split(":");
  const known = interestOptions.some((option) => option.value === value);
  if (known) return { interests: [value], tier };
  // Coming-soon modules without their own chip still preselect something sensible.
  return { interests: [], tier };
}

export function DemoForm({ endpoint, interest, source, onDone, compact = false }: { endpoint: string | null; interest?: string | null; source: string; onDone?: () => void; compact?: boolean }) {
  const id = useId();
  const started = useRef<number>(0);
  const preset = useMemo(() => parseInterest(interest), [interest]);
  const [selected, setSelected] = useState<string[]>(preset.interests);
  const [state, setState] = useState<State>({ kind: "idle" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    started.current = Date.now();
  }, []);
  useEffect(() => {
    setSelected(preset.interests);
  }, [preset]);

  const disabled = !endpoint;

  function toggle(value: string) {
    setSelected((current) => (current.includes(value) ? current.filter((item) => item !== value) : [...current, value]));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!endpoint || state.kind === "sending") return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) ?? "").trim();

    const nextErrors: Record<string, string> = {};
    if (!value("firstName")) nextErrors.firstName = "Enter your first name.";
    if (!value("lastName")) nextErrors.lastName = "Enter your last name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value("email"))) nextErrors.email = "Enter a work email address, like name@company.com.";
    if (!value("company")) nextErrors.company = "Enter your organisation's name.";
    if (!value("country")) nextErrors.country = "Choose a country.";
    if (data.get("consent") !== "on") nextErrors.consent = "We need your permission to contact you.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const first = form.querySelector<HTMLElement>(`[name="${Object.keys(nextErrors)[0]}"]`);
      first?.focus();
      return;
    }

    // A filled honeypot or an instant submission is almost certainly automated: accept quietly, send nothing.
    if (value("website") || Date.now() - started.current < MIN_FILL_MS) {
      setState({ kind: "sent" });
      return;
    }

    setState({ kind: "sending" });
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "omit",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          firstName: value("firstName"),
          lastName: value("lastName"),
          email: value("email"),
          company: value("company"),
          jobTitle: value("jobTitle"),
          country: value("country"),
          organisationSize: value("size"),
          interests: selected,
          tier: preset.tier ?? null,
          message: value("message"),
          consent: true,
          source,
          page: typeof window === "undefined" ? "" : window.location.pathname,
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      setState({ kind: "sent" });
    } catch {
      setState({ kind: "error", message: "Your request did not reach us. Check your connection and try again." });
    }
  }

  if (state.kind === "sent") {
    return (
      <div className="flex flex-col items-start gap-4 py-6" role="status">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-emerald-50 text-emerald-600"><Icon name="check" size={26} weight="fill" /></span>
        <h3 className="font-serif text-2xl">Thank you. We will be in touch.</h3>
        <p className="text-dim">Someone from Verity will reply to arrange a time that suits you. Nothing is booked until we confirm it with you.</p>
        {onDone && <button type="button" className="btn btn-outline btn-sm" onClick={onDone}>Close</button>}
      </div>
    );
  }

  const field = "w-full rounded-lg border border-line-strong bg-surface px-3 py-2.5 text-[15px] text-ink shadow-[0_1px_2px_rgb(16_24_40/0.04)] outline-none transition placeholder:text-faint focus:border-accent focus:shadow-focus disabled:cursor-not-allowed disabled:bg-subtle";
  const label = "mb-1.5 block text-[13px] font-medium text-ink";
  const errorText = (name: string) => errors[name] && <p id={`${id}-${name}-error`} className="mt-1 text-[13px] text-red-700">{errors[name]}</p>;
  const describedBy = (name: string) => (errors[name] ? `${id}-${name}-error` : undefined);

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4" aria-describedby={disabled ? `${id}-notice` : undefined}>
      {disabled && (
        <div id={`${id}-notice`} className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-[13.5px] leading-snug text-amber-900">
          <Icon name="info" size={18} className="mt-px shrink-0" />
          <p>Online requests are not connected yet, so this form cannot send anything. You can look through it now; nothing you type leaves your browser.</p>
        </div>
      )}
      <div className={cn("grid gap-4", !compact && "sm:grid-cols-2")}>
        <div>
          <label className={label} htmlFor={`${id}-first`}>First name</label>
          <input id={`${id}-first`} name="firstName" autoComplete="given-name" className={field} aria-invalid={!!errors.firstName} aria-describedby={describedBy("firstName")} />
          {errorText("firstName")}
        </div>
        <div>
          <label className={label} htmlFor={`${id}-last`}>Last name</label>
          <input id={`${id}-last`} name="lastName" autoComplete="family-name" className={field} aria-invalid={!!errors.lastName} aria-describedby={describedBy("lastName")} />
          {errorText("lastName")}
        </div>
        <div>
          <label className={label} htmlFor={`${id}-email`}>Work email</label>
          <input id={`${id}-email`} name="email" type="email" autoComplete="email" inputMode="email" className={field} aria-invalid={!!errors.email} aria-describedby={describedBy("email")} />
          {errorText("email")}
        </div>
        <div>
          <label className={label} htmlFor={`${id}-company`}>Organisation</label>
          <input id={`${id}-company`} name="company" autoComplete="organization" className={field} aria-invalid={!!errors.company} aria-describedby={describedBy("company")} />
          {errorText("company")}
        </div>
        <div>
          <label className={label} htmlFor={`${id}-title`}>Job title <span className="font-normal text-faint">(optional)</span></label>
          <input id={`${id}-title`} name="jobTitle" autoComplete="organization-title" className={field} />
        </div>
        <div>
          <label className={label} htmlFor={`${id}-country`}>Country</label>
          <select id={`${id}-country`} name="country" defaultValue="" className={field} aria-invalid={!!errors.country} aria-describedby={describedBy("country")}>
            <option value="" disabled>Choose a country</option>
            {countries.map((country) => <option key={country}>{country}</option>)}
          </select>
          {errorText("country")}
        </div>
        <div className={cn(!compact && "sm:col-span-2")}>
          <label className={label} htmlFor={`${id}-size`}>Organisation size <span className="font-normal text-faint">(optional)</span></label>
          <select id={`${id}-size`} name="size" defaultValue="" className={field}>
            <option value="">Choose a size</option>
            {sizes.map((size) => <option key={size} value={size}>{size} people</option>)}
          </select>
        </div>
      </div>

      <fieldset>
        <legend className={label}>What would you like to see? <span className="font-normal text-faint">(optional)</span></legend>
        <div className="flex flex-wrap gap-2">
          {interestOptions.map((option) => {
            const checked = selected.includes(option.value);
            return (
              <label key={option.value} className={cn("inline-flex cursor-pointer select-none items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-medium transition has-[:focus-visible]:shadow-focus", checked ? "border-ink bg-ink text-white" : "border-line-strong bg-surface text-body hover:border-[#b6bdc9]")}>
                <input type="checkbox" className="sr-only" checked={checked} onChange={() => toggle(option.value)} value={option.value} />
                {checked && <Icon name="check-plain" size={13} weight="bold" />}
                {option.label}
                {option.soon && <span className={cn("text-[11px]", checked ? "text-white/70" : "text-indigo-700")}>· soon</span>}
              </label>
            );
          })}
        </div>
      </fieldset>

      <div>
        <label className={label} htmlFor={`${id}-message`}>Anything we should know? <span className="font-normal text-faint">(optional)</span></label>
        <textarea id={`${id}-message`} name="message" rows={compact ? 2 : 3} maxLength={2000} className={cn(field, "resize-y")} placeholder="Frameworks you answer to, an audit date, the regulator you report to…" />
      </div>

      {/* Honeypot: hidden from people and assistive technology; bots tend to fill it. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor={`${id}-website`}>Website</label>
        <input id={`${id}-website`} name="website" tabIndex={-1} autoComplete="off" />
      </div>

      <div>
        <label className="flex items-start gap-2.5 text-[13.5px] leading-snug text-body">
          <input type="checkbox" name="consent" className="mt-0.5 h-4 w-4 shrink-0 accent-[rgb(var(--ink))]" aria-invalid={!!errors.consent} aria-describedby={describedBy("consent")} />
          <span>Verity may contact me about this request. My details are used only to reply to it.</span>
        </label>
        {errorText("consent")}
      </div>

      {state.kind === "error" && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-[13.5px] text-red-800" role="alert">{state.message}</p>}

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button type="submit" className="btn btn-dark" disabled={disabled || state.kind === "sending"} aria-disabled={disabled || state.kind === "sending"} style={disabled ? { opacity: 0.45, cursor: "not-allowed" } : undefined}>
          {state.kind === "sending" ? "Sending…" : "Request a demo"}
          {state.kind !== "sending" && <Icon name="arrow-right" size={16} weight="bold" className="btn-arrow" />}
        </button>
        <p className="text-[12.5px] text-faint">We reply by email to arrange a time. Nothing is booked until we confirm it with you.</p>
      </div>
    </form>
  );
}
