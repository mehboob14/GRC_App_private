import { tiers } from "@/content/pricing";

/**
 * The demo request, kept apart from React so its rules can be tested on their own:
 * what a link may preselect, what the form must have, and the JSON the endpoint gets.
 */

export interface InterestOption {
  value: string;
  label: string;
}

/** Areas a visitor can ask about. Values match module slugs, so module pages can preselect them. */
export const interestOptions: InterestOption[] = [
  { value: "compliance-automation", label: "Frameworks and controls" },
  { value: "evidence-management", label: "Evidence" },
  { value: "policy-management", label: "Policies" },
  { value: "risk-management", label: "Risk register" },
  { value: "third-party-risk", label: "Third-party risk" },
  { value: "asset-inventory", label: "Assets" },
  { value: "vulnerability-management", label: "Vulnerabilities" },
  { value: "integrations", label: "Integrations" },
  { value: "trust-center", label: "Trust Center" },
  { value: "ai-assistant", label: "AI assistant" },
  { value: "pricing", label: "Pricing" },
];

/** Accepts a module slug, "pricing", or "pricing:<tier>" and returns the interests and tier to preselect. */
export function parseInterest(raw: string | null | undefined): { interests: string[]; tier?: string } {
  if (!raw) return { interests: [] };
  const [value, tier] = raw.split(":");
  const known = interestOptions.some((option) => option.value === value);
  if (known) return { interests: [value], tier };
  // A topic without its own entry still reaches the team through the interest field; it just preselects nothing.
  return { interests: [], tier };
}

/** What the optional message starts with when a link says what the visitor was reading. Empty when it says nothing we know. */
export function interestSentence(raw: string | null | undefined): string {
  const { interests, tier } = parseInterest(raw);
  const option = interestOptions.find((candidate) => candidate.value === interests[0]);
  if (!option) return "";
  const plan = option.value === "pricing" ? tiers.find((candidate) => candidate.id === tier) : undefined;
  return plan ? `Interested in: ${option.label} (${plan.name} plan)` : `Interested in: ${option.label}`;
}

// The shapes the endpoint accepts (see the backend schema). A value outside them is dropped, never sent.
const INTEREST = /^[a-z0-9][a-z0-9:_-]{0,63}$/;
const SOURCE = /^[a-z0-9][a-z0-9_-]{0,31}$/;

export function safeInterest(raw: string | null | undefined): string | null {
  return raw && INTEREST.test(raw) ? raw : null;
}

/**
 * Which button the visitor came from, "demo-page" when they arrived without one. A long
 * name (a module's closing call to action) is cut to the length the endpoint takes rather
 * than dropped, so the request still says which module it came from.
 */
export function safeSource(raw: string | null | undefined): string {
  const cut = (raw ?? "").slice(0, 32).replace(/[-_]+$/, "");
  return SOURCE.test(cut) ? cut : "demo-page";
}

/** The link every "See a demo" action points at. `source` and `interest` ride along as query parameters. */
export function demoHref({ interest, source }: { interest?: string; source?: string } = {}): string {
  const query = new URLSearchParams();
  if (interest) query.set("interest", interest);
  if (source) query.set("from", source);
  const text = query.toString();
  return text ? `/demo/?${text}` : "/demo/";
}

export type DemoField = "name" | "email" | "company";

export interface DemoValues {
  name: string;
  email: string;
  company: string;
  message: string;
}

export const demoFieldOrder: DemoField[] = ["name", "email", "company"];

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** The problem with one field, or null. Messages say what to do, not what went wrong. */
export function checkDemoField(field: DemoField, value: string): string | null {
  const text = value.trim();
  if (field === "name") return text.length >= 2 ? null : "Enter your full name.";
  if (field === "email") return EMAIL.test(text) ? null : "Enter an email address like name@company.com.";
  return text ? null : "Enter your company name.";
}

export function validateDemoRequest(values: DemoValues): Partial<Record<DemoField, string>> {
  const errors: Partial<Record<DemoField, string>> = {};
  for (const field of demoFieldOrder) {
    const problem = checkDemoField(field, values[field]);
    if (problem) errors[field] = problem;
  }
  return errors;
}

/** The first word of a full name, for greeting the visitor on their own screen. */
export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? "";
}

/** The JSON the endpoint receives. Empty optional fields are left out. */
export function buildDemoPayload(values: DemoValues, context: { interest: string | null; source: string; page: string; website: string }) {
  const message = values.message.trim();
  return {
    full_name: values.name.trim(),
    email: values.email.trim(),
    company: values.company.trim(),
    message: message || undefined,
    interest: context.interest ?? undefined,
    source: context.source,
    page: context.page || undefined,
    // The honeypot field. Empty for people; the endpoint drops a request that fills it.
    website: context.website,
  };
}

/**
 * What to tell the visitor when the endpoint did not accept the request. A refusal that
 * says to come back much later (the endpoint limits an address per hour and a requester
 * per day) means they have most likely asked already, so the message says we have it.
 */
export function demoErrorMessage(status: number | null, retryAfterSeconds: number | null = null): string {
  if (status === 429) {
    if (retryAfterSeconds !== null && retryAfterSeconds > 3600) return "We cannot take another request right now. If you have already sent one, we have it and will reply by email.";
    return "There have been several requests from your network in a short time. Wait a few minutes and try again.";
  }
  if (status === 400 || status === 422) return "Some details were not accepted. Check your name, email and company and try again.";
  return "We could not send your request. Check your connection and try again in a moment.";
}

/** The seconds in a Retry-After header, or null when it is missing or is a date. */
export function retryAfterSeconds(value: string | null): number | null {
  const seconds = value === null ? NaN : Number(value);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}
