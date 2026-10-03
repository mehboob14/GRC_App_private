import type { StatusFamily } from "@/components/ui";
import type {
  Availability,
  ComposeMode,
  Composition,
  EvidenceState,
  ExpectedEvidence,
  SourceState,
} from "../api";

/**
 * The shared words for "what evidences this control": the Checks tab, the controls
 * register and the criterion view all draw from here, so a source never reads one
 * way in one place and another way in the next.
 */

export const MODE: Record<ComposeMode, { label: string; sentence: string }> = {
  automated: {
    label: "Systems",
    sentence:
      "Systems and Verity check this control. People provide only the documents that describe it.",
  },
  hybrid: {
    label: "Systems and people",
    sentence:
      "Systems check what they can. People provide the evidence a system cannot.",
  },
  manual: {
    label: "People",
    sentence:
      "No system or Verity module checks this control. People provide the evidence.",
  },
};

/** The sentence under the mode: what is true today, not only what is designed. */
export function compositionSentence(c: Composition): string {
  if (c.checks_total === 0) return MODE.manual.sentence;
  if (c.checks_running === 0 && c.checks_ready === 0) {
    return "Designed to be checked by systems and Verity. None of the checks can run yet, so people provide the evidence for now.";
  }
  if (c.checks_running === 0) {
    return "Checks are ready. Connect a system and they run. Until then, people provide the evidence.";
  }
  return MODE[c.mode].sentence;
}

export const SOURCE_STATE: Record<
  SourceState,
  { label: string; family: StatusFamily }
> = {
  connected: { label: "Connected", family: "success" },
  available: { label: "Ready to connect", family: "progress" },
  planned: { label: "Planned", family: "pending" },
  not_planned: { label: "Not in plan", family: "neutral" },
};

export const AVAILABILITY: Record<Availability, string> = {
  running: "Running",
  ready: "Ready to connect",
  planned: "Planned",
  not_planned: "Not in plan",
};

export const CADENCE: Record<ExpectedEvidence["cadence"], string> = {
  annual: "Every year",
  quarterly: "Every quarter",
  monthly: "Every month",
  on_change: "When it changes",
  per_event: "Each time it happens",
  once: "Once",
  ongoing: "Kept current",
};

/** Verity modules that can hold evidence, and where they live in the app. */
export const MODULE: Record<string, { label: string; to: string }> = {
  documents: { label: "Policies and documents", to: "/documents" },
  risks: { label: "Risks", to: "/risks" },
  vendors: { label: "Vendors", to: "/vendors" },
  assets: { label: "Assets", to: "/assets" },
  vulnerabilities: { label: "Vulnerabilities", to: "/vulnerabilities" },
  tasks: { label: "Tasks", to: "/tasks" },
  controls: { label: "Controls", to: "/controls" },
};

export const EVIDENCE_STATE: Record<
  EvidenceState,
  { label: string; family: StatusFamily }
> = {
  automatic: { label: "Collected automatically", family: "success" },
  partial: { label: "Partly collected", family: "progress" },
  when_connected: { label: "Collected once connected", family: "progress" },
  planned: { label: "Provide it for now", family: "pending" },
  platform: { label: "Kept in Verity", family: "neutral" },
  manual: { label: "You provide this", family: "neutral" },
};
