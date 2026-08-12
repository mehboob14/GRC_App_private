import { setupWorker } from "msw/browser";
import { handlers } from "@/mocks/handlers";

export const worker = setupWorker(...handlers);

/** One handshake, one option set — main.tsx boot, keepalive and the API
 * client's dev-only self-heal all go through here. */
export function startWorker(): Promise<unknown> {
  return worker.start({
    onUnhandledRequest: "bypass",
    serviceWorker: { url: "/mockServiceWorker.js" },
  });
}
