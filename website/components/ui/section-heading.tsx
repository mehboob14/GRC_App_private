import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("eyebrow", className)}>{children}</p>;
}

/** Eyebrow, serif title and lead, left-aligned or centred. */
export function SectionHeading({ eyebrow, title, lead, align = "start", id, size = "lg", className, children }: { eyebrow?: string; title: ReactNode; lead?: ReactNode; align?: "start" | "center"; id?: string; size?: "lg" | "md"; className?: string; children?: ReactNode }) {
  return (
    <div className={cn("max-w-3xl", align === "center" && "mx-auto text-center", className)}>
      {eyebrow && <Eyebrow className="mb-4">{eyebrow}</Eyebrow>}
      <h2 id={id} className={cn("font-serif font-normal", size === "lg" ? "text-display-lg" : "text-display-md")}>{title}</h2>
      {lead && <p className={cn("mt-5 text-[17px] leading-relaxed text-dim sm:text-lg", align === "center" && "mx-auto max-w-2xl")}>{lead}</p>}
      {children}
    </div>
  );
}
