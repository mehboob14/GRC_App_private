// Cross-tab "your email was just verified" signal. The verify-email tab (opened
// from the link) announces; the sign-up tab (which still holds the credentials)
// listens and continues automatically. Same-browser only — the manual
// "I've verified" button covers a link opened on another device.

const CHANNEL = "verity-auth";
const MESSAGE = "email-verified";

export function announceEmailVerified(): void {
  if (typeof BroadcastChannel === "undefined") return;
  const bc = new BroadcastChannel(CHANNEL);
  bc.postMessage(MESSAGE);
  bc.close();
}

/** Calls `onVerified` when another tab announces. Returns a cleanup. */
export function onEmailVerified(onVerified: () => void): () => void {
  if (typeof BroadcastChannel === "undefined") return () => {};
  const bc = new BroadcastChannel(CHANNEL);
  bc.onmessage = (event) => {
    if (event.data === MESSAGE) onVerified();
  };
  return () => bc.close();
}
