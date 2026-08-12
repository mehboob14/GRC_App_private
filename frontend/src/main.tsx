import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRoutes } from "@/app/routes";
import { ToastProvider, TooltipProvider } from "@/components/ui";
import { ThemeProvider } from "@/lib/theme";
import { AuthProvider } from "@/lib/auth/auth-context";
import { mocksEnabled } from "@/lib/api/client";

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
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

async function enableMocks() {
  if (!mocksEnabled()) return;
  const { worker } = await import("@/mocks/browser");
  await worker.start({
    onUnhandledRequest: "bypass",
    serviceWorker: { url: "/mockServiceWorker.js" },
  });
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
                <AuthProvider>
                  <AppRoutes />
                </AuthProvider>
              </BrowserRouter>
            </TooltipProvider>
          </ToastProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
});
