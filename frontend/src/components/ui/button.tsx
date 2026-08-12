import { Slot } from "@radix-ui/react-slot";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const variants = {
  primary:
    "bg-action-primary text-action-primary-fg hover:brightness-110 disabled:bg-action-primary/40",
  secondary:
    "bg-surface-primary text-text-primary border border-border hover:bg-surface-hover disabled:text-text-subtle",
  ghost: "bg-transparent text-text-secondary hover:bg-surface-hover hover:text-text-primary",
  destructive:
    "bg-status-danger-base text-text-inverse hover:brightness-110 disabled:bg-status-danger-base/40",
  "destructive-2":
    "bg-transparent text-status-danger-text border border-status-danger-border hover:bg-status-danger-bg",
  "success-2":
    "bg-status-success-bg text-status-success-text border border-status-success-base/20 hover:brightness-95",
  link: "bg-transparent text-action-accent underline-offset-4 hover:underline px-0 h-auto",
} as const;

const sizes = {
  sm: "h-7 px-2.5 text-label-sm rounded-sm gap-1.5",
  md: "h-9 px-3.5 text-label-md rounded-md gap-2",
  lg: "h-11 px-5 text-label-md rounded-md gap-2",
  icon: "size-9 rounded-md p-0",
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
    return (
      <Comp
        ref={ref}
        type={asChild ? undefined : type}
        aria-busy={loading || undefined}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center font-sans font-semibold transition-colors",
          "disabled:pointer-events-none disabled:opacity-60",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
          variants[variant],
          sizes[size],
          loading && "relative",
          className,
        )}
        {...props}
      >
        {children}
      </Comp>
    );
  },
);

Button.displayName = "Button";
