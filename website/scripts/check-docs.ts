/**
 * Quick validation for documentation MDX while it is being written.
 * Usage: npx tsx scripts/check-docs.ts [file ...]   (no arguments: every page)
 * The full build performs the same checks; this gives authors a fast loop.
 */
import { compile } from "@mdx-js/mdx";
import remarkGfm from "remark-gfm";
import GithubSlugger from "github-slugger";
import { parse as parseYaml } from "yaml";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { docsOrder } from "../content/docs/nav";

const root = path.resolve(import.meta.dirname, "..");
const docsDir = path.join(root, "content/docs");
const components = new Set(["Callout", "Steps", "Step", "Tabs", "Tab", "Screenshot", "Walkthrough", "Lifecycle", "Cards", "Card", "Status", "Kbd"]);
const cardIcons = new Set(["rocket", "compass", "shield", "file", "folder", "check", "clock", "warning", "users", "user", "building", "server", "bug", "plug", "gear", "book", "map", "stack", "sparkle", "lock", "eye", "list", "chart", "flag", "handshake", "scales", "clipboard", "target", "key", "bell", "globe", "graduation", "laptop", "lightning", "tree"]);
const calloutTypes = new Set(["note", "tip", "warning", "soon"]);

function listPages(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) return listPages(full);
    return entry.endsWith(".mdx") ? [full] : [];
  });
}

function splitFrontMatter(source: string): { data: Record<string, unknown>; body: string; offset: number } {
  const match = /^---\n([\s\S]*?)\n---\n/.exec(source);
  if (!match) throw new Error("missing front matter (--- block at the top)");
  return { data: parseYaml(match[1]) as Record<string, unknown>, body: source.slice(match[0].length), offset: match[0].split("\n").length - 1 };
}

function headingSlugs(body: string): Set<string> {
  const slugger = new GithubSlugger();
  const slugs = new Set<string>();
  let fenced = false;
  for (const line of body.split("\n")) {
    if (line.startsWith("```")) fenced = !fenced;
    if (fenced) continue;
    const match = /^(#{2,4})\s+(.+?)\s*$/.exec(line);
    if (match) slugs.add(slugger.slug(match[2].replace(/[*_`]/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")));
  }
  return slugs;
}

function screenshotExists(name: string): boolean {
  return existsSync(path.join(root, "public/docs/screens", `${name}.webp`)) || existsSync(path.join(root, "../docs/user-guide/images", `${name}.png`));
}

async function checkFile(file: string, slugsByPage: Map<string, Set<string>>): Promise<string[]> {
  const problems: string[] = [];
  const rel = path.relative(docsDir, file).replace(/\\/g, "/").replace(/\.mdx$/, "");
  const source = readFileSync(file, "utf8");
  let fm;
  try { fm = splitFrontMatter(source); } catch (error) { return [`${rel}: ${(error as Error).message}`]; }
  const { data, body } = fm;
  if (typeof data.title !== "string" || data.title.length < 3 || data.title.length > 70) problems.push(`${rel}: front matter title must be 3-70 characters`);
  if (typeof data.description !== "string" || data.description.length < 20 || data.description.length > 200) problems.push(`${rel}: front matter description must be 20-200 characters`);
  if (!["live", "preview", "soon"].includes(String(data.status))) problems.push(`${rel}: front matter status must be live, preview or soon`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(data.updated instanceof Date ? data.updated.toISOString().slice(0, 10) : data.updated))) problems.push(`${rel}: front matter updated must be YYYY-MM-DD`);
  if (!docsOrder.includes(rel)) problems.push(`${rel}: page is not listed in content/docs/nav.ts`);
  if (/^#\s/m.test(body.replace(/```[\s\S]*?```/g, ""))) problems.push(`${rel}: do not use a level-1 heading; the title renders as the H1`);

  try {
    await compile(body, { remarkPlugins: [remarkGfm] });
  } catch (error) {
    const err = error as { line?: number; reason?: string; message: string };
    problems.push(`${rel}: MDX does not compile${err.line ? ` (body line ${err.line})` : ""}: ${err.reason ?? err.message}`);
  }

  for (const match of body.matchAll(/<([A-Z][A-Za-z]*)\b/g)) {
    if (!components.has(match[1])) problems.push(`${rel}: unknown component <${match[1]}>`);
  }
  for (const match of body.matchAll(/<(Screenshot|Walkthrough)\b([^>]*)\/?>/g)) {
    const attrs = match[2];
    const name = /name="([^"]+)"/.exec(attrs)?.[1];
    const alt = /alt="([^"]*)"/.exec(attrs)?.[1];
    if (!name) problems.push(`${rel}: <${match[1]}> needs name="..."`);
    else if (!screenshotExists(name)) problems.push(`${rel}: screenshot "${name}" does not exist`);
    if (!alt || alt.trim().length < 12) problems.push(`${rel}: <${match[1]} name="${name}"> needs a descriptive alt (12+ characters)`);
  }
  for (const match of body.matchAll(/<Callout\b([^>]*)>/g)) {
    const type = /type="([^"]+)"/.exec(match[1])?.[1];
    if (!type || !calloutTypes.has(type)) problems.push(`${rel}: <Callout> type must be one of ${[...calloutTypes].join(", ")}`);
  }
  for (const match of body.matchAll(/<Card\b([^>]*)>/g)) {
    const icon = /icon="([^"]+)"/.exec(match[1])?.[1];
    if (icon && !cardIcons.has(icon)) problems.push(`${rel}: <Card> icon "${icon}" is not in the icon set`);
    const href = /href="([^"]+)"/.exec(match[1])?.[1];
    if (!href) problems.push(`${rel}: <Card> needs href`);
  }

  const links = [...body.matchAll(/\]\(([^)\s]+)\)/g), ...body.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
  for (const href of links) {
    if (href.startsWith("http://")) problems.push(`${rel}: use https for ${href}`);
    if (!href.startsWith("/docs") && !href.startsWith("#")) continue;
    const [pathPart, fragment] = href.split("#");
    if (href.startsWith("#")) {
      if (fragment && !slugsByPage.get(rel)?.has(fragment)) problems.push(`${rel}: link to missing heading #${fragment} on this page`);
      continue;
    }
    if (!pathPart.endsWith("/")) problems.push(`${rel}: internal link ${href} must end with a slash`);
    const target = pathPart.replace(/^\/docs\/?/, "").replace(/\/$/, "");
    if (target === "") continue;
    if (!docsOrder.includes(target)) { problems.push(`${rel}: link to unknown page ${href}`); continue; }
    if (fragment && slugsByPage.has(target) && !slugsByPage.get(target)!.has(fragment)) problems.push(`${rel}: link to missing heading ${href}`);
  }
  return problems;
}

async function main() {
  const all = existsSync(docsDir) ? listPages(docsDir) : [];
  const slugsByPage = new Map<string, Set<string>>();
  for (const file of all) {
    const rel = path.relative(docsDir, file).replace(/\\/g, "/").replace(/\.mdx$/, "");
    try { slugsByPage.set(rel, headingSlugs(splitFrontMatter(readFileSync(file, "utf8")).body)); } catch { /* reported below */ }
  }
  const targets = process.argv.slice(2).map((f) => path.resolve(f));
  const files = targets.length ? targets : all;
  const problems = (await Promise.all(files.map((f) => checkFile(f, slugsByPage)))).flat();
  const missing = docsOrder.filter((slug) => !slugsByPage.has(slug));
  if (!targets.length && missing.length) console.log(`Pages in nav without a file yet (${missing.length}): ${missing.join(", ")}`);
  if (problems.length) {
    console.error(problems.join("\n"));
    process.exitCode = 1;
  } else {
    console.log(`OK: ${files.length} page(s) checked`);
  }
}

void main();
