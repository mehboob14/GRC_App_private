import { Slot } from "@radix-ui/react-slot";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const variants = {
  primary:
    "bg-accent text-accent-fg hover:brightness-110 disabled:bg-accent/40",
  secondary:
    "bg-bg-elevated text-text border border-border hover:bg-bg-sunken disabled:text-text-faint",
  ghost: "bg-transparent text-text-muted hover:bg-bg-sunken hover:text-text",
  destructive:
    "bg-fail text-text-inverse hover:brightness-110 disabled:bg-fail/40",
  "destructive-2":
    "bg-transparent text-fail-fg border border-fail-border hover:bg-fail-bg",
  "success-2":
    "bg-pass-bg text-pass-fg border border-pass/20 hover:brightness-95",
  link: "bg-transparent text-accent underline-offset-4 hover:underline px-0 h-auto",
} as const;

const sizes = {
  sm: "h-7 px-2.5 text-label-sm rounded-md gap-1.5",
  md: "h-9 px-3.5 text-label-md rounded-lg gap-2",
  lg: "h-11 px-5 text-label-md rounded-lg gap-2",
  icon: "size-9 rounded-lg p-0",
  "icon-sm": "size-7 rounded-md p-0",
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
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
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
