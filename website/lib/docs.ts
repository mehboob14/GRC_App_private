import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import type { ComponentType } from "react";
import * as runtime from "react/jsx-runtime";
import { createProcessor, evaluate } from "@mdx-js/mdx";
import GithubSlugger from "github-slugger";
import rehypeSlug from "rehype-slug";
import remarkGfm from "remark-gfm";
import { visit } from "unist-util-visit";
import { parse as parseYaml } from "yaml";
import { docsNav, docsOrder, type DocsNavGroup } from "@/content/docs/nav";

/**
 * Website-owned documentation: MDX under content/docs, ordered by
 * content/docs/nav.ts. Everything here runs at build time; a problem in the
 * content throws with the file and the reference so the build fails loudly.
 */

export type DocStatus = "live" | "preview" | "soon";

export interface DocMeta {
  slug: string;
  title: string;
  description: string;
  status: DocStatus;
  updated: string;
  label: string;
  group: Pick<DocsNavGroup, "id" | "title" | "icon">;
}

export interface TocItem {
  id: string;
  text: string;
  depth: 2 | 3;
}

export interface SearchSection {
  id: string;
  heading: string;
  text: string;
}

export const docsDir = path.join(process.cwd(), "content/docs");
const screensDir = path.join(process.cwd(), "public/docs/screens");

/** Components MDX pages may use. Kept in step with components/docs/mdx-components.tsx. */
export const docComponentNames = ["Callout", "Steps", "Step", "Tabs", "Tab", "Screenshot", "Walkthrough", "Lifecycle", "Cards", "Card", "Status", "Kbd"] as const;

/** Old /docs/NN-chapter/ URLs from the first site, mapped to their new homes. */
export const legacyRedirects: Record<string, string> = {
  "01-getting-started": "get-started/introduction",
  "02-finding-your-way-around": "get-started/navigating-verity",
  "03-frameworks-and-controls": "compliance/controls",
  "04-evidence": "compliance/evidence",
  "05-policies-and-documents": "policies/documents-and-policies",
  "06-tasks": "tasks/overview",
  "07-risks": "risk/risk-register",
  "08-vendors": "vendors/overview",
  "09-assets": "assets/inventory",
  "10-vulnerabilities": "vulnerabilities/findings-and-priority",
  "11-connections": "integrations/overview",
  "12-settings-and-administration": "admin/people",
  "13-glossary": "reference/glossary",
};

function fail(message: string): never {
  throw new Error(`[docs] ${message}`);
}

interface Source {
  meta: DocMeta;
  body: string;
  file: string;
}

let sources: Map<string, Source> | null = null;

function listFiles(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).flatMap((entry) => {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) return listFiles(full);
    return entry.endsWith(".mdx") ? [full] : [];
  });
}

function navEntry(slug: string) {
  for (const group of docsNav) {
    const item = group.items.find((candidate) => candidate.slug === slug);
    if (item) return { item, group };
  }
  return null;
}

function loadSources(): Map<string, Source> {
  if (sources) return sources;
  const map = new Map<string, Source>();
  for (const file of listFiles(docsDir)) {
    const slug = path.relative(docsDir, file).replace(/\\/g, "/").replace(/\.mdx$/, "");
    const raw = readFileSync(file, "utf8");
    const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/.exec(raw);
    if (!match) fail(`${slug}.mdx has no front matter`);
    const data = parseYaml(match[1]) as Record<string, unknown>;
    const updated = data.updated instanceof Date ? data.updated.toISOString().slice(0, 10) : String(data.updated ?? "");
    if (typeof data.title !== "string" || !data.title.trim()) fail(`${slug}.mdx: front matter needs a title`);
    if (typeof data.description !== "string" || data.description.length < 20) fail(`${slug}.mdx: front matter needs a description of 20+ characters`);
    if (!["live", "preview", "soon"].includes(String(data.status))) fail(`${slug}.mdx: status must be live, preview or soon`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(updated)) fail(`${slug}.mdx: updated must be YYYY-MM-DD`);
    const entry = navEntry(slug);
    if (!entry) fail(`${slug}.mdx is not listed in content/docs/nav.ts`);
    map.set(slug, {
      file,
      body: raw.slice(match[0].length),
      meta: {
        slug,
        title: data.title,
        description: data.description as string,
        status: data.status as DocStatus,
        updated,
        label: entry.item.label,
        group: { id: entry.group.id, title: entry.group.title, icon: entry.group.icon },
      },
    });
  }
  for (const slug of docsOrder) if (!map.has(slug)) fail(`content/docs/nav.ts lists "${slug}" but content/docs/${slug}.mdx does not exist`);
  sources = map;
  return map;
}

export function getAllDocs(): DocMeta[] {
  const map = loadSources();
  return docsOrder.map((slug) => map.get(slug)!.meta);
}

export function getDocMeta(slug: string): DocMeta | undefined {
  return loadSources().get(slug)?.meta;
}

/** Sidebar data: nav order with each page's status from its front matter. */
export function getSidebarGroups() {
  const meta = new Map(getAllDocs().map((page) => [page.slug, page]));
  return docsNav.map((group) => ({
    id: group.id,
    title: group.title,
    icon: group.icon,
    items: group.items.map((item) => ({ slug: item.slug, label: item.label, status: meta.get(item.slug)?.status ?? ("live" as DocStatus) })),
  }));
}

export function getNeighbours(slug: string): { prev?: DocMeta; next?: DocMeta } {
  const index = docsOrder.indexOf(slug);
  const all = getAllDocs();
  return { prev: index > 0 ? all[index - 1] : undefined, next: index >= 0 && index < all.length - 1 ? all[index + 1] : undefined };
}

/* ------------------------------------------------------------- analysis */

type Node = { type: string; children?: Node[]; value?: string; name?: string | null; attributes?: { type: string; name?: string; value?: unknown }[]; url?: string; depth?: number; tagName?: string; properties?: Record<string, unknown> };

function attr(node: Node, name: string): string | undefined {
  const found = node.attributes?.find((a) => a.type === "mdxJsxAttribute" && a.name === name);
  return typeof found?.value === "string" ? found.value : undefined;
}

function plainText(node: Node): string {
  if (node.type === "text" || node.type === "inlineCode") return node.value ?? "";
  return (node.children ?? []).map(plainText).join("");
}

interface Analysis {
  headings: Set<string>;
  toc: TocItem[];
  links: string[];
  screenshots: { name: string; alt?: string; component: string }[];
  components: Set<string>;
  sections: SearchSection[];
}

const analyses = new Map<string, Analysis>();

/** Parse a page's MDX into an mdast and pull out what validation, contents and search need. */
function analyse(slug: string): Analysis {
  const cached = analyses.get(slug);
  if (cached) return cached;
  const source = loadSources().get(slug);
  if (!source) fail(`unknown page ${slug}`);
  const processor = createProcessor({ remarkPlugins: [remarkGfm] });
  let tree: Node;
  try {
    tree = processor.parse(source.body) as unknown as Node;
  } catch (error) {
    fail(`${slug}.mdx does not parse: ${(error as Error).message}`);
  }
  const slugger = new GithubSlugger();
  const result: Analysis = { headings: new Set(), toc: [], links: [], screenshots: [], components: new Set(), sections: [] };
  let current: SearchSection = { id: "", heading: source.meta.title, text: "" };
  result.sections.push(current);

  const push = (text: string) => {
    if (text) current.text += (current.text ? " " : "") + text.replace(/\s+/g, " ").trim();
  };

  const walk = (node: Node) => {
    if (node.type === "heading") {
      const text = plainText(node).trim();
      const id = slugger.slug(text);
      result.headings.add(id);
      if (node.depth === 2 || node.depth === 3) result.toc.push({ id, text, depth: node.depth as 2 | 3 });
      current = { id, heading: text, text: "" };
      result.sections.push(current);
      return;
    }
    if (node.type === "link" && node.url) result.links.push(node.url);
    if (node.type === "mdxJsxFlowElement" || node.type === "mdxJsxTextElement") {
      const name = node.name ?? "";
      result.components.add(name);
      if (name === "Screenshot" || name === "Walkthrough") result.screenshots.push({ name: attr(node, "name") ?? "", alt: attr(node, "alt"), component: name });
      const href = attr(node, "href");
      if (href) result.links.push(href);
      for (const key of ["title", "caption", "alt"]) {
        const value = attr(node, key);
        if (value && name !== "Screenshot") push(value);
      }
    }
    if (node.type === "text" || node.type === "inlineCode") {
      push(node.value ?? "");
      return;
    }
    node.children?.forEach(walk);
  };
  walk(tree);
  result.sections = result.sections.filter((section) => section.text || section.id);
  analyses.set(slug, result);
  return result;
}

export function getToc(slug: string): TocItem[] {
  return analyse(slug).toc;
}

/** Build-time content checks. Throws with every problem found, so the build fails with a full list. */
export function validateDocs(): void {
  const problems: string[] = [];
  const all = getAllDocs();
  const known = new Set<string>(docComponentNames);
  for (const page of all) {
    const result = analyse(page.slug);
    for (const name of result.components) if (!known.has(name)) problems.push(`${page.slug}.mdx uses unknown component <${name}>`);
    for (const shot of result.screenshots) {
      if (!shot.name) problems.push(`${page.slug}.mdx: <${shot.component}> needs a name`);
      else if (!existsSync(path.join(screensDir, `${shot.name}.webp`))) problems.push(`${page.slug}.mdx: screenshot "${shot.name}" is missing from public/docs/screens`);
      if (!shot.alt || shot.alt.trim().length < 12) problems.push(`${page.slug}.mdx: <${shot.component} name="${shot.name}"> needs descriptive alt text`);
    }
    for (const href of result.links) {
      if (href.startsWith("http://")) problems.push(`${page.slug}.mdx links over plain http: ${href}`);
      if (!href.startsWith("/docs") && !href.startsWith("#")) continue;
      const [pathname, fragment] = href.split("#");
      const target = href.startsWith("#") ? page.slug : pathname.replace(/^\/docs\/?/, "").replace(/\/$/, "");
      if (!href.startsWith("#") && pathname !== "/docs/" && !pathname.endsWith("/")) problems.push(`${page.slug}.mdx: internal link ${href} must end with "/"`);
      if (target === "") continue;
      if (!docsOrder.includes(target)) { problems.push(`${page.slug}.mdx links to a page that does not exist: ${href}`); continue; }
      if (fragment && !analyse(target).headings.has(fragment)) problems.push(`${page.slug}.mdx links to a missing heading: ${href}`);
    }
  }
  if (problems.length) fail(`documentation has ${problems.length} problem(s):\n  - ${problems.join("\n  - ")}`);
}

/* ------------------------------------------------------------ rendering */

const compiled = new Map<string, Promise<ComponentType<{ components?: Record<string, unknown> }>>>();

/** Compile a page to a React component. Cached for the build. */
export function getDocContent(slug: string) {
  const existing = compiled.get(slug);
  if (existing) return existing;
  const source = loadSources().get(slug);
  if (!source) fail(`unknown page ${slug}`);
  const promise = evaluate(source.body, {
    ...(runtime as unknown as Parameters<typeof evaluate>[1]),
    remarkPlugins: [remarkGfm],
    rehypePlugins: [rehypeSlug, rehypeExternalLinks],
  }).then((module) => module.default as ComponentType<{ components?: Record<string, unknown> }>);
  compiled.set(slug, promise);
  return promise;
}

/** Mark absolute links as external so the renderer can open them safely. */
function rehypeExternalLinks() {
  return (tree: Node) => {
    visit(tree as never, "element", (node: Node) => {
      if (node.tagName === "a" && typeof node.properties?.href === "string" && /^https?:/.test(node.properties.href)) {
        node.properties.rel = "noopener noreferrer";
        node.properties.target = "_blank";
      }
    });
  };
}

/* --------------------------------------------------------------- search */

export interface SearchDoc {
  slug: string;
  title: string;
  description: string;
  group: string;
  status: DocStatus;
  sections: SearchSection[];
}

export function buildSearchIndex(): SearchDoc[] {
  return getAllDocs().map((page) => ({
    slug: page.slug,
    title: page.title,
    description: page.description,
    group: page.group.title,
    status: page.status,
    sections: analyse(page.slug).sections.map((section) => ({ ...section, text: section.text.slice(0, 1600) })),
  }));
}

export function readingMinutes(slug: string): number {
  const words = analyse(slug).sections.reduce((total, section) => total + section.text.split(/\s+/).length, 0);
  return Math.max(1, Math.round(words / 220));
}
