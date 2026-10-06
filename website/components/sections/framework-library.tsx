"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { DemoButton } from "@/components/site/demo-button";
import type { Framework, FrameworkCategory, Region } from "@/content/frameworks";

interface Props {
  frameworks: Framework[];
  regions: { id: Region; name: string; short: string }[];
  categories: Record<FrameworkCategory, string>;
}

const typeLabel: Record<Framework["type"], string> = { standard: "Standard", regulation: "Regulation", law: "Law", framework: "Framework", attestation: "Attestation report" };

/** The filterable framework library with a details popup per framework. */
export function FrameworkLibrary({ frameworks, regions, categories }: Props) {
  const params = useSearchParams();
  // Deep links: ?region=pk, ?q=PCI, ?f=<id> set the starting state.
  const [region, setRegion] = useState<Region | "all">(() => {
    const r = params.get("region");
    return r && regions.some((item) => item.id === r) ? (r as Region) : "all";
  });
  const [category, setCategory] = useState<FrameworkCategory | "all">("all");
  const [status, setStatus] = useState<"all" | "live" | "soon">("all");
  const [query, setQuery] = useState(() => params.get("q") ?? "");
  const [selected, setSelected] = useState<Framework | null>(() => frameworks.find((item) => item.id === params.get("f")) ?? null);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (selected && !node.open) node.showModal();
    if (!selected && node.open) node.close();
  }, [selected]);

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return frameworks.filter((item) =>
      (region === "all" || item.region === region) &&
      (category === "all" || item.categories.includes(category)) &&
      (status === "all" || item.status === status) &&
      (!needle || `${item.name} ${item.shortName} ${item.issuer} ${item.summary}`.toLowerCase().includes(needle)),
    );
  }, [frameworks, region, category, status, query]);

  const usedCategories = useMemo(() => (Object.keys(categories) as FrameworkCategory[]).filter((key) => frameworks.some((item) => item.categories.includes(key))), [categories, frameworks]);
  const regionName = (id: Region) => regions.find((item) => item.id === id)?.name ?? id;

  const reset = () => { setRegion("all"); setCategory("all"); setStatus("all"); setQuery(""); };

  return (
    <div>
      <div className="sticky top-[var(--header-h)] z-20 -mx-4 border-b border-line bg-surface/95 px-4 py-4 backdrop-blur sm:mx-0 sm:rounded-2xl sm:border sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <label className="flex h-10 flex-1 items-center gap-2 rounded-lg border border-line-strong bg-surface px-3 focus-within:border-accent focus-within:shadow-focus">
            <Icon name="search" size={17} className="text-dim" />
            <span className="sr-only">Search frameworks</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name, issuer or topic" className="h-full w-full bg-transparent text-[15px] text-ink outline-none placeholder:text-faint" />
          </label>
          <div className="grid grid-cols-3 gap-2 lg:flex">
            <select aria-label="Region" value={region} onChange={(event) => setRegion(event.target.value as Region | "all")} className="h-10 rounded-lg border border-line-strong bg-surface px-2.5 text-[14px] text-ink">
              <option value="all">All regions</option>
              {regions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <select aria-label="Category" value={category} onChange={(event) => setCategory(event.target.value as FrameworkCategory | "all")} className="h-10 rounded-lg border border-line-strong bg-surface px-2.5 text-[14px] text-ink">
              <option value="all">All categories</option>
              {usedCategories.map((key) => <option key={key} value={key}>{categories[key]}</option>)}
            </select>
            <select aria-label="Status" value={status} onChange={(event) => setStatus(event.target.value as "all" | "live" | "soon")} className="h-10 rounded-lg border border-line-strong bg-surface px-2.5 text-[14px] text-ink">
              <option value="all">Any status</option>
              <option value="live">Available now</option>
              <option value="soon">Coming soon</option>
            </select>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <button type="button" onClick={() => setRegion("all")} className={cn("rounded-full border px-3 py-1 text-[13px] font-medium", region === "all" ? "border-ink bg-ink text-white" : "border-line text-body hover:border-line-strong")}>All</button>
          {regions.map((item) => (
            <button key={item.id} type="button" onClick={() => setRegion(item.id)} aria-pressed={region === item.id} className={cn("rounded-full border px-3 py-1 text-[13px] font-medium", region === item.id ? "border-ink bg-ink text-white" : "border-line text-body hover:border-line-strong")}>{item.name}</button>
          ))}
          <span className="ms-auto text-[13px] text-dim" aria-live="polite">{shown.length} of {frameworks.length}</span>
        </div>
      </div>

      {shown.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-line-strong p-10 text-center">
          <p className="text-[16px] font-medium text-ink">No frameworks match these filters.</p>
          <p className="mt-1 text-dim">Try another region or search term. If yours is missing, tell us and we will consider it for the library.</p>
          <div className="mt-5 flex justify-center gap-2">
            <button type="button" onClick={reset} className="btn btn-outline btn-sm">Clear filters</button>
            <DemoButton variant="dark" className="btn-sm" interest="compliance-automation" source="framework-library-empty">Request a framework</DemoButton>
          </div>
        </div>
      ) : (
        <ul className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {shown.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={(event) => { opener.current = event.currentTarget; setSelected(item); }}
                className="group flex h-full w-full flex-col rounded-xl border border-line bg-surface p-5 text-left shadow-card transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-float"
                aria-haspopup="dialog"
              >
                <span className="flex w-full items-start justify-between gap-3">
                  <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{regionName(item.region)}</span>
                  <StatusBadge status={item.status} size="xs" hideLive={false} />
                </span>
                <span className="mt-3 text-[17px] font-semibold leading-snug text-ink">{item.shortName}</span>
                <span className="mt-0.5 text-[13px] text-dim">{item.issuer.split("(")[0].trim()}</span>
                <span className="mt-3 line-clamp-3 text-[14px] leading-relaxed text-body">{item.summary}</span>
                <span className="mt-auto flex flex-wrap gap-1.5 pt-4">
                  {item.categories.slice(0, 3).map((key) => <span key={key} className="rounded border border-line px-1.5 py-0.5 text-[11.5px] text-dim">{categories[key]}</span>)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <dialog
        ref={dialog}
        className="demo-dialog m-auto w-[min(640px,calc(100vw-24px))] rounded-2xl border border-line bg-surface p-0 text-body shadow-menu backdrop:bg-ink/40"
        aria-labelledby="framework-dialog-title"
        onClose={() => { setSelected(null); opener.current?.focus(); }}
        onClick={(event) => { if (event.target === dialog.current) setSelected(null); }}
      >
        {selected && (
          <div className="p-6 sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{regionName(selected.region)}{selected.jurisdictionNote ? ` · ${selected.jurisdictionNote}` : ""}</p>
                <h2 id="framework-dialog-title" className="mt-2 font-serif text-[28px] leading-tight text-ink">{selected.shortName}</h2>
                <p className="mt-1 text-[14px] text-dim">{selected.name}</p>
              </div>
              <button type="button" onClick={() => setSelected(null)} className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-dim hover:bg-muted hover:text-ink" aria-label="Close"><Icon name="x" size={18} weight="bold" /></button>
            </div>
            <dl className="mt-6 grid grid-cols-1 gap-x-6 gap-y-4 text-[14px] sm:grid-cols-2">
              <div><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Issuer</dt><dd className="mt-1 text-ink">{selected.issuer}</dd></div>
              <div><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Type</dt><dd className="mt-1 text-ink">{typeLabel[selected.type]}</dd></div>
              <div className="sm:col-span-2"><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Version</dt><dd className="mt-1 text-ink">{selected.version}</dd></div>
              <div className="sm:col-span-2"><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">What it covers</dt><dd className="mt-1 leading-relaxed text-body">{selected.summary}</dd></div>
              <div className="sm:col-span-2"><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Who it is for</dt><dd className="mt-1 leading-relaxed text-body">{selected.whoItsFor}</dd></div>
            </dl>
            <div className={cn("mt-6 flex gap-3 rounded-xl border p-4 text-[14px] leading-relaxed", selected.status === "live" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-dashed border-indigo-300 bg-indigo-50/60 text-indigo-950")}>
              <Icon name={selected.status === "live" ? "check" : "map"} size={19} className="mt-0.5 shrink-0" />
              <p>
                {selected.status === "live"
                  ? "Available now. The library ships with every workspace, mapped to Verity's control set."
                  : "Coming soon. This library is on our roadmap. Today you can add your own controls for it and link evidence to them."}{" "}
                Verity prepares the work; certification or attestation is issued by your auditor or certification body.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap gap-2">
              <DemoButton variant="dark" className="btn-sm" interest="compliance-automation" source={`framework-${selected.id}`}>Talk to us about {selected.shortName}</DemoButton>
              <button type="button" onClick={() => setSelected(null)} className="btn btn-outline btn-sm">Close</button>
            </div>
          </div>
        )}
      </dialog>
    </div>
  );
}
