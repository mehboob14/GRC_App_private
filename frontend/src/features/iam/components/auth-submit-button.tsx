import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent,
} from "react";
import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/features/iam/auth-motion";

export type AuthSubmitPhase = "idle" | "loading" | "success";

// No dash glyphs: the product shows none anywhere, the cipher included.
const GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%&*+=?";

/**
 * Text that resolves out of scrambled glyphs, left to right, like a message
 * being decrypted. Returns the final text straight away for reduced motion.
 */
function useDecoded(text: string, run: boolean): string {
  const [shown, setShown] = useState(text);
  useEffect(() => {
    if (!run || prefersReducedMotion()) {
      setShown(text);
      return;
    }
    let raf = 0;
    let frame = 0;
    const frames = Math.max(18, text.length * 2);
    const tick = () => {
      frame += 1;
      const reveal = Math.floor((frame / frames) * text.length);
      if (reveal >= text.length) {
        setShown(text);
        return;
      }
      if (frame % 2 === 0) {
        setShown(
          Array.from(text, (ch, i) =>
            i < reveal || ch === " "
              ? ch
              : GLYPHS[Math.floor(Math.random() * GLYPHS.length)],
          ).join(""),
        );
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [text, run]);
  return shown;
}

/**
 * The submit button of the sign-in and create-workspace forms.
 *
 * It answers the pointer (leans toward it under a spotlight, ripples from the
 * exact point pressed) and narrates the request: the label lifts away letter by
 * letter, a light races around the border, a fill creeps toward done without
 * ever claiming it, and each status line decodes itself. Success completes the
 * fill, turns green and draws a check; a failure drains it and shakes. The
 * page owns the phase, so the button can never say "signed in" before the
 * server has.
 */
export function AuthSubmitButton({
  label,
  steps,
  successLabel,
  phase,
  shakeKey = 0,
  className,
}: {
  label: string;
  /** Status lines while the request runs. Advances and holds on the last. */
  steps: string[];
  successLabel: string;
  phase: AuthSubmitPhase;
  /** Bump to replay the failure shake (a refused request or an invalid form). */
  shakeKey?: number;
  className?: string;
}) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const frameRef = useRef(0);
  const [step, setStep] = useState(0);
  const [shaking, setShaking] = useState(false);
  const [ripples, setRipples] = useState<
    { id: number; x: number; y: number }[]
  >([]);

  useEffect(() => {
    if (phase !== "loading") {
      setStep(0);
      return;
    }
    const timer = window.setInterval(
      () => setStep((s) => Math.min(s + 1, steps.length - 1)),
      1500,
    );
    return () => window.clearInterval(timer);
  }, [phase, steps.length]);

  // Progress eases toward 90% while pending: it is honest about not knowing
  // when the server will answer, and only the answer completes it.
  useEffect(() => {
    const el = buttonRef.current;
    if (!el) return;
    if (phase !== "loading") {
      el.style.setProperty("--vx-p", phase === "success" ? "1" : "0");
      return;
    }
    // Time based, so a 120 Hz screen does not fill twice as fast: about a
    // third after one second, two thirds after three, never past 90%.
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = 0.9 - 0.84 * Math.exp(-(now - start) / 2200);
      el.style.setProperty("--vx-p", p.toFixed(4));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  useEffect(() => {
    if (!shakeKey) return;
    setShaking(true);
    const timer = window.setTimeout(() => setShaking(false), 560);
    return () => window.clearTimeout(timer);
  }, [shakeKey]);

  const lean = (event: PointerEvent<HTMLButtonElement>) => {
    const el = buttonRef.current;
    if (!el || phase !== "idle" || event.pointerType === "touch") return;
    const rect = el.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      el.style.setProperty("--vx-x", `${x}px`);
      el.style.setProperty("--vx-y", `${y}px`);
      el.style.setProperty("--vx-tx", `${(x / rect.width - 0.5) * 6}px`);
      el.style.setProperty("--vx-ty", `${(y / rect.height - 0.5) * 4}px`);
    });
  };

  const settle = () => {
    const el = buttonRef.current;
    if (!el) return;
    cancelAnimationFrame(frameRef.current);
    el.style.setProperty("--vx-tx", "0px");
    el.style.setProperty("--vx-ty", "0px");
  };

  const ripple = (event: PointerEvent<HTMLButtonElement>) => {
    const el = buttonRef.current;
    if (!el || phase !== "idle") return;
    const rect = el.getBoundingClientRect();
    const id = event.timeStamp;
    setRipples((rs) => [
      ...rs,
      { id, x: event.clientX - rect.left, y: event.clientY - rect.top },
    ]);
    window.setTimeout(
      () => setRipples((rs) => rs.filter((r) => r.id !== id)),
      700,
    );
  };

  const status = useDecoded(steps[step] ?? label, phase === "loading");
  const done = useDecoded(successLabel, phase === "success");
  const busy = phase !== "idle";
  const chars = Array.from(label);

  return (
    <span className={cn("vx-cta-wrap", className)} data-phase={phase}>
      <button
        ref={buttonRef}
        type="submit"
        data-phase={phase}
        disabled={busy}
        aria-busy={phase === "loading" || undefined}
        aria-label={
          phase === "loading"
            ? steps[step]
            : phase === "success"
              ? successLabel
              : label
        }
        onPointerMove={lean}
        onPointerLeave={settle}
        onPointerDown={ripple}
        className={cn(
          "vx-cta font-sans text-label-md font-bold",
          shaking && "vx-cta-shake",
        )}
      >
        <span className="vx-cta-success" aria-hidden />
        <span className="vx-cta-fill" aria-hidden />
        <span className="vx-cta-spot" aria-hidden />
        <span className="vx-cta-ring" aria-hidden />
        {ripples.map((r) => (
          <span
            key={r.id}
            className="vx-cta-ripple"
            style={{ left: r.x, top: r.y }}
            aria-hidden
          />
        ))}
        <span className="vx-cta-content" aria-hidden>
          <span className="vx-cta-label">
            {chars.map((ch, i) => (
              <span
                key={i}
                className="vx-cta-char"
                style={{ "--i": i } as CSSProperties}
              >
                {ch === " " ? "\u00a0" : ch}
              </span>
            ))}
            <span
              className="vx-cta-char vx-cta-arrow"
              style={{ "--i": chars.length } as CSSProperties}
            >
              <svg
                viewBox="0 0 24 24"
                className="size-4"
                fill="none"
                stroke="currentColor"
                strokeWidth={2.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h13M13 6l6 6-6 6" />
              </svg>
            </span>
          </span>
          <span className="vx-cta-state vx-cta-loading">
            <svg
              viewBox="0 0 24 24"
              className="size-4 shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6l7-3z" />
              <path className="vx-cta-scan" d="M8.5 12h7" />
            </svg>
            <span className="vx-cta-text">{status}</span>
          </span>
          <span className="vx-cta-state vx-cta-done">
            <svg
              viewBox="0 0 24 24"
              className="vx-cta-check size-4 shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12.5l4.5 4.5L19 7.5" />
            </svg>
            <span className="vx-cta-text">{done}</span>
          </span>
        </span>
      </button>
      <span className="sr-only" role="status" aria-live="polite">
        {phase === "loading"
          ? steps[step]
          : phase === "success"
            ? successLabel
            : ""}
      </span>
    </span>
  );
}
