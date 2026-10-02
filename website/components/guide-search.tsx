"use client";

import { useEffect, useMemo, useState } from "react";
import type { SearchEntry } from "@/lib/guide";

function score(entry: SearchEntry, terms: string[]): number {
  const title = entry.title.toLowerCase();
  const section = entry.section.toLowerCase();
  const body = entry.body.toLowerCase();
  if (!terms.every((term) => title.includes(term) || section.includes(term) || body.includes(term))) return 0;
  return terms.reduce((sum, term) => sum + (title.includes(term) ? 5 : 0) + (section.includes(term) ? 3 : 0) + (body.includes(term) ? 1 : 0), 0);
}

export function GuideSearch() {
  const [entries, setEntries] = useState<SearchEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/guide-search.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Guide index unavailable");
        return response.json() as Promise<SearchEntry[]>;
      })
      .then((data) => { setEntries(data); setStatus("ready"); })
      .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setStatus("error"); });
    return () => controller.abort();
  }, []);

  const results = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    return entries.map((entry) => ({ entry, rank: score(entry, terms) }))
      .filter(({ rank }) => rank > 0)
      .sort((a, b) => b.rank - a.rank || a.entry.title.localeCompare(b.entry.title))
      .slice(0, 8).map(({ entry }) => entry);
  }, [entries, query]);

  return (
    <div className="guide-search">
      <form role="search" onSubmit={(event) => {
        event.preventDefault();
        if (results[0]) window.location.assign(results[0].href);
      }}>
        <label htmlFor="guide-query">Search the user guide</label>
        <div className="guide-search-field"><span aria-hidden="true">⌕</span><input id="guide-query" type="search" placeholder="Search controls, evidence, roles..." value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /><kbd>Enter</kbd></div>
      </form>
      {query.trim() && <div className="search-results" aria-live="polite">
        {status === "loading" && <p>Loading guide index…</p>}
        {status === "error" && <p>Search is unavailable. Browse the chapters below.</p>}
        {status === "ready" && results.length === 0 && <p>No results for “{query.trim()}”. Try another term or browse the chapters.</p>}
        {status === "ready" && results.length > 0 && <ul>{results.map((entry) => <li key={entry.href}><a href={entry.href}><strong>{entry.section}</strong><span>{entry.title} · {entry.body.slice(0, 125)}{entry.body.length > 125 ? "…" : ""}</span></a></li>)}</ul>}
      </div>}
    </div>
  );
}
