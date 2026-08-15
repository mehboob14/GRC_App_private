import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { Icon } from "@/components/ui";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";

// The continuous GRC loop, shown as a flow (security-first framing): assess
// risk → close the gaps → watch continuously → prove it to auditors.
const LIFECYCLE = ["Assess", "Remediate", "Monitor", "Attest"];

// Full framework catalogue for the bottom marquee. Text chips (no third-party
// brand marks) — a shield glyph stands in for each logo.
const FRAMEWORKS: { label: string; blurb: string }[] = [
  { label: "SOC 2", blurb: "Trust services" },
  { label: "ISO 27001", blurb: "Information security" },
  { label: "GDPR", blurb: "Data protection" },
  { label: "NIST CSF", blurb: "Cyber framework" },
  { label: "PCI-DSS", blurb: "Payment security" },
  { label: "HIPAA", blurb: "Health data" },
  { label: "ISO 22301", blurb: "Business continuity" },
  { label: "ISO 27701", blurb: "Privacy management" },
  { label: "DORA", blurb: "Operational resilience" },
  { label: "NIS2", blurb: "EU cyber directive" },
  { label: "CIS Controls", blurb: "Security baselines" },
  { label: "SOX", blurb: "Financial reporting" },
];

const MARQUEE_MASK =
  "linear-gradient(to right, transparent, black 8%, black 92%, transparent)";

function Wordmark() {
  return (
    <Link to="/sign-in" className="inline-flex items-center gap-2.5">
      <span className="flex size-9 items-center justify-center rounded-md bg-action-primary text-action-primary-fg">
        <Icon name="check" className="size-5" />
      </span>
      <span className="font-display text-heading-sm text-text-primary">
        Verity
      </span>
    </Link>
  );
}

function LifecycleFlow() {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
      {LIFECYCLE.map((stage, i) => (
        <div key={stage} className="flex items-center gap-3">
          <span className="flex flex-col">
            <span className="text-body-md font-semibold tracking-tight text-text-primary">
              {stage}
            </span>
            <span className="mt-1 h-[3px] w-9 rounded-full bg-gradient-to-r from-action-accent to-action-accent/30" />
          </span>
          {i < LIFECYCLE.length - 1 ? (
            <Icon
              name="arrowr"
              className="size-4 shrink-0 text-action-accent/60"
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}

function FrameworkMarquee() {
  const cards = [...FRAMEWORKS, ...FRAMEWORKS];
  return (
    <div className="relative z-10 w-full pb-10 pt-2">
      <p className="mb-3 text-center type-overline text-text-subtle">
        Frameworks built in
      </p>
      <div className="mx-auto w-[min(92%,72rem)] rounded-full border border-white/70 bg-surface-primary/50 p-2 shadow-2 backdrop-blur-md">
        <div
          className="overflow-hidden rounded-full"
          style={{ maskImage: MARQUEE_MASK, WebkitMaskImage: MARQUEE_MASK }}
        >
          <div className="auth-marquee-track flex w-max items-center gap-3 py-1 pr-3">
            {cards.map(({ label, blurb }, i) => (
              <div
                key={`${label}-${i}`}
                className="flex h-[3.25rem] items-center gap-3 rounded-full border border-border bg-surface-primary py-2 pl-3 pr-6 shadow-1"
              >
                <span className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface-primary ring-1 ring-border">
                  <FrameworkLogo name={label} size={26} eager />
                </span>
                <span className="flex flex-col leading-tight">
                  <span className="whitespace-nowrap text-sm font-bold text-text-primary">
                    {label}
                  </span>
                  <span className="whitespace-nowrap text-[11px] font-medium text-text-subtle">
                    {blurb}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Auth shell for sign-in & sign-up — one continuous light gradient (Verity
 * blue), a brand hero on the left, the form in a floating white card on the
 * right, and a full-width framework marquee along the bottom. Forced light
 * (`.light`) so the auth screens stay white even under the app's dark theme.
 */
export function AuthSplitLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="light relative flex min-h-screen w-full flex-col overflow-hidden bg-gradient-to-br from-action-accent-tint to-surface-primary text-text-primary lg:h-screen">
      {/* soft decorative glow — one surface across the whole page */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="auth-blob-1 absolute -left-32 -top-32 size-[26rem] rounded-full bg-action-accent/10 blur-3xl" />
        <div className="auth-blob-2 absolute -bottom-40 right-1/3 size-[28rem] rounded-full bg-surface-primary/70 blur-3xl" />
        <div className="auth-blob-3 absolute right-0 top-0 size-[22rem] rounded-full bg-action-accent/[0.07] blur-3xl" />
      </div>

      <div className="relative z-10 flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[46fr_54fr]">
        {/* ── LEFT · brand hero ─────────────────────────────────────────── */}
        <aside className="hidden min-h-0 p-8 lg:flex lg:flex-col lg:justify-between xl:p-10">
          <div className="auth-fade-up">
            <Wordmark />
          </div>

          <div className="flex min-h-0 max-w-lg flex-col justify-center gap-6 py-4">
            <p className="auth-fade-up type-overline text-action-accent">
              AI-native enterprise GRC
            </p>

            <h1
              className="auth-fade-up font-display text-heading-xl leading-[1.14] tracking-tight text-text-primary xl:text-display-lg"
              style={{ animationDelay: "0.05s" }}
            >
              The GRC platform
              <br />
              your auditors trust.
            </h1>

            <div
              className="auth-fade-up flex flex-col gap-3"
              style={{ animationDelay: "0.12s" }}
            >
              <p className="text-body-lg font-medium text-text-secondary">
                Governance, risk &amp; compliance —{" "}
                <span className="font-semibold text-action-accent">
                  one continuous loop.
                </span>
              </p>
              <LifecycleFlow />
            </div>

            <div
              className="auth-fade-up h-px w-24 bg-gradient-to-r from-action-accent to-transparent"
              style={{ animationDelay: "0.18s" }}
            />

            <div
              className="auth-fade-up flex items-center gap-4 text-body-sm font-medium text-text-secondary"
              style={{ animationDelay: "0.22s" }}
            >
              <span className="whitespace-nowrap">AI-native</span>
              <span className="h-3.5 w-px bg-border" />
              <span className="whitespace-nowrap">Continuous evidence</span>
              <span className="h-3.5 w-px bg-border" />
              <span className="whitespace-nowrap">Audit-ready</span>
            </div>

            <p
              className="auth-fade-up max-w-sm text-body-lg font-semibold leading-snug tracking-tight text-text-primary"
              style={{ animationDelay: "0.28s" }}
            >
              One workspace for risk, compliance and audit readiness.
            </p>
          </div>

          <div />
        </aside>

        {/* ── RIGHT · white form card ───────────────────────────────────── */}
        <main className="flex min-h-0 flex-1 items-stretch justify-center px-4 py-4 sm:px-6 lg:pl-0 lg:pr-8">
          <div
            className="auth-fade-up auth-no-scrollbar flex w-full flex-col items-center overflow-y-auto rounded-[28px] bg-surface-primary px-5 py-6 shadow-3 ring-1 ring-black/5 sm:px-10 lg:max-w-[33rem]"
            style={{ animationDelay: "0.08s" }}
          >
            <div className="my-auto w-full max-w-md">
              <div className="mb-6 flex justify-center lg:hidden">
                <Wordmark />
              </div>
              <div className="mb-5 text-center">
                <h2 className="font-display text-heading-lg text-text-primary">
                  {title}
                </h2>
                <p className="mt-1.5 text-body-md text-text-secondary">
                  {subtitle}
                </p>
              </div>
              {children}
            </div>
          </div>
        </main>
      </div>

      {/* ── BOTTOM · full-width framework marquee ─────────────────────────── */}
      <FrameworkMarquee />
    </div>
  );
}
