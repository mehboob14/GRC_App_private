"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { DemoForm } from "./demo-form";

interface OpenOptions {
  interest?: string;
  source?: string;
}

const DemoContext = createContext<((options?: OpenOptions) => void) | null>(null);

/**
 * Hosts the one demo-request popup for the whole marketing site. Every
 * "See a demo" / "Talk to sales" action opens it; without JavaScript those
 * actions are ordinary links to /demo/.
 */
export function DemoProvider({ endpoint, children }: { endpoint: string | null; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const [options, setOptions] = useState<OpenOptions | null>(null);

  const open = useCallback((next: OpenOptions = {}) => {
    opener.current = document.activeElement as HTMLElement | null;
    setOptions(next);
  }, []);

  const close = useCallback(() => {
    dialog.current?.close();
  }, []);

  useEffect(() => {
    const node = dialog.current;
    if (!node || !options) return;
    if (!node.open) node.showModal();
    document.documentElement.style.overflow = "hidden";
    const onClose = () => {
      document.documentElement.style.overflow = "";
      setOptions(null);
      opener.current?.focus?.();
    };
    node.addEventListener("close", onClose, { once: true });
    return () => node.removeEventListener("close", onClose);
  }, [options]);

  return (
    <DemoContext.Provider value={open}>
      {children}
      <dialog
        ref={dialog}
        aria-labelledby="demo-dialog-title"
        className="demo-dialog m-auto w-[min(680px,calc(100vw-24px))] max-h-[min(860px,calc(100dvh-24px))] overflow-hidden rounded-2xl border border-line bg-surface p-0 text-body shadow-menu backdrop:bg-ink/40 backdrop:backdrop-blur-[2px]"
        onClick={(event) => {
          if (event.target === dialog.current) close();
        }}
      >
        {options && (
          <div className="flex max-h-[inherit] flex-col">
            <div className="flex items-start justify-between gap-6 border-b border-line px-5 pb-4 pt-5 sm:px-7 sm:pt-6">
              <div>
                <p className="eyebrow mb-2">See Verity</p>
                <h2 id="demo-dialog-title" className="font-serif text-[26px] leading-tight">Book a demo with our team</h2>
                <p className="mt-1.5 text-[14.5px] text-dim">Tell us what you answer to and what slows you down. We will show you those parts of Verity.</p>
              </div>
              <button type="button" onClick={close} className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-dim transition hover:bg-muted hover:text-ink" aria-label="Close">
                <Icon name="x" size={18} weight="bold" />
              </button>
            </div>
            <div className="overflow-y-auto px-5 pb-6 pt-5 sm:px-7">
              <DemoForm endpoint={endpoint} interest={options.interest} source={options.source ?? "popup"} onDone={close} />
            </div>
          </div>
        )}
      </dialog>
    </DemoContext.Provider>
  );
}

/** A link to /demo/ that opens the popup instead when scripting is available. */
export function DemoButton({ children, className, interest, source, variant }: { children: ReactNode; className?: string; interest?: string; source?: string; variant?: "dark" | "outline" | "light" | "ghost" | "none" }) {
  const open = useContext(DemoContext);
  const href = interest ? `/demo/?interest=${encodeURIComponent(interest)}` : "/demo/";
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!open || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    open({ interest, source });
  };
  return (
    <a href={href} onClick={onClick} className={cn(variant && variant !== "none" && `btn btn-${variant}`, className)} aria-haspopup="dialog">
      {children}
    </a>
  );
}
