import { useState } from "react";
import { Icon } from "@/components/ui";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import {
  displayRecoveryCode,
  secondaryPill,
} from "@/features/iam/auth-kit/helpers";

type Props = {
  codes: string[];
  onContinue: () => void;
};

/**
 * The one time display of MFA recovery codes. They leave the server exactly
 * once (on enrollment confirmation), so the user must acknowledge saving them
 * before proceeding. Nothing here refetches or persists them. Codes show with a
 * space between the groups; sign in accepts them typed either way.
 */
export function RecoveryCodesPanel({ codes, onContinue }: Props) {
  const [copied, setCopied] = useState(false);
  const shown = codes.map(displayRecoveryCode);

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(shown.join("\n"));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked (permissions, insecure context); the codes are
      // on screen to copy by hand, so this is a non-error.
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        onContinue();
      }}
    >
      <ul
        className="grid grid-cols-2 gap-2 rounded-2xl border border-border bg-surface-sunken p-3"
        aria-label="Recovery codes"
      >
        {shown.map((code) => (
          <li
            key={code}
            className="rounded-lg bg-surface-primary py-2 text-center font-mono text-body-md font-semibold tracking-wider text-text-primary shadow-1 tabular"
          >
            {code}
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => void copyAll()}
        className={secondaryPill}
      >
        <Icon name={copied ? "check" : "copy"} className="size-4" />
        {copied ? "Copied" : "Copy all codes"}
      </button>

      <AuthSubmitButton
        label="I've saved them, continue"
        steps={["Opening your workspace"]}
        successLabel="Done"
        phase="idle"
      />
    </form>
  );
}
