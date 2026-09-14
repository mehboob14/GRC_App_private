/** How long the success state of the auth button plays before the page moves on. */
const AUTH_SUCCESS_MS = 950;

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}

/** Zero for people who asked for less motion: nothing waits on an animation they will not see. */
export function authSuccessDelay(): number {
  return prefersReducedMotion() ? 0 : AUTH_SUCCESS_MS;
}
