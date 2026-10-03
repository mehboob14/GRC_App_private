import Link from "next/link";
import { cn } from "@/lib/cn";

/** The Verity mark: an isometric cube (the same language as the site art) carrying a check. */
export function BrandMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <path d="M16 2.5 28 9.25 16 16 4 9.25Z" fill="#7DD3FC" />
      <path d="M4 9.25 16 16v13.5L4 22.75Z" fill="#0EA5E9" />
      <path d="M16 16 28 9.25v13.5L16 29.5Z" fill="#0369A1" />
      <path d="m9.6 16.4 4.6 4.4 8.6-9.6" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ className, suffix, href = "/" }: { className?: string; suffix?: string; href?: string }) {
  return (
    <Link href={href} className={cn("inline-flex shrink-0 items-center gap-2 rounded-md text-ink", className)} aria-label={suffix ? `Verity ${suffix} home` : "Verity home"}>
      <BrandMark />
      <span className="text-[21px] font-semibold leading-none tracking-[-0.035em]">verity</span>
      {suffix && <span className="ms-1 border-s border-line-strong ps-2.5 text-[15px] font-medium leading-none tracking-tight text-dim">{suffix}</span>}
    </Link>
  );
}
