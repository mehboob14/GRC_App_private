import type { Metadata } from "next";
import Link from "next/link";
import { GuideMarkdown } from "@/components/guide-markdown";
import { GuideSearch } from "@/components/guide-search";
import { GuideSidebar } from "@/components/guide-sidebar";
import { getGuidePages, guidePath } from "@/lib/guide";

export const metadata: Metadata = { title: "User guide", description: "Step-by-step help for using Verity day to day.", alternates: { canonical: "/docs/" } };

const journeys = [
  { label: "New to Verity", detail: "Set up and find your way around", slug: "01-getting-started" },
  { label: "Running the audit", detail: "Work through controls and evidence", slug: "03-frameworks-and-controls" },
  { label: "Managing third parties", detail: "Follow the vendor lifecycle", slug: "08-vendors" },
  { label: "Administering a workspace", detail: "People, roles, and security settings", slug: "12-settings-and-administration" },
];

export default function DocsHome() {
  const pages = getGuidePages();
  const overview = pages[0];
  return <main id="main-content" className="docs-main">
    <div className="docs-hero"><div className="site-container"><h1>Verity user guide</h1><p>Find instructions for setup, controls, evidence, tasks, risks, vendors, and administration.</p><GuideSearch /></div></div>
    <div className="site-container docs-layout"><GuideSidebar pages={pages} current="" /><div className="docs-content">
      <section className="guide-journeys" aria-labelledby="journeys-title"><div className="docs-section-label">START WITH YOUR ROLE</div><h2 id="journeys-title">What are you here to do?</h2><div className="journey-grid">{journeys.map((journey) => <Link href={guidePath(journey.slug)} key={journey.slug}><span>{journey.label}</span><small>{journey.detail}</small></Link>)}</div></section>
      <section className="chapter-list" aria-labelledby="chapters-title"><div className="docs-section-label">THE COMPLETE GUIDE</div><h2 id="chapters-title">Explore every chapter</h2><div className="chapter-grid">{pages.filter((page) => page.slug).map((page) => <Link href={guidePath(page.slug)} key={page.slug}><span>{page.slug.slice(0, 2)}</span><div><strong>{page.title}</strong><small>{page.description}</small></div></Link>)}</div></section>
      <section className="guide-release-notes" aria-labelledby="release-title"><div className="docs-section-label">ABOUT THIS RELEASE</div><h2 id="release-title">Read the guide with context</h2><p>The Dashboard screen is a preview with illustrative figures. Screens marked “Soon” are not built yet. Screenshots come from a demonstration workspace with invented names, numbers, and people.</p></section>
      <details className="full-guide-overview"><summary>Read the full guide introduction</summary><article className="prose-guide"><GuideMarkdown page={overview} /></article></details>
    </div></div>
  </main>;
}
