"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Adds `is-visible` to [data-reveal] and [data-animate] elements as they enter
 * the viewport. CSS decides what that means; with reduced motion the CSS shows
 * everything in its final state, so this only ever adds polish.
 */
export function RevealObserver() {
  const pathname = usePathname();
  useEffect(() => {
    const seen = new WeakSet<Element>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );
    const scan = () => {
      document.querySelectorAll("[data-reveal], [data-animate]").forEach((node) => {
        if (seen.has(node)) return;
        seen.add(node);
        io.observe(node);
      });
    };
    scan();
    const mo = new MutationObserver(scan);
    mo.observe(document.body, { childList: true, subtree: true });
    return () => {
      io.disconnect();
      mo.disconnect();
    };
  }, [pathname]);
  return null;
}
