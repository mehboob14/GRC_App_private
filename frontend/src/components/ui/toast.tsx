import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";
import {
  ToastContext,
  type ToastItem,
  type ToastOptions,
  type ToastTone,
} from "@/components/ui/toast-context";

const toneIcon: Record<ToastTone, IconName> = {
  success: "check",
  danger: "alert",
  neutral: "info",
};

const toneIconClass: Record<ToastTone, string> = {
  success: "text-status-success-base",
  danger: "text-status-danger-base",
  neutral: "text-text-inverse",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback((options: ToastOptions) => {
    const item: ToastItem = {
      id: nextId.current++,
      title: options.title,
      tone: options.tone ?? "neutral",
      durationMs: options.durationMs ?? 5000,
    };
    setItems((current) => [...current, item]);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-label="Notifications"
        className="pointer-events-none fixed bottom-6 right-6 z-toast flex w-[360px] max-w-[calc(100vw-3rem)] flex-col gap-2"
      >
        {items.map((item) => (
          <Toast key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function Toast({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(item.id), item.durationMs);
    return () => window.clearTimeout(timer);
  }, [item.id, item.durationMs, onDismiss]);

  return (
    <div
      role={item.tone === "danger" ? "alert" : "status"}
      className={cn(
        "animate-toast-in pointer-events-auto flex items-center gap-2.5 rounded-md bg-surface-inverse px-3.5 py-3 shadow-toast",
      )}
    >
      <Icon
        name={toneIcon[item.tone]}
        className={cn("size-4 shrink-0", toneIconClass[item.tone])}
      />
      <p className="min-w-0 flex-1 text-label-md font-semibold text-text-inverse">
        {item.title}
      </p>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(item.id)}
        className="flex size-6 shrink-0 items-center justify-center rounded-xs text-text-inverse/70 hover:bg-white/10 hover:text-text-inverse"
      >
        <Icon name="x" className="size-3.5" />
      </button>
    </div>
  );
}
