/**
 * What still needs filling in on a policy, found in plain text.
 *
 * One matcher for the read-only viewer and the editor, so a highlight means the
 * same thing in both, and the same rules as the backend's `placeholders.py`, so
 * the counts agree with the document:
 *
 * - field: `{{snake_case}}`, a decision such as `{{frequency}}`.
 * - prompt: a written instruction, `<approver of exceptions, e.g., CFO>`, or a
 *   square-bracketed instruction of three or more words.
 * - optional: an `[Optional ...]` marker, a keep-or-cut decision.
 * - company: the company name the platform filled in, so it can be checked.
 */

export type MarkKind = "field" | "prompt" | "optional" | "company";

export type PlaceholderMark = {
  from: number;
  to: number;
  kind: MarkKind;
  key: string;
  label: string;
};

const FIELD = /\{\{\s*([a-z0-9_]+)\s*\}\}/gi;
const PROMPT = /<([A-Za-z0-9{#](?:[^<>\n]|<[^<>\n]{1,80}>){0,299}?)>/g;
const BRACKET = /\[(?!Optional)([A-Za-z][^[\]\n]{2,199})\]/g;
const OPTIONAL = /\[Optional[^[\]\n]{0,80}\]/g;
const MIN_BRACKET_WORDS = 3;

/** Must match the backend's `placeholders.LABELS`. */
const FIELD_LABELS: Record<string, string> = {
  company_name: "Company name",
  frequency: "How often (e.g. quarterly)",
  time: "How many business hours",
};

/** Literal classes (see document-prose.css), a matching dot and a hover hint per kind. */
export const MARK_META: Record<
  MarkKind,
  { className: string; dot: string; legend: string; hint: (label: string) => string }
> = {
  field: {
    className: "ph ph-field",
    dot: "bg-status-warning-base",
    legend: "To decide",
    hint: (label) => `To decide: ${label}`,
  },
  prompt: {
    className: "ph ph-prompt",
    dot: "bg-status-pending-base",
    legend: "To replace",
    hint: () => "Replace with your own text",
  },
  optional: {
    className: "ph ph-optional",
    dot: "bg-status-neutral-base",
    legend: "Optional",
    hint: () => "Optional text: keep or remove",
  },
  company: {
    className: "ph ph-company",
    dot: "bg-action-accent",
    legend: "Company name",
    hint: () => "Filled in with your company name",
  },
};

export const MARK_ORDER: MarkKind[] = ["field", "prompt", "optional", "company"];

export function humanizeKey(key: string): string {
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function collapse(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Company names worth highlighting: trimmed, distinct, longest first. */
export function companyNameList(...names: (string | null | undefined)[]): string[] {
  const clean = names.map((n) => (n ?? "").trim()).filter((n) => n.length >= 2);
  return [...new Set(clean)].sort((a, b) => b.length - a.length);
}

/**
 * Every mark in one run of text, in order and never overlapping. Where two
 * overlap the earlier, longer one wins, so a prompt that contains a field is
 * highlighted once, as a prompt.
 */
export function findPlaceholderMarks(text: string, companyNames: readonly string[] = []): PlaceholderMark[] {
  const found: PlaceholderMark[] = [];
  const collect = (
    pattern: RegExp,
    kind: MarkKind,
    describe: (match: RegExpExecArray) => { key: string; label: string } | null,
  ) => {
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const described = describe(match);
      if (described) found.push({ from: match.index, to: match.index + match[0].length, kind, ...described });
      if (match[0].length === 0) pattern.lastIndex += 1;
    }
  };

  collect(FIELD, "field", (m) => {
    const key = m[1].toLowerCase();
    return { key, label: FIELD_LABELS[key] ?? humanizeKey(key) };
  });
  collect(PROMPT, "prompt", (m) => {
    const label = collapse(m[1]);
    return { key: `prompt:${label.toLowerCase()}`, label };
  });
  collect(BRACKET, "prompt", (m) => {
    const label = collapse(m[1]);
    return label.split(" ").length >= MIN_BRACKET_WORDS ? { key: `prompt:${label.toLowerCase()}`, label } : null;
  });
  collect(OPTIONAL, "optional", (m) => {
    const label = collapse(m[0].slice(1, -1));
    return { key: `optional:${label.toLowerCase()}`, label };
  });
  for (const name of companyNames) {
    collect(new RegExp(escapeRegExp(name), "g"), "company", () => ({ key: "company", label: "Company name" }));
  }

  found.sort((a, b) => a.from - b.from || b.to - b.from - (a.to - a.from));
  const kept: PlaceholderMark[] = [];
  let end = -1;
  for (const mark of found) {
    if (mark.from >= end) {
      kept.push(mark);
      end = mark.to;
    }
  }
  return kept;
}

/**
 * Sanitised HTML with every mark wrapped in a `<mark>`, for the read-only view,
 * and how many of each kind were found. Only text nodes are touched and the
 * marks are built with DOM calls, so nothing new can reach the page as markup.
 */
export function highlightHtml(
  html: string,
  companyNames: readonly string[],
): { html: string; counts: Record<MarkKind, number> } {
  const counts: Record<MarkKind, number> = { field: 0, prompt: 0, optional: 0, company: 0 };
  if (!html) return { html, counts };
  const parsed = new DOMParser().parseFromString(`<!doctype html><body>${html}</body>`, "text/html");
  const walker = parsed.createTreeWalker(parsed.body, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);

  for (const node of nodes) {
    const text = node.data;
    const marks = findPlaceholderMarks(text, companyNames);
    if (marks.length === 0) continue;
    const fragment = parsed.createDocumentFragment();
    let at = 0;
    for (const mark of marks) {
      if (mark.from > at) fragment.append(text.slice(at, mark.from));
      const element = parsed.createElement("mark");
      element.className = MARK_META[mark.kind].className;
      element.title = MARK_META[mark.kind].hint(mark.label);
      element.textContent = text.slice(mark.from, mark.to);
      fragment.append(element);
      counts[mark.kind] += 1;
      at = mark.to;
    }
    if (at < text.length) fragment.append(text.slice(at));
    node.replaceWith(fragment);
  }
  return { html: parsed.body.innerHTML, counts };
}
