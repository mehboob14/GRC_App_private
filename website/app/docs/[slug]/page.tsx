import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { GuideMarkdown } from "@/components/guide-markdown";
import { GuideSearch } from "@/components/guide-search";
import { GuideSidebar } from "@/components/guide-sidebar";
import { getGuidePages, guidePath } from "@/lib/guide";

type Props = { params: Promise<{ slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return getGuidePages().filter((page) => page.slug).map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const page = getGuidePages().find((item) => item.slug === slug);
  if (!page) return {};
  return { title: page.title, description: page.description, alternates: { canonical: guidePath(slug) } };
}

export default async function GuideChapter({ params }: Props) {
  const { slug } = await params;
  const pages = getGuidePages();
  const index = pages.findIndex((page) => page.slug === slug);
  if (index < 1) notFound();
  const page = pages[index];
  const previous = pages[index - 1];
  const next = pages[index + 1];
  return <main id="main-content" className="docs-main docs-chapter-main"><div className="site-container docs-layout"><GuideSidebar pages={pages} current={slug} /><div className="docs-content docs-article-column">
    <div className="guide-breadcrumb"><Link href="/docs/">User guide</Link><span aria-hidden="true">/</span><span>{page.title}</span></div>
    <div className="article-topline"><span>CHAPTER {slug.slice(0, 2)} / 13</span><span>VERITY USER GUIDE</span></div>
    <article className="prose-guide"><GuideMarkdown page={page} /></article>
    <nav className="chapter-pagination" aria-label="Chapter navigation"><Link href={guidePath(previous.slug)}><small>PREVIOUS CHAPTER</small><strong>{previous.title}</strong></Link>{next ? <Link href={guidePath(next.slug)}><small>NEXT CHAPTER</small><strong>{next.title}</strong></Link> : <Link href="/docs/"><small>BACK TO</small><strong>Guide home</strong></Link>}</nav>
  </div><aside className="article-rail"><div className="rail-search"><GuideSearch /></div><div className="rail-heading">ON THIS PAGE</div><nav aria-label="On this page">{page.headings.filter((heading) => heading.depth === 2 || heading.depth === 3).map((heading) => <a className={heading.depth === 3 ? "toc-nested" : ""} href={`#${heading.id}`} key={heading.id}>{heading.text}</a>)}</nav><div className="rail-note">Screenshots use demonstration data. Your workspace will show your own records.</div></aside></div></main>;
}
