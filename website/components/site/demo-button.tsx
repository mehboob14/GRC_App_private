import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { demoHref } from "@/lib/demo";

// Written out so the stylesheet keeps every variant: a class built from a string is never found by the build.
const VARIANT = {
  dark: "btn btn-dark",
  outline: "btn btn-outline",
  light: "btn btn-light",
  ghost: "btn btn-ghost",
  none: "",
} as const;

/**
 * Every "See a demo" and "Talk to sales" action on the site: a link to the demo
 * request page. `source` and `interest` ride along, so the team learns which button
 * and which topic the request came from.
 */
export function DemoButton({ children, className, interest, source, variant = "none" }: { children: ReactNode; className?: string; interest?: string; source?: string; variant?: keyof typeof VARIANT }) {
  return (
    <Link href={demoHref({ interest, source })} className={cn(VARIANT[variant], className)}>
      {children}
    </Link>
  );
}
