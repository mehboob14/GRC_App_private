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

/** Figma 8:20 — white left panel + brand gradient panel. */
export function AuthSplitLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-full bg-bg-elevated">
      <div className="flex w-full max-w-[512px] flex-col px-8 py-12 sm:px-14 sm:py-12">
        <Link to="/sign-in" className="flex items-center gap-[11px]">
          <span className="flex size-[34px] items-center justify-center rounded-[10px] bg-accent text-accent-fg shadow-mark">
            <Icon name="check" className="size-5" />
          </span>
          <span className="font-display text-heading-lg font-bold text-text">
            Verity
          </span>
        </Link>

        <div className="flex flex-1 flex-col justify-center py-10">
          <div className="w-full max-w-[360px]">
            <h1 className="font-display text-heading-xl text-text">{title}</h1>
            <p className="mt-2 mb-7 text-body-lg text-text-muted">
              {subtitle}
            </p>
            {children}
          </div>
        </div>

        <p className="text-body-sm text-text-faint">
          © 2026 Verity ·{" "}
          <span className="text-text-muted">Privacy</span>
          {" · "}
          <span className="text-text-muted">Terms</span>
          {footer}
        </p>
      </div>

      <aside
        className="relative hidden flex-1 overflow-hidden lg:flex lg:flex-col lg:justify-center lg:px-[60px] lg:py-14"
        style={{
          backgroundImage:
            "linear-gradient(150deg, rgb(var(--color-panel-1)) 0%, rgb(var(--color-panel-2)) 55%, rgb(var(--color-panel-3)) 100%)",
        }}
      >
        <div className="pointer-events-none absolute left-[calc(100%-340px)] top-[-80px] size-[340px] rounded-full bg-panel-glow/[0.22] blur-3xl" />
        <div className="pointer-events-none absolute bottom-[-40px] left-[-60px] size-[360px] rounded-full bg-panel-glow/[0.12] blur-3xl" />
        <div className="relative max-w-[440px] text-white">
          <span className="inline-flex rounded-full border border-panel-glow/25 bg-panel-glow/[0.12] px-3 py-[5px] text-body-sm font-semibold text-panel-accent">
            CONTINUOUS COMPLIANCE
          </span>
          <h2 className="mt-6 font-display text-heading-xl">
            Audit-ready, every day of the year.
          </h2>
          <p className="mt-4 text-[16px] leading-6 text-white">
            Verity continuously collects evidence, monitors 218 automated
            checks, and keeps SOC 2, ISO 27001 and HIPAA in one place.
          </p>
          <div className="mt-8 flex gap-[14px]">
            {[
              ["91%", "SOC 2 readiness"],
              ["218", "live checks"],
              ["842", "evidence items"],
            ].map(([value, label]) => (
              <div
                key={label}
                className="w-[137px] rounded-xl border border-white/25 bg-white/10 px-[18px] py-4 backdrop-blur-sm"
              >
                <p className="font-display text-heading-xl tabular text-white">
                  {value}
                </p>
                <p className="mt-[3px] text-body-sm text-white/90">{label}</p>
              </div>
            ))}
          </div>
          <div className="mt-[34px] flex items-center gap-3 border-t border-white/25 pt-[26px]">
            <div className="flex">
              {CONNECTOR_MARKS.map((mark, index) => (
                <span
                  key={mark.label}
                  className={`flex size-8 items-center justify-center rounded-lg border-2 border-panel-edge text-body-sm font-medium text-white ${
                    index < CONNECTOR_MARKS.length - 1 ? "-mr-1.5" : ""
                  }`}
                  style={{ backgroundColor: mark.color }}
                >
                  {mark.label}
                </span>
              ))}
            </div>
            <p className="text-body-sm text-white/90">
              Trusted by security teams collecting evidence from 120+ systems
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
