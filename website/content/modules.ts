import type { IconName } from "@/components/ui/icon";
import type { Family } from "@/components/visuals/ui-kit";
import type { Status } from "./catalog";

/** Code-native compositions that a module page can show. */
export type CompositionName = "proof-flow" | "vendor-register" | "estate-dashboard" | "policy-campaign" | "assistant-draft" | "control-mapping";

/** Screenshots of the application (demonstration workspace) available under public/docs/screens/. */
export type ScreenshotName =
  | "asset-detail" | "assets-overview" | "assets-register" | "assets-settings" | "audit-log" | "connections" | "control-detail" | "controls-register"
  | "dialog-add-risk" | "dialog-add-vendor" | "dialog-custom-field" | "dialog-request-vendor" | "document-detail" | "document-editor" | "documents-register"
  | "evidence-detail" | "evidence-register" | "frameworks-dashboard" | "frameworks-list" | "quick-start" | "risk-detail" | "risks-overview" | "risks-register"
  | "risks-settings" | "settings-people" | "settings-roles" | "task-detail" | "tasks-overview" | "tasks-register" | "tasks-settings" | "vendor-assessments"
  | "vendor-detail" | "vendor-lifecycle" | "vendors-findings" | "vendors-intake" | "vendors-overview" | "vendors-policy" | "vendors-questionnaires"
  | "vendors-register" | "vulnerabilities-overview" | "vulnerabilities-register" | "vulnerabilities-settings" | "vulnerability-detail";

export type SectionVisual =
  | { kind: "screenshot"; name: ScreenshotName; alt: string }
  | { kind: "composition"; name: CompositionName }
  /** A product-style card for concepts without a screen yet (coming-soon modules). */
  | { kind: "list"; title: string; icon: IconName; rows: { label: string; meta?: string; status: string; tone: Family }[]; note?: string };

export interface ModuleSection {
  eyebrow: string;
  title: string;
  text: string;
  bullets: string[];
  visual: SectionVisual;
}

export interface ModulePage {
  slug: string;
  eyebrow: string;
  headline: string;
  lead: string;
  /** At-a-glance facts. Only verifiable numbers or plain facts; omit when there are none. */
  facts?: { label: string; value: string }[];
  heroVisual: SectionVisual;
  sections: ModuleSection[];
  capabilities: { icon: IconName; title: string; text: string; status: Status }[];
  related: string[];
  docs: { title: string; href: string }[];
  faqs: { q: string; a: string }[];
  /** Coming-soon modules: what to use today instead. */
  today?: { title: string; text: string; href: string }[];
}

export { modulePages } from "./modules.data";
