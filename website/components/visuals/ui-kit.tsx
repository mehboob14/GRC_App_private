import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";

/**
 * Small pieces of the Verity product interface, rebuilt with the product's own
 * status colours (frontend/src/styles/tokens.css) so compositions on the site
 * read as the real application. All data shown with them is sample data.
 */

export type Family = "success" | "danger" | "warning" | "progress" | "pending" | "neutral";

const family: Record<Family, string> = {
  success: "bg-[#E7F5EF] text-[#08794F] border-[#C7E9D9]",
  danger: "bg-[#FDEEF1] text-[#C01741] border-[#F6CFD8]",
  warning: "bg-[#FBF1E4] text-[#9A5007] border-[#F0D9B4]",
  progress: "bg-[#EAF4FB] text-[#0369A1] border-[#BEDBF0]",
  pending: "bg-[#F3EFFC] text-[#6947C7] border-[#DBD0F6]",
  neutral: "bg-[#F0F2F5] text-[#566072] border-[#D6DBE3]",
};

export const familyBase: Record<Family, string> = {
  success: "#059669",
  danger: "#E11D48",
  warning: "#D97706",
  progress: "#0284C7",
  pending: "#7C5CD6",
  neutral: "#64748B",
};

export function Pill({ tone, children, icon, className }: { tone: Family; children: ReactNode; icon?: IconName; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-[3px] text-[11.5px] font-medium leading-none", family[tone], className)}>
      {icon && <Icon name={icon} size={12} weight="bold" />}
      {children}
    </span>
  );
}

/** The reference's "✓ Success" chip that sits above a step card. */
export function OutcomePill({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <span style={style} className={cn("inline-flex items-center gap-1.5 rounded-md border border-[#BFE5B4] bg-[#F3FBEF] px-2 py-1 text-[12.5px] font-medium leading-none text-[#2F7D1A]", className)}>
      <Icon name="check" size={14} />
      {children}
    </span>
  );
}

const severityTone: Record<string, string> = {
  Critical: "bg-[#FDEEF1] text-[#C01741] border-[#F6CFD8]",
  High: "bg-[#FFF1E8] text-[#C2410C] border-[#FBD5BC]",
  Medium: "bg-[#FBF1E4] text-[#9A5007] border-[#F0D9B4]",
  Low: "bg-[#E7F5EF] text-[#08794F] border-[#C7E9D9]",
  Info: "bg-[#EAF4FB] text-[#0369A1] border-[#BEDBF0]",
};

export function Severity({ level }: { level: keyof typeof severityTone | string }) {
  return <span className={cn("inline-flex rounded border px-1.5 py-[3px] text-[11px] font-medium leading-none", severityTone[level] ?? severityTone.Info)}>{level}</span>;
}

export function Avatar({ name, className }: { name: string; className?: string }) {
  const initials = name.split(" ").map((part) => part[0]).slice(0, 2).join("");
  return <span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#EEF1F6] font-mono text-[9.5px] font-semibold text-[#45526A] ring-1 ring-[#D6DBE3]", className)} aria-hidden="true">{initials}</span>;
}

export function CodeChip({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex rounded border border-[#D6DBE3] bg-[#F7F8FA] px-1.5 py-[3px] font-mono text-[10.5px] font-medium leading-none text-[#45526A]", className)}>{children}</span>;
}

/** A floating product card: optional icon + title header, then content. */
export function Panel({ title, icon, meta, children, className, bodyClassName, style }: { title?: ReactNode; icon?: IconName; meta?: ReactNode; children: ReactNode; className?: string; bodyClassName?: string; style?: CSSProperties }) {
  return (
    <div style={style} className={cn("overflow-hidden rounded-xl border border-[#E3E7EC] bg-white text-left shadow-float", className)}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-[#EDF0F3] px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            {icon && <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#E3E7EC] text-[#0B0F17]"><Icon name={icon} size={16} /></span>}
            <span className="truncate text-[14px] font-semibold text-[#0B0F17]">{title}</span>
          </div>
          {meta}
        </div>
      )}
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </div>
  );
}

/** "Sample data" caption that accompanies every composition. */
export function SampleNote({ className, children = "Illustrative sample data" }: { className?: string; children?: ReactNode }) {
  return <p className={cn("font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint", className)}>{children}</p>;
}

export function Legend({ items, className }: { items: { label: string; value?: ReactNode; color: string }[]; className?: string }) {
  return (
    <ul className={cn("flex flex-wrap gap-x-3.5 gap-y-1.5 text-[11.5px] text-[#45526A]", className)}>
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-[2px]" style={{ background: item.color }} aria-hidden="true" />
          {item.label}
          {item.value !== undefined && <span className="font-semibold text-[#0B0F17] tabular">{item.value}</span>}
        </li>
      ))}
    </ul>
  );
}
