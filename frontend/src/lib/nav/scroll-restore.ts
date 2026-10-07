import { useEffect, useRef, type RefObject } from "react";
import { useLocation, useNavigationType } from "react-router-dom";
import { entryIndex } from "@/lib/nav/history-log";

/**
 * Scroll for the page area, the way a browser does it for a document.
 *
 * The app scrolls inside `<main>`, not the window, so the browser's own restore
 * never applies: Back from a detail page landed at the top of a long register, and
 * a new page opened part way down because the same element kept its offset. Going
 * back or forward returns to where that history entry was scrolled; any other
 * navigation to a different page starts at the top.
 */
const positions = new Map<string, number>();
/** How long to wait for a page that fills in as its data arrives. */
const RETRY_MS = 100;
const MAX_TRIES = 30;

export function useScrollRestoration(area: RefObject<HTMLElement | null>): void {
  const { key, pathname } = useLocation();
  const navigation = useNavigationType();
  const previousPath = useRef(pathname);

  // Remember where this entry is scrolled to as it moves. Leaving a page replaces
  // its content, which can clamp the offset to zero and fire one more scroll event
  // after the history has already moved on: that one is not this entry's position.
  useEffect(() => {
    const element = area.current;
    if (!element) return undefined;
    const idx = entryIndex();
    const remember = () => {
      if (entryIndex() === idx) positions.set(key, element.scrollTop);
    };
    element.addEventListener("scroll", remember, { passive: true });
    return () => element.removeEventListener("scroll", remember);
  }, [area, key]);

  // On arrival: restore on back or forward, reset when the page itself changed.
  useEffect(() => {
    const element = area.current;
    const moved = previousPath.current !== pathname;
    previousPath.current = pathname;
    if (!element) return undefined;
    if (navigation !== "POP") {
      if (moved) element.scrollTop = 0;
      return undefined;
    }
    const target = positions.get(key) ?? 0;
    if (target === 0) {
      element.scrollTop = 0;
      return undefined;
    }
    // The page may not be tall enough yet, so keep trying until it is, or until the
    // person scrolls for themselves.
    let tries = 0;
    const timer = window.setInterval(() => {
      element.scrollTop = target;
      tries += 1;
      if (Math.abs(element.scrollTop - target) < 2 || tries >= MAX_TRIES) {
        window.clearInterval(timer);
      }
    }, RETRY_MS);
    const stop = () => window.clearInterval(timer);
    element.addEventListener("wheel", stop, { once: true, passive: true });
    element.addEventListener("touchstart", stop, { once: true, passive: true });
    element.addEventListener("keydown", stop, { once: true });
    return () => {
      window.clearInterval(timer);
      element.removeEventListener("wheel", stop);
      element.removeEventListener("touchstart", stop);
      element.removeEventListener("keydown", stop);
    };
  }, [area, key, pathname, navigation]);
}
