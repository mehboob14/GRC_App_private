import { Button, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { ExitCheck } from "../types";

/**
 * Where a reader goes to clear a check, keyed on the object type the backend
 * says would satisfy it.
 *
 * The point is that a blocker is never just a red line: it names the thing that
 * would clear it and offers the way there. A checklist that says "2 blockers"
 * and leaves the reader to hunt is a status display, not a workspace.
 */
const CLEARS: Record<string, { label: string; target: string }> = {
  vendor: { label: "Edit the vendor", target: "vendor" },
  vendor_tiering_assessment: { label: "Tier this engagement", target: "tiering" },
  vendor_assessment: { label: "Go to the questionnaire", target: "assessments" },
  vendor_team_roster: { label: "Open the roster", target: "roster" },
  vendor_finding: { label: "Work the findings", target: "findings" },
  vendor_contract: { label: "Open the paperwork", target: "paperwork" },
  vendor_approval: { label: "Record the decision", target: "approval" },
  vendor_stage: { label: "Review the lifecycle", target: "lifecycle" },
};

export type CheckTarget = (typeof CLEARS)[string]["target"];

export function ExitCheckRow({
  check,
  onGo,
}: {
  check: ExitCheck;
  /** Called with the target this check names. Absent means render no action. */
  onGo?: (target: string) => void;
}) {
  // Three-valued on purpose. `null` is the module that answers this not
  // existing yet — it is never a tick and never a failure, because both would
  // be a claim about the vendor rather than about the build.
  const unanswerable = check.satisfied === null;
  const passed = check.satisfied === true;
  const route = check.clears_with ? CLEARS[check.clears_with] : undefined;

  return (
    <li className="flex items-start gap-2.5 py-2">
      <span className="mt-0.5 shrink-0">
        {passed ? (
          <Icon name="check" className="size-4 text-status-success-base" aria-label="Met" />
        ) : unanswerable ? (
          <Icon name="clock" className="size-4 text-text-faint" aria-label="Not yet answerable" />
        ) : (
          <Icon name="alert" className="size-4 text-status-warning-base" aria-label="Blocking" />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-body-md",
            unanswerable ? "text-text-subtle" : "text-text-primary",
          )}
        >
          {check.label}
        </span>
        {check.detail ? (
          <span className="mt-0.5 block text-body-sm text-text-subtle">{check.detail}</span>
        ) : null}
        {unanswerable ? (
          <span className="mt-0.5 block text-caption text-text-subtle">
            Not checked — the part of Verity that answers this has not shipped yet. It is not
            holding anything up.
          </span>
        ) : null}
      </span>
      {!passed && !unanswerable && route && onGo ? (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={() => onGo(route.target)}>
          {route.label}
        </Button>
      ) : null}
    </li>
  );
}
