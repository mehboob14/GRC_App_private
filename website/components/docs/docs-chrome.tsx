"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { Brand } from "@/components/site/brand";
import type { TocItem } from "@/lib/docs";
import { SearchButton } from "./search-dialog";

export interface SidebarGroup {
  id: string;
  title: string;
  icon: IconName;
  items: { slug: string; label: string; status: "live" | "preview" | "soon" }[];
}

/* ---------------------------------------------------------------- theme */

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    setTheme(document.documentElement.dataset.docsTheme === "dark" ? "dark" : "light");
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.docsTheme = next;
    try { localStorage.setItem("verity-docs-theme", next); } catch { /* storage may be unavailable; the choice still applies to this visit */ }
    setTheme(next);
  };
  return (
    <button type="button" onClick={toggle} className="grid h-9 w-9 place-items-center rounded-lg text-dim transition hover:bg-muted hover:text-ink" aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"} title={theme === "dark" ? "Light theme" : "Dark theme"}>
      <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
    </button>
  );
}

/* --------------------------------------------------------------- header */

export function DocsHeader({ groups, trialUrl }: { groups: SidebarGroup[]; trialUrl: string }) {
  const [drawer, setDrawer] = useState(false);
  const [progress, setProgress] = useState(0);
  const pathname = usePathname();
  const isArticle = pathname !== "/docs/" && pathname !== "/docs";

  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => {
    if (!isArticle) return;
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isArticle, pathname]);
  useEffect(() => {
    if (!drawer) return;
    document.documentElement.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setDrawer(false); };
    document.addEventListener("keydown", onKey);
    return () => { document.documentElement.style.overflow = ""; document.removeEventListener("keydown", onKey); };
  }, [drawer]);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/85">
      <div className="mx-auto flex h-[var(--header-h)] max-w-[1600px] items-center gap-4 px-4 sm:px-6">
        <button type="button" className="grid h-9 w-9 place-items-center rounded-lg text-ink hover:bg-muted lg:hidden" aria-label="Open documentation menu" aria-expanded={drawer} aria-controls="docs-drawer" onClick={() => setDrawer(true)}>
          <Icon name="menu" size={21} />
        </button>
        <Brand suffix="Docs" href="/docs/" />
        <nav aria-label="Documentation sections" className="ms-4 hidden items-center gap-1 text-[14px] md:flex">
          <Link href="/docs/" className={cn("rounded-md px-2.5 py-1.5 font-medium transition-colors", !pathname.startsWith("/docs/reference/release-notes") ? "text-ink" : "text-dim hover:text-ink")}>Guides</Link>
          <Link href="/docs/reference/release-notes/" className={cn("rounded-md px-2.5 py-1.5 font-medium transition-colors", pathname.startsWith("/docs/reference/release-notes") ? "text-ink" : "text-dim hover:text-ink")}>Release notes</Link>
          <Link href="/platform/" className="rounded-md px-2.5 py-1.5 font-medium text-dim transition-colors hover:text-ink">Platform</Link>
        </nav>
        <div className="ms-auto flex items-center gap-2">
          <SearchButton className="hidden w-64 sm:flex" />
          <SearchButton compact className="sm:hidden" />
          <ThemeToggle />
          <Link href="/" className="hidden rounded-md px-2.5 py-1.5 text-[14px] font-medium text-dim hover:text-ink xl:inline-flex">verity.com</Link>
          <a href={trialUrl} className="btn btn-dark btn-sm hidden sm:inline-flex">Start trial</a>
        </div>
      </div>
      {isArticle && <span className="docs-progress" style={{ transform: `scaleX(${progress})` }} aria-hidden="true" />}
      {drawer && (
        <div className="fixed inset-0 z-[70] lg:hidden" role="dialog" aria-modal="true" aria-label="Documentation menu" id="docs-drawer">
          <button type="button" className="absolute inset-0 animate-fade-in bg-ink/30" aria-label="Close menu" tabIndex={-1} onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 start-0 flex w-[min(340px,88vw)] animate-slide-in-start flex-col bg-surface shadow-menu">
            <div className="flex h-[var(--header-h)] shrink-0 items-center justify-between border-b border-line px-4">
              <Brand suffix="Docs" href="/docs/" />
              <button type="button" className="grid h-9 w-9 place-items-center rounded-lg hover:bg-muted" aria-label="Close menu" onClick={() => setDrawer(false)}><Icon name="x" size={20} /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4"><SidebarNav groups={groups} /></div>
          </div>
        </div>
      )}
    </header>
  );
}

/* -------------------------------------------------------------- sidebar */

export function SidebarNav({ groups }: { groups: SidebarGroup[] }) {
  const pathname = usePathname();
  const current = pathname.replace(/^\/docs\/?/, "").replace(/\/$/, "");
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => Object.fromEntries(groups.map((group) => [group.id, true])));
  const activeRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest" });
  }, [current]);

  return (
    <nav aria-label="Documentation" className="text-[14px]">
      <Link href="/docs/" className={cn("mb-3 flex items-center gap-2.5 rounded-lg px-2.5 py-2 font-medium transition-colors", current === "" ? "bg-muted text-ink" : "text-body hover:bg-subtle hover:text-ink")}>
        <Icon name="book" size={17} />Documentation home
      </Link>
      {groups.map((group) => {
        const open = openGroups[group.id];
        const hasActive = group.items.some((item) => item.slug === current);
        return (
          <div key={group.id} className="mb-1">
            <button type="button" onClick={() => setOpenGroups((state) => ({ ...state, [group.id]: !state[group.id] }))} aria-expanded={open} className={cn("flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left font-semibold transition-colors hover:bg-subtle", hasActive ? "text-ink" : "text-body")}>
              <Icon name={group.icon} size={17} className="text-dim" />
              <span className="flex-1">{group.title}</span>
              <Icon name="caret-down" size={12} weight="bold" className={cn("text-faint transition-transform duration-200", !open && "-rotate-90")} />
            </button>
            {open && (
              <ul className="relative mb-2 ms-[19px] border-s border-line ps-2">
                {group.items.map((item) => {
                  const active = item.slug === current;
                  return (
                    <li key={item.slug}>
                      <Link ref={active ? activeRef : undefined} href={`/docs/${item.slug}/`} aria-current={active ? "page" : undefined} className={cn("relative flex items-center gap-2 rounded-md px-2.5 py-[7px] leading-snug transition-colors", active ? "bg-accent-soft font-medium text-accent-strong" : "text-dim hover:bg-subtle hover:text-ink")}>
                        {active && <span className="absolute -start-[9px] top-1.5 bottom-1.5 w-[2px] rounded-full bg-accent" aria-hidden="true" />}
                        <span className="flex-1">{item.label}</span>
                        {item.status !== "live" && <StatusBadge status={item.status} size="xs" />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </nav>
  );
}

/* --------------------------------------------------------- on this page */

export function OnThisPage({ toc, mobile = false }: { toc: TocItem[]; mobile?: boolean }) {
  const [active, setActive] = useState<string | null>(toc[0]?.id ?? null);
  useEffect(() => {
    if (!toc.length) return;
    const headings = toc.map((item) => document.getElementById(item.id)).filter((node): node is HTMLElement => !!node);
    const onScroll = () => {
      const offset = 120;
      let current = headings[0]?.id ?? null;
      for (const heading of headings) if (heading.getBoundingClientRect().top - offset <= 0) current = heading.id;
      setActive(current);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [toc]);

  if (!toc.length) return null;
  const list = (
    <ul className="space-y-0.5 border-s border-line text-[13.5px]">
      {toc.map((item) => (
        <li key={item.id}>
          <a href={`#${item.id}`} className={cn("-ms-px block border-s-2 py-1 leading-snug transition-colors", item.depth === 3 ? "ps-6" : "ps-3.5", active === item.id ? "border-accent font-medium text-accent-strong" : "border-transparent text-dim hover:text-ink")}>
            {item.text}
          </a>
        </li>
      ))}
    </ul>
  );
  if (mobile) {
    return (
      <details className="group mb-8 rounded-xl border border-line bg-subtle xl:hidden">
        <summary className="flex items-center justify-between px-4 py-3 text-[14px] font-medium text-ink">
          On this page
          <Icon name="caret-down" size={13} weight="bold" className="text-dim transition-transform group-open:rotate-180" />
        </summary>
        <div className="px-4 pb-4">{list}</div>
      </details>
    );
  }
  return (
    <nav aria-label="On this page">
      <p className="eyebrow mb-3">On this page</p>
      {list}
    </nav>
  );
}

/* ------------------------------------------------------------- feedback */

export function Feedback({ endpoint, slug }: { endpoint: string; slug: string }) {
  const [state, setState] = useState<"idle" | "sent" | "error">("idle");
  const send = async (helpful: boolean) => {
    try {
      const response = await fetch(endpoint, { method: "POST", credentials: "omit", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ page: `/docs/${slug}/`, helpful }) });
      setState(response.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  };
  return (
    <div className="mt-14 flex flex-wrap items-center gap-3 rounded-xl border border-line bg-subtle px-5 py-4" aria-live="polite">
      {state === "sent" ? (
        <p className="text-[14.5px] text-ink">Thank you. Your answer helps us improve this page.</p>
      ) : (
        <>
          <p className="text-[14.5px] font-medium text-ink">Was this page helpful?</p>
          <div className="flex gap-2">
            <button type="button" onClick={() => send(true)} className="btn btn-outline btn-sm"><Icon name="thumbs-up" size={16} />Yes</button>
            <button type="button" onClick={() => send(false)} className="btn btn-outline btn-sm"><Icon name="thumbs-down" size={16} />No</button>
          </div>
          {state === "error" && <p className="w-full text-[13px] text-red-700">That did not send. Please try again later.</p>}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ copy link */

export function CopyLink() {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(window.location.href.split("#")[0]);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1800);
        } catch { /* clipboard not available; nothing to do */ }
      }}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] text-dim transition hover:bg-muted hover:text-ink"
      aria-live="polite"
    >
      <Icon name={copied ? "check-plain" : "link"} size={14} />
      {copied ? "Link copied" : "Copy link"}
    </button>
  );
}
