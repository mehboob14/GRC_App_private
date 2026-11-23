"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import type { MenuColumn, MenuLink } from "@/content/navigation";
import { Brand } from "./brand";
import { DemoButton } from "./demo-provider";

type MenuId = "platform" | "solutions" | "resources";

interface Props {
  platform: MenuColumn[];
  solutions: MenuColumn[];
  resources: MenuColumn[];
  signInUrl: string;
  trialUrl: string;
}

const groupIcons: Record<string, IconName> = { Compliance: "shield", Risk: "scales", Security: "server", Platform: "stack" };

function MenuLinkRow({ link, onNavigate, dense = false }: { link: MenuLink; onNavigate: () => void; dense?: boolean }) {
  return (
    <Link href={link.href} onClick={onNavigate} className={cn("group/link flex items-start gap-3 rounded-lg transition-colors hover:bg-subtle focus-visible:bg-subtle", dense ? "px-2.5 py-2" : "px-3 py-2.5")}>
      {link.icon && (
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md border border-line bg-surface text-ink shadow-[0_1px_1px_rgb(16_24_40/0.04)] transition-colors group-hover/link:border-sky-200 group-hover/link:text-sky-700">
          <Icon name={link.icon} size={17} />
        </span>
      )}
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-2 text-[14px] font-medium leading-5 text-ink">
          {link.title}
          {link.status && <StatusBadge status={link.status} size="xs" />}
        </span>
        {link.description && <span className="mt-0.5 block text-[12.5px] leading-[1.35] text-dim">{link.description}</span>}
      </span>
    </Link>
  );
}

function PanelShell({ id, open, children, labelledBy }: { id: string; open: boolean; children: ReactNode; labelledBy: string }) {
  return (
    <div id={id} role="region" aria-labelledby={labelledBy} hidden={!open} className="absolute inset-x-0 top-full z-40 px-4 pt-2 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-frame animate-pop-in overflow-hidden rounded-2xl border border-line bg-surface shadow-menu">{children}</div>
    </div>
  );
}

export function SiteNavigation({ platform, solutions, resources, signInUrl, trialUrl }: Props) {
  const [open, setOpen] = useState<MenuId | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const root = useRef<HTMLElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const triggers = useRef<Partial<Record<MenuId, HTMLButtonElement | null>>>({});
  const drawerRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  const closeAll = useCallback(() => {
    setOpen(null);
    setDrawer(false);
  }, []);

  // Close menus when the route changes (adjusting state on a prop change, not in an effect).
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(null);
    setDrawer(false);
  }

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        const trigger = triggers.current[open];
        setOpen(null);
        trigger?.focus();
      }
    };
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  // Drawer: lock scroll, trap focus, Escape closes.
  useEffect(() => {
    if (!drawer) return;
    const node = drawerRef.current;
    document.documentElement.style.overflow = "hidden";
    node?.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawer(false);
      if (event.key !== "Tab" || !node) return;
      const focusable = [...node.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), summary")].filter((el) => el.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.documentElement.style.overflow = "";
      document.removeEventListener("keydown", onKey);
    };
  }, [drawer]);

  const canHover = () => typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const hoverOpen = (id: MenuId) => {
    if (!canHover()) return;
    window.clearTimeout(closeTimer.current);
    setOpen(id);
  };
  const hoverClose = () => {
    if (!canHover()) return;
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setOpen(null), 160);
  };

  const trigger = (id: MenuId, label: string) => (
    <button
      ref={(node) => { triggers.current[id] = node; }}
      id={`nav-trigger-${id}`}
      type="button"
      aria-expanded={open === id}
      aria-controls={`nav-panel-${id}`}
      onClick={() => setOpen(open === id ? null : id)}
      onPointerEnter={() => hoverOpen(id)}
      className={cn("inline-flex h-9 items-center gap-1 rounded-md px-3 text-[14.5px] font-medium transition-colors", open === id ? "bg-muted text-ink" : "text-body hover:text-ink")}
    >
      {label}
      <Icon name="caret-down" size={13} weight="bold" className={cn("transition-transform duration-200", open === id && "rotate-180")} />
    </button>
  );

  return (
    <header ref={root} className="sticky top-0 z-50" onPointerLeave={hoverClose} onPointerEnter={() => window.clearTimeout(closeTimer.current)}>
      <div className={cn("border-b bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/85", scrolled || open ? "border-line" : "border-transparent")}>
        <div className="relative">
          <div className="frame flex h-[var(--header-h)] items-center gap-6">
            <Brand />
            <nav aria-label="Main" className="hidden items-center gap-0.5 lg:flex">
              <div>
                {trigger("platform", "Platform")}
                <PanelShell id="nav-panel-platform" open={open === "platform"} labelledBy="nav-trigger-platform">
                  <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-2 p-4">
                    {platform.map((column) => (
                      <div key={column.title} className="min-w-0">
                        <p className="eyebrow flex items-center gap-1.5 px-3 pb-2 pt-1"><Icon name={groupIcons[column.title] ?? "stack"} size={14} />{column.title}</p>
                        <div className="flex flex-col">{column.links.map((link) => <MenuLinkRow key={link.href} link={link} onNavigate={closeAll} dense />)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between gap-4 border-t border-line bg-subtle px-7 py-3.5 text-[13.5px]">
                    <span className="text-dim">One platform for compliance, risk and security. Items marked <StatusBadge status="soon" size="xs" className="mx-0.5" /> are on the way.</span>
                    <span className="flex items-center gap-5">
                      <Link href="/platform/" onClick={closeAll} className="link-arrow text-[13.5px]">Platform overview<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></Link>
                      <Link href="/docs/" onClick={closeAll} className="link-arrow text-[13.5px]">Documentation<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></Link>
                    </span>
                  </div>
                </PanelShell>
              </div>
              <div>
                {trigger("solutions", "Solutions")}
                <PanelShell id="nav-panel-solutions" open={open === "solutions"} labelledBy="nav-trigger-solutions">
                  <div className="grid grid-cols-[1.1fr_1fr_0.9fr] gap-2 p-4">
                    {solutions.map((column) => (
                      <div key={column.title}>
                        <p className="eyebrow px-3 pb-2 pt-1">{column.title}</p>
                        <div className="flex flex-col">{column.links.map((link) => <MenuLinkRow key={link.href} link={link} onNavigate={closeAll} dense />)}</div>
                      </div>
                    ))}
                    <Link href="/frameworks/" onClick={closeAll} className="group/feature relative flex flex-col justify-end overflow-hidden rounded-xl border border-line bg-gradient-to-b from-sky-50 to-white p-5">
                      <span className="absolute inset-x-6 top-6 flex flex-wrap gap-1.5" aria-hidden="true">
                        {["SOC 2", "ISO 27001", "PCI DSS", "NIST CSF", "SBP", "APRA", "UAE IA", "GDPR", "HIPAA"].map((label, index) => (
                          <span key={label} className={cn("rounded-md border px-2 py-1 font-mono text-[10.5px]", index === 0 ? "border-emerald-200 bg-white text-emerald-700" : "border-sky-200 bg-white/80 text-sky-800")}>{label}</span>
                        ))}
                      </span>
                      <span className="mt-28 text-[15px] font-semibold text-ink">Framework library</span>
                      <span className="mt-1 text-[13px] leading-snug text-dim">Map one control set to every framework you answer to.</span>
                      <span className="link-arrow mt-3 text-[13px]">Browse frameworks<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></span>
                    </Link>
                  </div>
                </PanelShell>
              </div>
              <Link href="/why-verity/" className="inline-flex h-9 items-center rounded-md px-3 text-[14.5px] font-medium text-body transition-colors hover:text-ink" onPointerEnter={() => canHover() && setOpen(null)}>Why Verity</Link>
              <Link href="/pricing/" className="inline-flex h-9 items-center rounded-md px-3 text-[14.5px] font-medium text-body transition-colors hover:text-ink" onPointerEnter={() => canHover() && setOpen(null)}>Pricing</Link>
              <div>
                {trigger("resources", "Resources")}
                <PanelShell id="nav-panel-resources" open={open === "resources"} labelledBy="nav-trigger-resources">
                  <div className="grid grid-cols-[1fr_1fr_0.95fr] gap-2 p-4">
                    {resources.map((column) => (
                      <div key={column.title}>
                        <p className="eyebrow px-3 pb-2 pt-1">{column.title}</p>
                        <div className="flex flex-col">{column.links.map((link) => <MenuLinkRow key={link.href} link={link} onNavigate={closeAll} dense />)}</div>
                      </div>
                    ))}
                    <Link href="/docs/" onClick={closeAll} className="flex flex-col overflow-hidden rounded-xl border border-line bg-ink p-5 text-white">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-sky-300">Documentation</span>
                      <span className="mt-3 font-serif text-[22px] leading-tight">Learn Verity task by task</span>
                      <span className="mt-2 text-[13px] leading-snug text-white/70">Walkthroughs, screenshots and search for every module.</span>
                      <span className="mt-auto inline-flex items-center gap-2 pt-6 font-mono text-[11.5px] text-white/60"><kbd className="rounded border border-white/20 px-1.5 py-0.5">⌘</kbd><kbd className="rounded border border-white/20 px-1.5 py-0.5">K</kbd> to search the docs</span>
                    </Link>
                  </div>
                </PanelShell>
              </div>
            </nav>
            <div className="ms-auto hidden items-center gap-2 lg:flex">
              <a href={signInUrl} className="inline-flex h-9 items-center rounded-md px-3 text-[14.5px] font-medium text-body transition-colors hover:text-ink">Sign in</a>
              <DemoButton variant="outline" className="btn-sm" source="header">See a demo</DemoButton>
              <a href={trialUrl} className="btn btn-dark btn-sm">Start trial</a>
            </div>
            <button type="button" className="ms-auto grid h-10 w-10 place-items-center rounded-lg text-ink hover:bg-muted lg:hidden" aria-label="Open menu" aria-expanded={drawer} aria-controls="mobile-menu" onClick={() => setDrawer(true)}>
              <Icon name="menu" size={22} />
            </button>
          </div>
        </div>
      </div>

      {drawer && (
        <div className="fixed inset-0 z-[70] lg:hidden" role="dialog" aria-modal="true" aria-label="Menu" id="mobile-menu">
          <button type="button" className="absolute inset-0 animate-fade-in bg-ink/30" aria-label="Close menu" tabIndex={-1} onClick={() => setDrawer(false)} />
          <div ref={drawerRef} className="absolute inset-y-0 end-0 flex w-full max-w-[420px] animate-slide-in-end flex-col bg-surface shadow-menu">
            <div className="flex h-[var(--header-h)] shrink-0 items-center justify-between border-b border-line px-4">
              <Brand />
              <button type="button" data-autofocus className="grid h-10 w-10 place-items-center rounded-lg text-ink hover:bg-muted" aria-label="Close menu" onClick={() => setDrawer(false)}>
                <Icon name="x" size={22} />
              </button>
            </div>
            <nav aria-label="Mobile" className="flex-1 overflow-y-auto overscroll-contain px-2 py-3">
              <MobileSection title="Platform">
                {platform.map((column) => (
                  <div key={column.title} className="pb-2">
                    <p className="eyebrow px-3 pb-1 pt-2">{column.title}</p>
                    {column.links.map((link) => <MenuLinkRow key={link.href} link={{ ...link, description: undefined }} onNavigate={closeAll} dense />)}
                  </div>
                ))}
                <Link href="/platform/" onClick={closeAll} className="link-arrow px-3 py-2 text-[14px]">Platform overview<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></Link>
              </MobileSection>
              <MobileSection title="Solutions">
                {solutions.map((column) => (
                  <div key={column.title} className="pb-2">
                    <p className="eyebrow px-3 pb-1 pt-2">{column.title}</p>
                    {column.links.map((link) => <MenuLinkRow key={link.href} link={{ ...link, description: undefined }} onNavigate={closeAll} dense />)}
                  </div>
                ))}
              </MobileSection>
              <Link href="/why-verity/" onClick={closeAll} className="flex items-center justify-between rounded-lg px-3 py-3.5 text-[16px] font-medium text-ink hover:bg-subtle">Why Verity</Link>
              <Link href="/pricing/" onClick={closeAll} className="flex items-center justify-between rounded-lg px-3 py-3.5 text-[16px] font-medium text-ink hover:bg-subtle">Pricing</Link>
              <MobileSection title="Resources">
                {resources.map((column) => (
                  <div key={column.title} className="pb-2">
                    <p className="eyebrow px-3 pb-1 pt-2">{column.title}</p>
                    {column.links.map((link) => <MenuLinkRow key={link.href} link={{ ...link, description: undefined }} onNavigate={closeAll} dense />)}
                  </div>
                ))}
              </MobileSection>
            </nav>
            <div className="grid shrink-0 gap-2 border-t border-line p-4">
              <DemoButton variant="outline" className="w-full" source="mobile-menu">See a demo</DemoButton>
              <a href={trialUrl} className="btn btn-dark w-full">Start trial</a>
              <a href={signInUrl} className="py-2 text-center text-[14.5px] font-medium text-body">Sign in</a>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function MobileSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="group border-b border-line last:border-b-0">
      <summary className="flex items-center justify-between rounded-lg px-3 py-3.5 text-[16px] font-medium text-ink hover:bg-subtle">
        {title}
        <Icon name="caret-down" size={16} weight="bold" className="text-dim transition-transform group-open:rotate-180" />
      </summary>
      <div className="pb-2">{children}</div>
    </details>
  );
}
