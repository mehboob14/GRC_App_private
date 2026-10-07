/**
 * Lets a tab that opens signed out take the session another tab of this browser holds.
 *
 * sessionStorage is per tab, so a link opened in a new tab (a right click, a
 * middle click, Ctrl and click) arrived with nothing and sent the person to sign in
 * again, however recently they had. Putting the token in localStorage would end
 * that, and would also leave it on disk after the browser closes, which ADR-0006
 * forbids. This keeps the rule: the token still lives only in tabs' sessionStorage,
 * and a new tab asks the open ones for it over a same-origin BroadcastChannel,
 * which no other origin can join.
 *
 * The trade-off, until sessions move to httpOnly cookies (ADR-0006): script running
 * in this origin in a fresh tab can now ask for the session, where before it could
 * only read its own tab's storage. So a tab answers only if it was in use in the last
 * half hour, a new tab takes the answer from the tab used most recently (that is the
 * one the link was opened from, and the right workspace when several are open), and
 * the sign-in, invitation and password pages never ask.
 *
 * Signing out is announced the same way, with the token that signed out, so the
 * tabs holding it end too and a tab opened afterwards cannot revive it. A tab
 * signed in as someone else is left alone.
 */

type Message =
  | { type: "request" }
  | { type: "session"; values: Record<string, string>; activeAt: number }
  | { type: "signout"; token: string };

/** How long a new tab waits for an open one to answer. A same-machine reply takes a few milliseconds. */
const WAIT_MS = 120;
/** Once one tab has answered, how much longer to listen for a more recently used one. */
const MORE_MS = 30;
/** A tab not used for this long does not hand its session to anyone. */
const MAX_IDLE_MS = 30 * 60_000;

/** When this tab was last in use: now if it is on screen, else when it last was. */
let touchedAt = Date.now();
function lastActive(): number {
  return typeof document !== "undefined" && document.visibilityState === "visible"
    ? Date.now()
    : touchedAt;
}
if (typeof window !== "undefined") {
  const touch = () => {
    touchedAt = Date.now();
  };
  window.addEventListener("focus", touch);
  window.addEventListener("pointerdown", touch, { capture: true, passive: true });
  window.addEventListener("keydown", touch, { capture: true, passive: true });
  // Hiding the tab is the last moment it was in use.
  document.addEventListener("visibilitychange", touch);
}

export function createTabShare(
  /** One channel per session plane, so the workspace and the platform admin stay apart. */
  channelName: string,
  /** The sessionStorage keys that make up the session. */
  keys: readonly string[],
  /** Which of them identifies the session. */
  tokenKey: string,
  /** Whether a page opened at this path may ask for a session at all. */
  mayAdopt: (pathname: string) => boolean = () => true,
) {
  function open(): BroadcastChannel | null {
    try {
      return typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(channelName);
    } catch {
      return null;
    }
  }

  /** The whole session this tab holds, or null if any part is missing. */
  function held(): Record<string, string> | null {
    try {
      const values: Record<string, string> = {};
      for (const key of keys) {
        const value = sessionStorage.getItem(key);
        if (value === null) return null;
        values[key] = value;
      }
      return values;
    } catch {
      return null;
    }
  }

  let responder: BroadcastChannel | null = null;

  /** Answer other tabs, and hand signing out to `onSignOut` when it is this session that ended. */
  function serve(onSignOut: () => void): void {
    if (responder) return;
    responder = open();
    if (!responder) return;
    responder.onmessage = (event: MessageEvent<Message>) => {
      const message = event.data;
      if (message.type === "request") {
        const values = held();
        const activeAt = lastActive();
        if (values && Date.now() - activeAt <= MAX_IDLE_MS) {
          responder?.postMessage({ type: "session", values, activeAt } satisfies Message);
        }
      } else if (message.type === "signout") {
        try {
          if (sessionStorage.getItem(tokenKey) === message.token) onSignOut();
        } catch {
          // Storage blocked: there is no session here to end.
        }
      }
    };
  }

  /** Before the first render: take a session from an open tab, if this one has none. */
  function adopt(): Promise<void> {
    if (!mayAdopt(window.location.pathname) || held()) return Promise.resolve();
    const asking = open();
    if (!asking) return Promise.resolve();
    return new Promise((resolve) => {
      let best: { values: Record<string, string>; activeAt: number } | null = null;
      let moreTimer: number | undefined;
      const finish = () => {
        window.clearTimeout(timer);
        window.clearTimeout(moreTimer);
        asking.close();
        if (best) {
          try {
            for (const key of keys) {
              const value = best.values[key];
              if (typeof value === "string") sessionStorage.setItem(key, value);
            }
          } catch {
            // Storage blocked: this tab stays signed out.
          }
        }
        resolve();
      };
      const timer = window.setTimeout(finish, WAIT_MS);
      asking.onmessage = (event: MessageEvent<Message>) => {
        const message = event.data;
        if (message.type !== "session") return;
        if (best === null) moreTimer = window.setTimeout(finish, MORE_MS);
        if (best === null || message.activeAt > best.activeAt) {
          best = { values: message.values, activeAt: message.activeAt };
        }
      };
      asking.postMessage({ type: "request" } satisfies Message);
    });
  }

  /** Tell the other tabs this session ended. */
  function announceSignOut(token: string | null): void {
    if (token) responder?.postMessage({ type: "signout", token } satisfies Message);
  }

  return { serve, adopt, announceSignOut };
}
