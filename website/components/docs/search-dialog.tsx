"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { search, tokenize, type IndexDoc, type SearchResult } from "@/lib/search";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";

const SearchContext = createContext<(query?: string) => void>(() => {});

export function useOpenSearch() {
  return useContext(SearchContext);
}

let indexPromise: Promise<IndexDoc[]> | null = null;
function loadIndex(): Promise<IndexDoc[]> {
  indexPromise ??= fetch("/search-index.json").then((response) => {
    if (!response.ok) throw new Error("search index unavailable");
    return response.json() as Promise<IndexDoc[]>;
  });
  return indexPromise;
}

function Highlight({ text, terms }: { text: string; terms: string[] }) {
  if (!terms.length) return <>{text}</>;
  const pattern = new RegExp(`(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  const parts = text.split(pattern);
  return <>{parts.map((part, index) => (index % 2 === 1 ? <mark key={index} className="rounded-sm bg-amber-200/70 px-0.5 text-inherit [[data-docs-theme=dark]_&]:bg-amber-500/30">{part}</mark> : part))}</>;
}

const suggestions = ["Invite someone", "Evidence freshness", "Accept a risk", "Vendor tiering", "Import assets", "Audit log"];

/** ⌘K / Ctrl+K / "/" documentation search, available on every docs page. */
export function SearchProvider({ children }: { children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<IndexDoc[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [active, setActive] = useState(0);

  const open = useCallback((initial?: string) => {
    opener.current = document.activeElement as HTMLElement | null;
    if (typeof initial === "string") { setQuery(initial); setActive(0); }
    dialog.current?.showModal();
    window.requestAnimationFrame(() => input.current?.select());
    loadIndex().then(setIndex).catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const typing = target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
        event.preventDefault();
        if (dialog.current?.open) dialog.current.close();
        else open();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const results: SearchResult[] = useMemo(() => (index ? search(index, query) : []), [index, query]);
  const terms = useMemo(() => tokenize(query), [query]);

  const go = (href: string) => {
    dialog.current?.close();
    router.push(href);
  };

  return (
    <SearchContext.Provider value={open}>
      {children}
      <dialog
        ref={dialog}
        className="demo-dialog m-auto mt-[10vh] w-[min(680px,calc(100vw-24px))] overflow-hidden rounded-2xl border border-line bg-surface p-0 text-body shadow-menu backdrop:bg-ink/40 backdrop:backdrop-blur-[2px]"
        aria-label="Search the documentation"
        onClick={(event) => { if (event.target === dialog.current) dialog.current?.close(); }}
        onClose={() => opener.current?.focus?.()}
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Icon name="search" size={19} className="shrink-0 text-dim" />
          <input
            ref={input}
            value={query}
            onChange={(event) => { setQuery(event.target.value); setActive(0); }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") { event.preventDefault(); setActive((value) => Math.min(value + 1, results.length - 1)); }
              if (event.key === "ArrowUp") { event.preventDefault(); setActive((value) => Math.max(value - 1, 0)); }
              if (event.key === "Enter" && results[active]) { event.preventDefault(); go(results[active].href); }
            }}
            placeholder="Search the documentation"
            className="h-14 w-full bg-transparent text-[16px] text-ink outline-none placeholder:text-faint"
            role="combobox"
            aria-expanded={results.length > 0}
            aria-controls="docs-search-results"
            aria-activedescendant={results[active] ? `docs-result-${active}` : undefined}
            aria-autocomplete="list"
          />
          <kbd className="hidden rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-dim sm:inline">Esc</kbd>
        </div>
        <div className="max-h-[min(60vh,520px)] overflow-y-auto p-2">
          {failed && <p className="p-4 text-[14px] text-dim">Search is unavailable right now. Browse the sections in the sidebar instead.</p>}
          {!failed && !query && (
            <div className="p-3">
              <p className="eyebrow mb-3">Try</p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => { setQuery(suggestion); setActive(0); }} className="chip hover:border-line-strong hover:text-ink">{suggestion}</button>
                ))}
              </div>
            </div>
          )}
          {!failed && query && index && results.length === 0 && (
            <div className="p-6 text-center">
              <p className="text-[15px] font-medium text-ink">No results for “{query}”</p>
              <p className="mt-1 text-[14px] text-dim">Try fewer or different words, or <button type="button" className="font-medium text-accent hover:underline" onClick={() => go("/docs/")}>browse the documentation home</button>.</p>
            </div>
          )}
          {!failed && query && !index && <p className="p-4 text-[14px] text-dim">Loading…</p>}
          <ul id="docs-search-results" role="listbox" aria-label="Results">
            {results.map((result, position) => (
              <li key={`${result.slug}-${position}`} id={`docs-result-${position}`} role="option" aria-selected={position === active}>
                <button
                  type="button"
                  onMouseMove={() => setActive(position)}
                  onClick={() => go(result.href)}
                  className={cn("flex w-full flex-col gap-1 rounded-lg px-3 py-2.5 text-left transition-colors", position === active ? "bg-muted" : "hover:bg-subtle")}
                >
                  <span className="flex flex-wrap items-center gap-2 text-[12px] text-dim">
                    {result.group}
                    <Icon name="caret-right" size={10} weight="bold" />
                    <span className="font-medium text-ink">{result.title}</span>
                    {result.status !== "live" && <StatusBadge status={result.status} size="xs" />}
                  </span>
                  {result.heading && <span className="text-[14.5px] font-semibold text-ink"><Highlight text={result.heading} terms={terms} /></span>}
                  <span className="line-clamp-2 text-[13.5px] leading-snug text-dim"><Highlight text={result.excerpt} terms={terms} /></span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="flex items-center gap-4 border-t border-line bg-subtle px-4 py-2.5 font-mono text-[11px] text-dim">
          <span><kbd className="rounded border border-line bg-surface px-1">↑</kbd> <kbd className="rounded border border-line bg-surface px-1">↓</kbd> to move</span>
          <span><kbd className="rounded border border-line bg-surface px-1">↵</kbd> to open</span>
          <span className="ms-auto">{index ? `${index.length} pages` : ""}</span>
        </div>
      </dialog>
    </SearchContext.Provider>
  );
}

export function SearchButton({ className, compact = false }: { className?: string; compact?: boolean }) {
  const open = useOpenSearch();
  return (
    <button type="button" onClick={() => open()} className={cn("flex items-center gap-2.5 rounded-lg border border-line-strong bg-surface text-[14px] text-dim shadow-[0_1px_2px_rgb(16_24_40/0.04)] transition hover:border-[#b6bdc9] hover:text-ink", compact ? "h-9 w-9 justify-center" : "h-9 px-3", className)} aria-label="Search the documentation" aria-keyshortcuts="Meta+K Control+K /">
      <Icon name="search" size={16} />
      {!compact && <span className="me-6">Search docs</span>}
      {!compact && <span className="ms-auto flex gap-0.5 font-mono text-[10.5px]"><kbd className="rounded border border-line px-1">⌘</kbd><kbd className="rounded border border-line px-1">K</kbd></span>}
    </button>
  );
}

/** Suggested searches that open the search dialog with the term filled in. */
export function PopularSearches({ terms }: { terms: string[] }) {
  const open = useOpenSearch();
  return (
    <p className="mt-4 flex flex-wrap items-center gap-2 text-[13.5px] text-dim">
      Popular:
      {terms.map((term) => (
        <button key={term} type="button" onClick={() => open(term)} className="rounded-full border border-line bg-surface px-2.5 py-1 transition hover:border-line-strong hover:text-ink">{term}</button>
      ))}
    </p>
  );
}
