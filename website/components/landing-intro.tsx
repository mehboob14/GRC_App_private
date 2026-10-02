"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

const seenKey = "verity-landing-intro-seen";

function subscribe(callback: () => void) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  window.addEventListener("storage", callback);
  reducedMotion.addEventListener("change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    reducedMotion.removeEventListener("change", callback);
  };
}

function shouldShowIntro() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  try {
    return sessionStorage.getItem(seenKey) !== "1";
  } catch {
    return true;
  }
}

export function LandingIntro() {
  const eligible = useSyncExternalStore(subscribe, shouldShowIntro, () => true);
  const [dismissed, setDismissed] = useState(false);
  const active = eligible && !dismissed;
  const skipRef = useRef<HTMLButtonElement>(null);

  const dismiss = useCallback((focusHero: boolean) => {
    try {
      sessionStorage.setItem(seenKey, "1");
    } catch {
      // The page still opens if storage is unavailable.
    }
    document.body.style.overflow = "";
    setDismissed(true);
    if (focusHero) {
      window.requestAnimationFrame(() => document.getElementById("hero-heading")?.focus());
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    const timer = window.setTimeout(() => dismiss(false), 1450);
    skipRef.current?.focus();
    document.body.style.overflow = "hidden";
    return () => {
      window.clearTimeout(timer);
      document.body.style.overflow = "";
    };
  }, [active, dismiss]);

  if (!active) return null;

  return (
    <div className="landing-intro" role="dialog" aria-modal="true" aria-label="Verity introduction" onKeyDown={(event) => {
      if (event.key === "Escape") dismiss(true);
      if (event.key === "Tab") {
        event.preventDefault();
        skipRef.current?.focus();
      }
    }}>
      <span className="intro-wordmark" aria-label="Verity">verity<span>.</span></span>
      <button className="intro-skip" type="button" ref={skipRef} onClick={(event) => dismiss(event.detail === 0)}>Skip intro</button>
    </div>
  );
}
