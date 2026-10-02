import Link from "next/link";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link className={`brand ${light ? "brand-light" : ""}`} href="/" aria-label="Verity home">
      <svg className="brand-symbol" viewBox="0 0 34 34" fill="none" aria-hidden="true">
        <path d="M17 2 31 10v14L17 32 3 24V10L17 2Z" stroke="currentColor" strokeWidth="2.4" />
        <path d="m10 17 5 5 9-10" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>verity<span className="brand-period">.</span></span>
    </Link>
  );
}
