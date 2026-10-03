import {
  useAuth,
} from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import type { IconName, StatusFamily } from "@/components/ui";
import type {
  AutomationStatus,
  Outcome,
  TestStatus,
} from "../api";
import { useAutomation, useRunConnections } from "../hooks";

export const CONTROL_STATE: Record<
  AutomationStatus,
  { label: string; family: StatusFamily; icon: IconName; tone: string }
> = {
  passing: {
    label: "Passing",
    family: "success",
    icon: "check",
    tone: "bg-status-success-base",
  },
  failing: {
    label: "Failing",
    family: "danger",
    icon: "x",
    tone: "bg-status-danger-base",
  },
  error: {
    label: "Could not check",
    family: "warning",
    icon: "alert",
    tone: "bg-status-warning-base",
  },
  stale: {
    label: "Out of date",
    family: "warning",
    icon: "clock",
    tone: "bg-status-warning-base",
  },
  not_applicable: {
    label: "Nothing to verify",
    family: "neutral",
    icon: "info",
    tone: "bg-status-neutral-base",
  },
  pending: {
    label: "First run in progress",
    family: "progress",
    icon: "clock",
    tone: "bg-status-progress-base",
  },
  not_connected: {
    label: "Not connected",
    family: "neutral",
    icon: "plug",
    tone: "bg-status-neutral-base",
  },
  manual: {
    label: "Evidenced manually",
    family: "neutral",
    icon: "users",
    tone: "bg-status-neutral-base",
  },
};

export const TEST_STATE: Record<TestStatus, { label: string; family: StatusFamily }> =
  {
    pass: { label: "Pass", family: "success" },
    fail: { label: "Fail", family: "danger" },
    error: { label: "Could not check", family: "warning" },
    stale: { label: "Out of date", family: "warning" },
    not_applicable: { label: "Not applicable", family: "neutral" },
    pending: { label: "Waiting", family: "progress" },
    not_connected: { label: "Not connected", family: "neutral" },
    not_available: { label: "Not automated yet", family: "pending" },
  };

export const OUTCOME_ICON: Record<Outcome, { icon: IconName; className: string }> = {
  pass: { icon: "check", className: "text-status-success-text" },
  fail: { icon: "x", className: "text-status-danger-text" },
  error: { icon: "alert", className: "text-status-warning-text" },
  not_applicable: { icon: "info", className: "text-text-faint" },
};

export const DAY_TONE: Record<Outcome | "none", string> = {
  pass: "bg-status-success-base",
  fail: "bg-status-danger-base",
  error: "bg-status-warning-base",
  not_applicable: "bg-status-neutral-base",
  none: "bg-surface-sunken",
};


export function useAutomationActions(controlId: string) {
  const { principal } = useAuth();
  const automation = useAutomation(controlId);
  const run = useRunConnections(automation.kick);
  return {
    automation,
    run,
    canConnect: hasPermission(principal, "connectors:manage"),
    canRequest: hasPermission(principal, "controls:manage"),
  };
}
