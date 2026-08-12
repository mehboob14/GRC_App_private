import { Slot } from "@radix-ui/react-slot";
import {
  forwardRef,
  useLayoutEffect,
  useRef,
  type ButtonHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

/**
 * DS §5.1 button hierarchy. Filled variants carry Inter 700 labels, outline
 * and ghost variants Inter 600. One primary per region.
 */
const variants = {
  primary:
    "bg-action-primary font-bold text-action-primary-fg hover:bg-action-primary-hover",
  secondary:
    "border border-border bg-surface-primary font-semibold text-text-primary hover:bg-surface-hover",
  ghost:
    "bg-transparent font-semibold text-text-secondary hover:bg-surface-hover hover:text-text-primary",
  destructive:
    "bg-action-danger font-bold text-action-danger-fg hover:bg-action-danger-hover",
  "destructive-2":
    "border border-status-danger-border bg-surface-primary font-bold text-status-danger-text hover:bg-action-danger-tint",
  "success-2":
    "bg-status-success-bg font-bold text-status-success-text hover:bg-status-success-border/60",
  link: "h-auto bg-transparent px-0 font-semibold text-text-link underline-offset-4 hover:underline",
} as const;

/** DS §5.3 — sm 28 / md 36 / lg 44, padding-x 12/16/16, radius sm (8). */
const sizes = {
  sm: "h-7 gap-1.5 rounded-sm px-3 text-label-sm",
  md: "h-9 gap-1.5 rounded-sm px-4 text-label-md",
  lg: "h-11 gap-1.5 rounded-sm px-4 text-label-md",
  icon: "size-9 rounded-sm p-0",
  "icon-sm": "size-7 rounded-sm p-0",
} as const;

export type ButtonVariant = keyof typeof variants;
export type ButtonSize = keyof typeof sizes;

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      asChild = false,
      loading = false,
      disabled,
      children,
      type = "button",
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    const innerRef = useRef<HTMLButtonElement | null>(null);

    // DS §5.2: while loading the width is locked so the label swap
    // ("Add" → "Adding…") cannot shift the layout.
    useLayoutEffect(() => {
      const el = innerRef.current;
      if (!el) return;
      if (loading) {
        el.style.minWidth = `${el.offsetWidth}px`;
      } else {
        el.style.removeProperty("min-width");
      }
    }, [loading]);

    return (
      <Comp
        ref={(node: HTMLButtonElement | null) => {
          innerRef.current = node;
          if (typeof ref === "function") ref(node);
          else if (ref) ref.current = node;
        }}
        type={asChild ? undefined : type}
        aria-busy={loading || undefined}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center font-sans transition-colors duration-80 ease-state",
          "disabled:pointer-events-none disabled:opacity-45",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      >
        {loading ? (
          <Icon name="spinner" className="size-3.5 animate-spin" />
        ) : null}
        {children}
      </Comp>
    );
  },
);

Button.displayName = "Button";
