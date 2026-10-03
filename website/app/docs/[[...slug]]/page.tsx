import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getSiteConfig } from "@/lib/site-config";
import { getAllDocs, getDocContent, getDocMeta, getNeighbours, getSidebarGroups, getToc, legacyRedirects, readingMinutes, validateDocs } from "@/lib/docs";
import { mdxComponents } from "@/components/docs/mdx-components";
import { CopyLink, Feedback, OnThisPage, SidebarNav } from "@/components/docs/docs-chrome";
import { DocsHome } from "@/components/docs/docs-home";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";

export const dynamicParams = false;

export function generateStaticParams() {
  validateDocs();
  return [{ slug: [] }, ...getAllDocs().map((page) => ({ slug: page.slug.split("/") })), ...Object.keys(legacyRedirects).map((old) => ({ slug: [old] }))];
}

type Params = { params: Promise<{ slug?: string[] }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug = [] } = await params;
  const path = slug.join("/");
  if (!path) return { title: "Documentation", description: "Task-by-task guides for every Verity module, with screenshots and search.", alternates: { canonical: "/docs/" } };
  const target = legacyRedirects[path];
  if (target) return { title: "Moved", robots: { index: false }, alternates: { canonical: `/docs/${target}/` } };
  const page = getDocMeta(path);
  if (!page) return {};
  return { title: `${page.title} · Docs`, description: page.description, alternates: { canonical: `/docs/${page.slug}/` }, openGraph: { title: `${page.title} · Verity documentation`, description: page.description } };
}

function formatDate(value: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export default async function DocPage({ params }: Params) {
  const { slug = [] } = await params;
  const path = slug.join("/");
  if (!path) return <DocsHome />;

  const moved = legacyRedirects[path];
  if (moved) {
    return (
      <main id="main-content" className="mx-auto max-w-xl px-6 py-24 text-center">
        <meta httpEquiv="refresh" content={`0; url=/docs/${moved}/`} />
        <p className="eyebrow">This page has moved</p>
        <h1 className="mt-3 font-serif text-3xl">The guide was reorganised.</h1>
        <p className="mt-3 text-dim">Its new home is <Link className="font-medium text-accent underline" href={`/docs/${moved}/`}>/docs/{moved}/</Link>.</p>
      </main>
    );
  }

  const page = getDocMeta(path);
  if (!page) notFound();
  const Content = await getDocContent(page.slug);
  const toc = getToc(page.slug);
  const { prev, next } = getNeighbours(page.slug);
  const { feedbackEndpoint } = getSiteConfig();

  return (
    <div className="mx-auto grid max-w-[1600px] grid-cols-1 lg:grid-cols-[288px_minmax(0,1fr)] xl:grid-cols-[288px_minmax(0,1fr)_248px]">
      <aside className="sticky top-[var(--header-h)] hidden h-[calc(100vh-var(--header-h))] overflow-y-auto border-e border-line px-4 py-6 lg:block">
        <SidebarNav groups={getSidebarGroups()} />
      </aside>
      <main id="main-content" className="min-w-0 px-5 pb-24 pt-8 sm:px-10 lg:px-14">
        <article className="mx-auto max-w-prose">
          <nav aria-label="Breadcrumb" className="mb-5 flex flex-wrap items-center gap-1.5 text-[13px] text-dim">
            <Link href="/docs/" className="hover:text-ink">Docs</Link>
            <Icon name="caret-right" size={11} weight="bold" className="text-faint" />
            <span>{page.group.title}</span>
            <Icon name="caret-right" size={11} weight="bold" className="text-faint" />
            <span className="text-ink" aria-current="page">{page.label}</span>
          </nav>
          <header className="mb-8 border-b border-line pb-7">
            <h1 className="font-serif text-[clamp(2rem,1.6rem+1.6vw,2.75rem)] font-normal leading-[1.1] tracking-[-0.015em] text-ink">{page.title}</h1>
            <p className="mt-3 text-[18px] leading-relaxed text-dim">{page.description}</p>
            <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-dim">
              {page.status !== "live" && <StatusBadge status={page.status} />}
              <span className="inline-flex items-center gap-1.5"><Icon name="clock" size={14} />{readingMinutes(page.slug)} min read</span>
              <span>Updated {formatDate(page.updated)}</span>
              <span className="ms-auto"><CopyLink /></span>
            </div>
          </header>
          {page.status === "soon" && (
            <div className="mb-8 flex gap-3 rounded-xl border border-dashed border-indigo-300 bg-indigo-50/60 p-4 text-[15px] leading-relaxed [[data-docs-theme=dark]_&]:border-indigo-800 [[data-docs-theme=dark]_&]:bg-indigo-950/40">
              <Icon name="map" size={20} className="mt-0.5 shrink-0 text-indigo-600 [[data-docs-theme=dark]_&]:text-indigo-300" />
              <p className="text-ink">
                <strong>This feature is coming soon.</strong> It is not available in Verity yet, so nothing on this page describes something you can use today. We publish it so you can see where the product is going and plan for it.{" "}
                <Link href="/demo/?interest=roadmap" className="font-medium text-accent underline">Tell us what you need</Link>.
              </p>
            </div>
          )}
          <OnThisPage toc={toc} mobile />
          <div className="docs-prose">
            <Content components={mdxComponents} />
          </div>
          {feedbackEndpoint && <Feedback endpoint={feedbackEndpoint} slug={page.slug} />}
          <nav aria-label="Previous and next" className="mt-14 grid grid-cols-1 gap-3 border-t border-line pt-8 sm:grid-cols-2">
            {prev ? (
              <Link href={`/docs/${prev.slug}/`} className="group rounded-xl border border-line p-4 transition hover:border-line-strong hover:shadow-card">
                <span className="flex items-center gap-1 text-[12.5px] text-dim"><Icon name="arrow-right" size={13} className="rotate-180" />Previous</span>
                <span className="mt-1 block font-medium text-ink group-hover:text-accent-strong">{prev.title}</span>
              </Link>
            ) : <span />}
            {next && (
              <Link href={`/docs/${next.slug}/`} className="group rounded-xl border border-line p-4 text-end transition hover:border-line-strong hover:shadow-card">
                <span className="flex items-center justify-end gap-1 text-[12.5px] text-dim">Next<Icon name="arrow-right" size={13} /></span>
                <span className="mt-1 block font-medium text-ink group-hover:text-accent-strong">{next.title}</span>
              </Link>
            )}
          </nav>
        </article>
      </main>
      <aside className="sticky top-[var(--header-h)] hidden h-[calc(100vh-var(--header-h))] overflow-y-auto py-10 pe-6 xl:block">
        <OnThisPage toc={toc} />
        <div className="mt-8 border-t border-line pt-5 text-[13px] text-dim">
          <p className="font-medium text-ink">Need a hand?</p>
          <p className="mt-1 leading-relaxed">Screens show a demonstration workspace; your own data appears in the same places.</p>
          <Link href="/demo/" className="mt-3 inline-flex items-center gap-1 font-medium text-accent hover:text-accent-strong">Talk to our team<Icon name="arrow-right" size={13} /></Link>
        </div>
      </aside>
    </div>
  );
}
