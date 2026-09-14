import type { ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";
import { Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import { suggestEmail, webmailFor } from "./email-hints";
import { linkClass } from "./helpers";

/** "Did you mean name@gmail.com?" under an email field; one click fixes it. */
export function EmailSuggestion({
  email,
  onAccept,
}: {
  email: string;
  onAccept: (email: string) => void;
}) {
  const suggestion = suggestEmail(email);
  if (!suggestion) return null;
  return (
    <p className="auth-msg-in mt-1.5 text-body-sm text-text-secondary">
      Did you mean{" "}
      <button
        type="button"
        onClick={() => onAccept(suggestion)}
        className={linkClass}
      >
        {suggestion}
      </button>
      ?
    </p>
  );
}

export function OrDivider({ children }: { children: ReactNode }) {
  return (
    <div className="my-5 flex items-center gap-3" role="separator">
      <span className="h-px flex-1 bg-border" />
      <span className="text-caption font-semibold uppercase tracking-wide text-text-subtle">
        {children}
      </span>
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden>
      <path
        fill="#4285F4"
        d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.5 5.5 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.7z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.2 0 6-1.1 7.9-2.9l-3.9-3c-1 .7-2.4 1.1-4 1.1-3.1 0-5.7-2.1-6.7-4.9h-4v3.1A12 12 0 0 0 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1z"
      />
      <path
        fill="#EA4335"
        d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1C6.3 6.9 8.9 4.8 12 4.8z"
      />
    </svg>
  );
}

function MicrosoftMark() {
  return (
    <span className="grid size-4 grid-cols-2 gap-px" aria-hidden>
      <span className="bg-[#F25022]" />
      <span className="bg-[#7FBA00]" />
      <span className="bg-[#00A4EF]" />
      <span className="bg-[#FFB900]" />
    </span>
  );
}

const SSO: { label: string; mark: ReactNode }[] = [
  { label: "Google", mark: <GoogleMark /> },
  { label: "Microsoft", mark: <MicrosoftMark /> },
  {
    label: "SSO",
    mark: <Icon name="key" className="size-4 text-text-secondary" />,
  },
];

/** Identity federation arrives in a later phase: visible, honest, not clickable. */
export function SsoOptions() {
  return (
    <div className="grid grid-cols-3 gap-2">
      {SSO.map((provider) => (
        <button
          key={provider.label}
          type="button"
          disabled
          aria-label={`Continue with ${provider.label}, coming soon`}
          className="relative flex h-11 cursor-not-allowed items-center justify-center gap-2 rounded-xl border border-border bg-surface-primary text-label-md text-text-secondary"
        >
          <span className="flex items-center gap-2 opacity-60">
            {provider.mark}
            {provider.label}
          </span>
          <span className="absolute -top-2 right-2 rounded-full bg-action-accent-tint px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-action-accent ring-2 ring-surface-primary">
            Soon
          </span>
        </button>
      ))}
    </div>
  );
}

/** Where the email went, with a way to fix a wrong address. */
export function SentTo({
  email,
  label = "Sent to",
  onChange,
}: {
  email: string;
  label?: string;
  onChange?: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-surface-sunken p-2.5 pr-4">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface-primary text-action-accent shadow-1 ring-1 ring-border">
        <Icon name="mail" className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-caption text-text-subtle">{label}</span>
        <span className="block truncate text-title-md text-text-primary">
          {email}
        </span>
      </span>
      {onChange ? (
        <button
          type="button"
          onClick={onChange}
          className={cn(linkClass, "text-label-sm")}
        >
          Change
        </button>
      ) : null}
    </div>
  );
}

/** One click into the inbox the link went to. */
export function WebmailLinks({ email }: { email: string }) {
  const links = webmailFor(email);
  return (
    <div
      className={cn(
        "grid gap-2",
        links.length > 1 ? "grid-cols-2" : "grid-cols-1",
      )}
    >
      {links.map((link) => (
        <a
          key={link.href}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex h-11 items-center justify-center gap-2 rounded-full border border-border bg-surface-primary text-label-md text-text-primary shadow-1 transition-[border-color,background-color,box-shadow] hover:border-border-strong hover:bg-surface-hover hover:shadow-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
        >
          <Icon name="mail" className="size-4 text-action-accent" />
          {link.label}
        </a>
      ))}
    </div>
  );
}

/** A primary call to action that navigates, dressed like the submit button. */
export function CtaLink({ children, className, ...props }: LinkProps) {
  return (
    <Link
      {...props}
      data-phase="idle"
      className={cn(
        "vx-cta group font-sans text-label-md font-bold",
        className,
      )}
    >
      <span className="vx-cta-ring" aria-hidden />
      <span className="relative z-[1] inline-flex items-center gap-2">
        {children}
        {/* The submit button's arrow, so both primaries read as one family. */}
        <svg
          viewBox="0 0 24 24"
          className="size-4 transition-transform duration-200 group-hover:translate-x-0.5"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.6}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M5 12h13M13 6l6 6-6 6" />
        </svg>
      </span>
    </Link>
  );
}
