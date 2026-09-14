import { Link } from "react-router-dom";
import type { CSSProperties, ReactNode } from "react";
import { BrandMark, Icon, type IconName } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ControlMap } from "@/features/iam/auth-kit/control-map";

// The chain Verity runs end to end, each module handing its findings to the
// next. The links light in turn, like work moving down the line.
const CHAIN: { icon: IconName; from: string; to: string }[] = [
  { icon: "box", from: "Asset", to: "Exposure" },
  { icon: "bug", from: "Vulnerability", to: "Risk" },
  { icon: "shieldCheck", from: "Risk", to: "Remediation" },
];

type MarkTone = "accent" | "success" | "warning" | "danger";

const MARK_TONE: Record<MarkTone, string> = {
  accent:
    "bg-action-accent text-white shadow-[0_12px_24px_-10px_rgb(var(--color-action-accent)/0.7)]",
  success:
    "bg-status-success-base text-white shadow-[0_12px_24px_-10px_rgb(var(--color-status-success-base)/0.7)]",
  warning:
    "bg-status-warning-base text-white shadow-[0_12px_24px_-10px_rgb(var(--color-status-warning-base)/0.7)]",
  danger:
    "bg-status-danger-base text-white shadow-[0_12px_24px_-10px_rgb(var(--color-status-danger-base)/0.7)]",
};

function Wordmark() {
  return (
    <Link
      to="/sign-in"
      className="inline-flex items-center gap-2.5 rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-action-accent"
    >
      <BrandMark size={34} />
      <span className="font-display text-heading-sm text-text-primary">
        Verity
      </span>
    </Link>
  );
}

/**
 * The shell for every signed out screen. Left, the product in one picture: a
 * control proven once lighting up six frameworks. Right, the form on a
 * floating card. Forced light (`.light`) so auth stays bright under the app's
 * dark theme. `mark` puts a status medallion over the title for outcome
 * screens (email sent, password updated, link expired).
 */
export function AuthSplitLayout({
  title,
  subtitle,
  children,
  mark,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  mark?: { icon: IconName; tone?: MarkTone };
}) {
  return (
    <div className="light relative flex min-h-screen w-full flex-col overflow-hidden bg-gradient-to-br from-action-accent-tint via-surface-primary to-surface-primary text-text-primary lg:h-screen">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="auth-blob-1 absolute -left-40 -top-40 size-[30rem] rounded-full bg-action-accent/10 blur-3xl" />
        <div className="auth-blob-3 absolute bottom-0 left-1/4 size-[24rem] rounded-full bg-action-accent/[0.06] blur-3xl" />
        <div className="auth-grid absolute inset-y-0 left-0 w-full lg:w-[52%]" />
      </div>

      <div className="relative z-10 flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <aside className="hidden min-h-0 flex-col justify-between gap-6 px-10 py-8 lg:flex xl:px-14">
          <div className="auth-fade-up">
            <Wordmark />
          </div>

          <div className="flex w-full max-w-[34rem] flex-col self-center">
            <p
              className="auth-fade-up text-overline uppercase text-action-accent"
              style={{ animationDelay: "0.04s" }}
            >
              Governance, risk and compliance
            </p>
            <h1
              className="auth-fade-up mt-3 text-balance font-display text-heading-xl text-text-primary xl:text-display-xl"
              style={{ animationDelay: "0.08s" }}
            >
              The GRC platform your auditors trust.
            </h1>
            <p
              className="auth-fade-up mt-3 text-body-lg text-text-secondary"
              style={{ animationDelay: "0.14s" }}
            >
              Map a control once. Prove it in every framework.
            </p>
            <div
              className="auth-fade-up mt-7 [@media(max-height:680px)]:hidden"
              style={{ animationDelay: "0.2s" }}
            >
              <ControlMap />
            </div>
          </div>

          <ol
            aria-label="How Verity connects security work"
            className="auth-fade-up flex flex-wrap items-center gap-x-3 gap-y-3"
            style={{ animationDelay: "0.26s" }}
          >
            {CHAIN.map((step, i) => (
              <li key={step.to} className="flex items-center gap-3">
                {i > 0 ? (
                  <Icon name="chevr" className="size-3 text-action-accent/40" />
                ) : null}
                <span
                  className="flex items-center gap-2.5"
                  style={{ "--i": i } as CSSProperties}
                >
                  <span className="auth-chain-icon grid size-8 shrink-0 place-items-center rounded-xl bg-surface-primary text-action-accent shadow-1 ring-1 ring-border">
                    <Icon name={step.icon} className="size-4" />
                  </span>
                  <span className="whitespace-nowrap leading-tight">
                    <span className="block text-caption text-text-subtle">
                      From {step.from}
                    </span>
                    <span className="block text-label-md text-text-primary">
                      to {step.to}
                    </span>
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </aside>

        <main className="flex min-h-0 flex-1 items-stretch justify-center px-4 py-4 sm:px-6 lg:py-6 lg:pl-0 lg:pr-8">
          <div
            className="auth-fade-up auth-no-scrollbar flex w-full flex-col items-center overflow-y-auto rounded-[28px] bg-surface-primary px-5 py-8 shadow-3 ring-1 ring-black/5 sm:px-10 lg:max-w-[34rem]"
            style={{ animationDelay: "0.06s" }}
          >
            <div className="my-auto w-full max-w-[25rem]">
              <div className="mb-7 flex justify-center lg:hidden">
                <Wordmark />
              </div>
              <div className="mb-6 flex flex-col items-center text-center">
                {mark ? (
                  <span
                    className={cn(
                      "auth-mark-in mb-4 grid size-14 place-items-center rounded-2xl",
                      MARK_TONE[mark.tone ?? "accent"],
                    )}
                  >
                    <Icon name={mark.icon} className="size-7" />
                  </span>
                ) : null}
                <h2 className="text-balance font-display text-heading-lg text-text-primary">
                  {title}
                </h2>
                {subtitle ? (
                  <p className="mt-1.5 text-balance text-body-lg text-text-secondary">
                    {subtitle}
                  </p>
                ) : null}
              </div>
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
