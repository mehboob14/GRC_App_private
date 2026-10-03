import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "./icon";

type Variant = "dark" | "outline" | "ghost" | "light";

export function ButtonLink({ href, children, variant = "dark", size, arrow = false, className, external = false }: { href: string; children: ReactNode; variant?: Variant; size?: "sm" | "lg"; arrow?: boolean; className?: string; external?: boolean }) {
  const classes = cn("btn", `btn-${variant}`, size && `btn-${size}`, className);
  const content = (
    <>
      {children}
      {arrow && <Icon name="arrow-right" size={16} weight="bold" className="btn-arrow" />}
    </>
  );
  if (external || /^https?:/.test(href)) {
    return <a href={href} className={classes}>{content}</a>;
  }
  return <Link href={href} className={classes}>{content}</Link>;
}

export function ArrowLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={cn("link-arrow", className)}>
      {children}
      <Icon name="arrow-right" size={15} weight="bold" className="btn-arrow" />
    </Link>
  );
}
