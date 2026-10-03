import type { ReactNode } from "react";
import { BrandMark } from "@/components/ui";

/**
 * The quiet frame for the platform sign in: one card on the page colour, the
 * platform name above it. No marketing panel, no workspace branding: an
 * operator is signing in to the platform, not to a tenant.
 */
export function ProviderAuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-page px-4 py-10">
      <div className="w-full max-w-[26rem]">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <BrandMark size={34} />
          <span className="font-display text-heading-sm text-text-primary">
            Verity platform
          </span>
        </div>
        <div className="rounded-xl border border-border bg-surface-primary p-6 shadow-2 sm:p-8">
          <div className="mb-6 text-center">
            <h1 className="font-display text-heading-lg text-text-primary">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-1.5 text-body-md text-text-secondary">
                {subtitle}
              </p>
            ) : null}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
