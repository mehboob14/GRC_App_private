import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRoutes } from "@/app/routes";
import { ToastProvider, TooltipProvider } from "@/components/ui";
import { ThemeProvider } from "@/lib/theme-provider";
import { AuthProvider } from "@/lib/auth/auth-provider";
import { ApiError, mocksEnabled } from "@/lib/api/client";
import { ErrorBoundary } from "@/components/error-boundary";

import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/sora/600.css";
import "@fontsource/sora/700.css";
import "@fontsource/sora/800.css";
import "@/styles/tokens.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // A blanket `retry: 1` retried 403s and 404s, which can never succeed, and
      // gave a dropped connection only one attempt. Retry what is transient
      // (offline, timeout, 429, 5xx) and fail the rest immediately so the
      // reader sees the real answer without waiting through a pointless round.
      retry: (failureCount, error) =>
        error instanceof ApiError && error.retryable && failureCount < 3,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Never auto-retry a write: it could double-apply a side effect.
      retry: false,
    },
  },
});

async function enableMocks() {
  if (!mocksEnabled()) return;
  const { startWorker } = await import("@/mocks/browser");
  await startWorker();

  // The browser can terminate an idle service worker; a restarted MSW
  // worker has lost its active-client set, so it silently passes every
  // request through to the Vite proxy, which 500s (no real backend behind
  // mocks). Ping a mock endpoint to keep the worker alive and re-handshake
  // whenever a ping slips through anyway. apiFetch carries the same
  // self-heal for requests that hit the dead window between pings.
  window.setInterval(() => {
    fetch("/api/v1/_mock/health")
      .then((res) => {
        if (!res.ok) return startWorker().then(() => undefined);
        return undefined;
      })
      .catch(() => undefined);
  }, 15_000);
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element #root not found");
}

void enableMocks().then(() => {
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ToastProvider>
            <TooltipProvider>
              <BrowserRouter>
                <ErrorBoundary>
                  <AuthProvider>
                    <AppRoutes />
                  </AuthProvider>
                </ErrorBoundary>
              </BrowserRouter>
            </TooltipProvider>
          </ToastProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
});
