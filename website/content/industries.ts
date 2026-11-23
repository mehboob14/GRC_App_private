import type { IconName } from "@/components/ui/icon";
import type { Region } from "./frameworks";
import type { IndustrySlug } from "./navigation";

export interface IndustryPage {
  slug: IndustrySlug;
  eyebrow: string;
  headline: string;
  lead: string;
  /** Kinds of organisation this page speaks to. */
  audiences: string[];
  /** Real obligations, in verified terms, each tied to the rule it comes from. */
  obligations: { region: Region; title: string; text: string; source: string }[];
  /** How Verity helps, each mapped to platform module slugs (see content/catalog.ts). */
  helps: { icon: IconName; title: string; text: string; modules: string[] }[];
  /** Framework ids from content/frameworks.data.ts, most relevant first. */
  frameworks: string[];
  workflow: { title: string; intro: string; steps: { title: string; text: string }[] };
  roles: string[];
  faqs: { q: string; a: string }[];
}

export { industryPages } from "./industries.data";
