/**
 * Client-side ranking for the documentation search index (built at
 * /search-index.json). Pure functions, so they are unit-tested.
 */

export interface IndexSection {
  id: string;
  heading: string;
  text: string;
}

export interface IndexDoc {
  slug: string;
  title: string;
  description: string;
  group: string;
  status: "live" | "preview" | "soon";
  sections: IndexSection[];
}

export interface SearchResult {
  slug: string;
  href: string;
  title: string;
  group: string;
  status: IndexDoc["status"];
  heading?: string;
  excerpt: string;
  score: number;
}

const stopwords = new Set(["a", "an", "the", "to", "of", "and", "or", "in", "on", "for", "is", "it", "how", "do", "i", "my", "with", "can", "what", "where", "when", "does"]);

/** Lower-cased search terms. Stop words are dropped unless the query has nothing else. */
export function tokenize(query: string): string[] {
  const words = query
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, " ")
    .split(/\s+/)
    .filter((term) => term.length > 0);
  const meaningful = words.filter((term) => !stopwords.has(term) && term.length > 1);
  return (meaningful.length ? meaningful : words).slice(0, 8);
}

function wordHit(haystack: string, term: string): number {
  // 3 for a whole word, 2 for a word prefix, 1 for any substring, 0 otherwise.
  const index = haystack.indexOf(term);
  if (index < 0) return 0;
  const boundary = new RegExp(`(^|[^\\p{L}\\p{N}])${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "u");
  if (!boundary.test(haystack)) return 1;
  const whole = new RegExp(`(^|[^\\p{L}\\p{N}])${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|[^\\p{L}\\p{N}])`, "u");
  return whole.test(haystack) ? 3 : 2;
}

/** A short excerpt around the first matching term. */
export function excerpt(text: string, terms: string[], length = 150): string {
  const lower = text.toLowerCase();
  const positions = terms.map((term) => lower.indexOf(term)).filter((position) => position >= 0);
  const at = positions.length ? Math.min(...positions) : 0;
  const start = Math.max(0, at - Math.floor(length / 3));
  const slice = text.slice(start, start + length).trim();
  return `${start > 0 ? "…" : ""}${slice}${start + length < text.length ? "…" : ""}`;
}

/**
 * Every term must appear somewhere in the page. Title hits outrank heading
 * hits, which outrank description and body hits. Returns the best section of
 * each matching page, best first.
 */
export function search(index: IndexDoc[], query: string, limit = 12): SearchResult[] {
  const terms = tokenize(query);
  if (!terms.length) return [];
  const results: SearchResult[] = [];
  for (const doc of index) {
    const title = doc.title.toLowerCase();
    const description = doc.description.toLowerCase();
    const pageText = `${title} ${description} ${doc.sections.map((s) => `${s.heading} ${s.text}`).join(" ")}`.toLowerCase();
    if (!terms.every((term) => pageText.includes(term))) continue;

    let best: { section?: IndexSection; score: number } = { score: -1 };
    for (const section of doc.sections) {
      const heading = section.heading.toLowerCase();
      const body = section.text.toLowerCase();
      let score = 0;
      for (const term of terms) {
        // The intro section's "heading" is the page title, which is scored once at page level.
        if (section.id) score += wordHit(heading, term) * 6;
        score += Math.min(3, wordHit(body, term));
      }
      if (score > best.score) best = { section, score };
    }
    let pageScore = best.score;
    for (const term of terms) {
      pageScore += wordHit(title, term) * 10;
      pageScore += wordHit(description, term) * 2;
    }
    if (doc.status === "soon") pageScore -= 2;
    const section = best.section;
    const sectionIsPage = !section || !section.id;
    results.push({
      slug: doc.slug,
      href: `/docs/${doc.slug}/${sectionIsPage ? "" : `#${section!.id}`}`,
      title: doc.title,
      group: doc.group,
      status: doc.status,
      heading: sectionIsPage ? undefined : section!.heading,
      excerpt: excerpt(section?.text || doc.description, terms),
      score: pageScore,
    });
  }
  return results.sort((a, b) => b.score - a.score || a.title.localeCompare(b.title)).slice(0, limit);
}
