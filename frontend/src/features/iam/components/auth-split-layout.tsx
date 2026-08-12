import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { Icon } from "@/components/ui";
import { VENDOR_MARKS } from "@/lib/vendor-marks";

const CONNECTOR_MARKS = [
  VENDOR_MARKS.aws,
  VENDOR_MARKS.okta,
  VENDOR_MARKS.github,
  VENDOR_MARKS.datadog,
];

const PANEL_STATS = [
  ["91%", "SOC 2 readiness"],
  ["218", "live checks"],
  ["842", "evidence items"],
] as const;

/** Figma 8:20 — white form column + fixed dark marketing panel (DS dark surfaces). */
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
    <div className="flex min-h-full bg-surface-primary">
      <div className="flex w-full max-w-[512px] flex-col px-8 py-12 sm:px-14 sm:py-12">
        <Link to="/sign-in" className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-md bg-action-primary text-action-primary-fg">
            <Icon name="check" className="size-5" />
          </span>
          {/* Wordmark, not a heading — same style as the sidebar wordmark. */}
          <span className="font-display text-heading-sm text-text-primary">
            Verity
          </span>
        </Link>

        <div className="flex flex-1 flex-col justify-center py-10">
          <div className="w-full max-w-[360px]">
            <h1 className="font-display text-heading-xl text-text-primary">
              {title}
            </h1>
            <p className="mt-2 mb-7 text-body-lg text-text-secondary">
              {subtitle}
            </p>
            {children}
          </div>
        </div>

        <p className="text-body-sm text-text-subtle">
          © 2026 Verity ·{" "}
          <span className="text-text-secondary">Privacy</span>
          {" · "}
          <span className="text-text-secondary">Terms</span>
        </p>
      </div>

      <aside
        className="relative hidden flex-1 overflow-hidden lg:flex lg:flex-col lg:justify-center lg:px-16 lg:py-14"
        style={{
          backgroundImage:
            "linear-gradient(150deg, rgb(var(--color-panel-1)) 0%, rgb(var(--color-panel-2)) 55%, rgb(var(--color-panel-3)) 100%)",
        }}
      >
        <div className="pointer-events-none absolute left-[calc(100%-340px)] top-[-80px] size-[340px] rounded-full bg-panel-glow/[0.22] blur-3xl" />
        <div className="pointer-events-none absolute bottom-[-40px] left-[-60px] size-[360px] rounded-full bg-panel-glow/[0.12] blur-3xl" />
        <div className="relative max-w-[440px] text-white">
          <span className="inline-flex items-center rounded-full border border-panel-glow/25 bg-panel-glow/[0.12] px-3 py-1 font-sans text-overline uppercase text-panel-accent">
            Continuous compliance
          </span>
          <h2 className="mt-6 font-display text-display-xl">
            Audit-ready, every day of the year.
          </h2>
          <p className="mt-4 text-body-lg text-panel-muted">
            Verity continuously collects evidence, monitors 218 automated
            checks, and keeps SOC 2, ISO 27001 and HIPAA in one place.
          </p>
          <div className="mt-8 flex gap-3">
            {PANEL_STATS.map(([value, label]) => (
              <div
                key={label}
                className="flex-1 rounded-lg border border-panel-border bg-white/5 px-4 py-4 backdrop-blur-sm"
              >
                <p className="font-display text-numeral-lg tabular text-white">
                  {value}
                </p>
                <p className="mt-1 text-body-sm text-panel-muted">{label}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex items-center gap-3 border-t border-panel-border pt-6">
            <div className="flex">
              {CONNECTOR_MARKS.map((mark, index) => (
                <span
                  key={mark.label}
                  className={`flex size-8 items-center justify-center rounded-md border-2 border-panel-edge text-caption font-semibold text-white ${
                    index < CONNECTOR_MARKS.length - 1 ? "-mr-1.5" : ""
                  }`}
                  style={{ backgroundColor: mark.color }}
                >
                  {mark.label}
                </span>
              ))}
            </div>
            <p className="text-body-sm text-panel-muted">
              Trusted by security teams collecting evidence from 120+ systems
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
