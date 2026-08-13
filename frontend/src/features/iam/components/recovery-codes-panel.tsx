import { useState } from "react";
import { Button, Icon } from "@/components/ui";

type Props = {
  codes: string[];
  onContinue: () => void;
};

/**
 * The one-time display of MFA recovery codes. They leave the server exactly once
 * (on enrollment confirmation), so the user must acknowledge saving them before
 * proceeding. Nothing here refetches or persists them.
 */
export function RecoveryCodesPanel({ codes, onContinue }: Props) {
  const [copied, setCopied] = useState(false);

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked (permissions, insecure context); the codes are
      // on screen to copy by hand, so this is a non-error.
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <ul
        className="grid grid-cols-2 gap-2 rounded-md border border-border bg-surface-sunken p-3"
        aria-label="Recovery codes"
      >
        {codes.map((code) => (
          <li
            key={code}
            className="text-center font-mono text-body-md tracking-wide text-text-primary tabular"
          >
            {code}
          </li>
        ))}
      </ul>

      <Button variant="secondary" onClick={copyAll} className="w-full">
        <Icon name={copied ? "check" : "doc"} className="size-4" />
        {copied ? "Copied" : "Copy all codes"}
      </Button>

      <Button size="lg" className="w-full" onClick={onContinue}>
        I've saved them — continue
        <Icon name="arrowr" className="size-4" />
      </Button>
    </div>
  );
}
