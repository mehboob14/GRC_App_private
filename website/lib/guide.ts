import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import GithubSlugger from "github-slugger";
import { toString } from "mdast-util-to-string";
import type { Heading, Root } from "mdast";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import { unified } from "unified";
import { visit } from "unist-util-visit";

export const guideRoot = path.resolve(process.cwd(), "../docs/user-guide");
const parser = unified().use(remarkParse).use(remarkGfm);
const chapterPattern = /^\d{2}-[a-z0-9-]+\.md$/;

export type GuideHeading = { depth: number; text: string; id: string };
export type GuidePage = {
  filename: string;
  slug: string;
  title: string;
  markdown: string;
  description: string;
  headings: GuideHeading[];
};
export type SearchEntry = { title: string; section: string; href: string; body: string };

export function guidePath(slug: string): string {
  return slug ? `/docs/${slug}/` : "/docs/";
}

function headingsIn(tree: Root): GuideHeading[] {
  const slugger = new GithubSlugger();
  const headings: GuideHeading[] = [];
  visit(tree, "heading", (node: Heading) => {
    const text = toString(node);
    headings.push({ depth: node.depth, text, id: slugger.slug(text) });
  });
  return headings;
}

function firstParagraph(tree: Root): string {
  const paragraph = tree.children.find((node) => node.type === "paragraph");
  return paragraph ? toString(paragraph).replace(/\s+/g, " ").slice(0, 170) : "Verity user guide";
}

export function getGuidePages(): GuidePage[] {
  const chapters = readdirSync(guideRoot).filter((name) => chapterPattern.test(name)).sort();
  const files = ["README.md", ...chapters];
  return files.map((filename) => {
    const markdown = readFileSync(path.join(guideRoot, filename), "utf8");
    const tree = parser.parse(markdown);
    const headings = headingsIn(tree);
    const title = (headings[0]?.text ?? filename).replace(/^\d+\.\s*/, "");
    return {
      filename,
      slug: filename === "README.md" ? "" : filename.slice(0, -3),
      title,
      markdown,
      description: firstParagraph(tree),
      headings,
    };
  });
}

export function getGuidePage(slug: string): GuidePage | undefined {
  return getGuidePages().find((page) => page.slug === slug);
}

export function imageInfo(filename: string): { src: string; width: number; height: number } {
  if (!/^[a-z0-9-]+\.png$/.test(filename)) throw new Error(`Unsupported guide image: ${filename}`);
  const fullPath = path.join(guideRoot, "images", filename);
  if (!existsSync(fullPath)) throw new Error(`Missing guide image: ${filename}`);
  const header = readFileSync(fullPath).subarray(0, 24);
  if (header.toString("hex", 0, 8) !== "89504e470d0a1a0a") throw new Error(`Invalid PNG: ${filename}`);
  return { src: `/guide-images/${filename}`, width: header.readUInt32BE(16), height: header.readUInt32BE(20) };
}

export function resolveGuideHref(source: GuidePage, href: string, pages = getGuidePages()): string {
  if (/^https:\/\//.test(href) || /^mailto:/.test(href)) return href;
  if (/^[a-z]+:/i.test(href) || href.startsWith("//")) throw new Error(`${source.filename}: disallowed link ${href}`);
  const [targetFile, fragment = ""] = href.split("#", 2);
  const target = targetFile ? pages.find((page) => page.filename === targetFile) : source;
  if (!target) throw new Error(`${source.filename}: missing guide target ${href}`);
  if (fragment && !target.headings.some((heading) => heading.id === decodeURIComponent(fragment))) {
    throw new Error(`${source.filename}: missing guide heading ${href}`);
  }
  return `${guidePath(target.slug)}${fragment ? `#${fragment}` : ""}`;
}

export function validateGuide(pages = getGuidePages()): void {
  for (const page of pages) {
    const tree = parser.parse(page.markdown);
    visit(tree, "link", (node) => { resolveGuideHref(page, node.url, pages); });
    visit(tree, "image", (node) => {
      if (!node.alt?.trim()) throw new Error(`${page.filename}: image ${node.url} needs alt text`);
      if (!node.url.startsWith("images/")) throw new Error(`${page.filename}: disallowed image ${node.url}`);
      imageInfo(node.url.slice("images/".length));
    });
  }
}

export function getSearchEntries(pages = getGuidePages()): SearchEntry[] {
  return pages.flatMap((page) => {
    const tree = parser.parse(page.markdown);
    const entries: SearchEntry[] = [];
    let current: SearchEntry = { title: page.title, section: "Overview", href: guidePath(page.slug), body: "" };
    let headingIndex = 0;
    for (const node of tree.children) {
      if (node.type === "heading") {
        if (current.body.trim()) entries.push({ ...current, body: current.body.trim().slice(0, 1200) });
        const heading = page.headings[headingIndex++];
        current = {
          title: page.title,
          section: heading.text,
          href: `${guidePath(page.slug)}#${heading.id}`,
          body: "",
        };
      } else {
        current.body += ` ${toString(node)}`;
      }
    }
    if (current.body.trim()) entries.push({ ...current, body: current.body.trim().slice(0, 1200) });
    return entries;
  });
}
