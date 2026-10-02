import Link from "next/link";
import type { GuidePage } from "@/lib/guide";
import { guidePath } from "@/lib/guide";

function ChapterLinks({ pages, current }: { pages: GuidePage[]; current: string }) {
  return <nav aria-label="Guide chapters"><Link className={current === "" ? "active" : ""} href="/docs/">Guide home</Link>{pages.filter((page) => page.slug).map((page) => <Link key={page.slug} className={current === page.slug ? "active" : ""} href={guidePath(page.slug)} aria-current={current === page.slug ? "page" : undefined}><span>{page.slug.slice(0, 2)}</span>{page.title}</Link>)}</nav>;
}

export function GuideSidebar({ pages, current }: { pages: GuidePage[]; current: string }) {
  return <>
    <aside className="guide-sidebar desktop-guide-sidebar"><div className="sidebar-title">USER GUIDE <span>01—13</span></div><ChapterLinks pages={pages} current={current} /></aside>
    <details className="mobile-guide-sidebar"><summary>Browse guide chapters</summary><ChapterLinks pages={pages} current={current} /></details>
  </>;
}
