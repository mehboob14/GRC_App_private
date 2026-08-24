import { createContext, useContext } from "react";
import type { StatusFamily } from "@/components/ui/status-pill";

/**
 * DS §7.2 toast — the channel for a user-triggered result (and completion of
 * long-running jobs). Never a validation error (inline under the field),
 * never an ongoing condition (page banner).
 *
 * The context and its hook live here rather than in `toast.tsx` so that module
 * exports only components; a file that mixes the two loses fast refresh.
 */
export type ToastTone = Extract<StatusFamily, "success" | "danger" | "neutral">;

export type ToastOptions = {
  title: string;
  tone?: ToastTone;
  /** Defaults to the DS 5s. */
  durationMs?: number;
};

export type ToastItem = Required<ToastOptions> & { id: number };

export type ToastContextValue = {
  toast: (options: ToastOptions) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
