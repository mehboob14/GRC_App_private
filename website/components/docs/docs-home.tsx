import Link from "next/link";
import type { CSSProperties } from "react";
import { getAllDocs, getSidebarGroups } from "@/lib/docs";
import { Icon, type IconName } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { PopularSearches, SearchButton } from "./search-dialog";

/** Role-based entry points, adapted from the user guide's "Start here" table. */
const roles: { icon: IconName; role: string; text: string; links: { label: string; slug: string }[] }[] = [
  { icon: "rocket", role: "New to Verity", text: "Sign in, find your way around and make a new workspace useful.", links: [{ label: "Your first half hour", slug: "get-started/quick-start" }, { label: "Finding your way around", slug: "get-started/navigating-verity" }] },
  { icon: "seal", role: "Running the audit", text: "Frameworks, readiness and the evidence behind every control.", links: [{ label: "Frameworks and readiness", slug: "compliance/frameworks" }, { label: "Evidence", slug: "compliance/evidence" }] },
  { icon: "user-check", role: "A control owner", text: "Work your controls, attach proof and close the tasks assigned to you.", links: [{ label: "Controls", slug: "compliance/controls" }, { label: "Tasks and issues", slug: "tasks/overview" }] },
  { icon: "file", role: "Writing policies", text: "Draft from a template, route for approval and get it acknowledged.", links: [{ label: "Draft a policy", slug: "policies/documents-and-policies" }, { label: "Acknowledgement campaigns", slug: "policies/acknowledgement-campaigns" }] },
  { icon: "handshake", role: "Managing third parties", text: "Requests, tiering, questionnaires, findings and offboarding.", links: [{ label: "How vendor risk works", slug: "vendors/overview" }, { label: "Tiering", slug: "vendors/tiering" }] },
  { icon: "server", role: "Looking after the estate", text: "Keep the asset inventory current and fix what matters first.", links: [{ label: "Asset inventory", slug: "assets/inventory" }, { label: "Findings and priority", slug: "vulnerabilities/findings-and-priority" }] },
  { icon: "gear", role: "Administering the workspace", text: "People, roles, two-factor rules and the audit log.", links: [{ label: "People and invitations", slug: "admin/people" }, { label: "Audit log and isolation", slug: "admin/audit-log-and-isolation" }] },
];

const popular = ["Invite someone", "Accept a risk", "Import assets", "Evidence freshness"];

export function DocsHome() {
  const groups = getSidebarGroups();
  const pages = getAllDocs();
  const soon = pages.filter((page) => page.status === "soon");
  return (
    <main id="main-content">
      <section className="relative overflow-hidden border-b border-line bg-gradient-to-b from-[#E6ECF2] to-[rgb(var(--canvas))] [[data-docs-theme=dark]_&]:from-[#121a26]">
        <div className="mx-auto max-w-[1200px] px-5 pb-14 pt-14 sm:px-8 lg:pb-20 lg:pt-20">
          <p className="eyebrow">Verity documentation</p>
          <h1 className="mt-4 max-w-3xl font-serif text-[clamp(2.4rem,1.6rem+3vw,3.6rem)] font-normal leading-[1.06] tracking-[-0.02em] text-ink">Learn Verity, one task at a time.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-dim">Walkthroughs with screenshots for every module, written for the people who use Verity every day: compliance leads, control owners, risk and security teams, and workspace administrators.</p>
          <div className="mt-8 max-w-xl">
            <SearchButton className="h-12 w-full text-[15px]" />
          </div>
          <PopularSearches terms={popular} />
        </div>
      </section>

      <div className="mx-auto max-w-[1200px] px-5 py-14 sm:px-8 lg:py-20">
        <section aria-labelledby="roles-title">
          <h2 id="roles-title" className="font-serif text-display-sm font-normal">Start where you are</h2>
          <p className="mt-2 text-[16px] text-dim">Pick the job you are here to do.</p>
          <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {roles.map((role, index) => (
              <li key={role.role} data-reveal style={{ ["--reveal-delay" as string]: `${index * 50}ms` } as CSSProperties} className="flex flex-col rounded-2xl border border-line bg-surface p-5 shadow-card">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-sky-50 text-sky-700 [[data-docs-theme=dark]_&]:bg-sky-950/60 [[data-docs-theme=dark]_&]:text-sky-300"><Icon name={role.icon} size={20} /></span>
                <h3 className="mt-4 text-[17px] font-semibold text-ink">{role.role}</h3>
                <p className="mt-1 text-[14.5px] leading-snug text-dim">{role.text}</p>
                <ul className="mt-4 space-y-1.5 border-t border-line pt-3">
                  {role.links.map((link) => (
                    <li key={link.slug}><Link href={`/docs/${link.slug}/`} className="link-arrow text-[14px]">{link.label}<Icon name="arrow-right" size={13} weight="bold" className="btn-arrow" /></Link></li>
                  ))}
                </ul>
              </li>
            ))}
            <li className="flex flex-col justify-between rounded-2xl border border-line bg-[#0B0F17] p-5 text-white">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-sky-300">Key concepts</p>
                <h3 className="mt-3 font-serif text-[24px] leading-tight">How the pieces fit together</h3>
                <p className="mt-2 text-[14px] leading-snug text-white/70">Controls, evidence, owners, linked records and the audit log, in ten minutes.</p>
              </div>
              <Link href="/docs/get-started/key-concepts/" className="btn btn-light btn-sm mt-6 self-start">Read key concepts<Icon name="arrow-right" size={14} /></Link>
            </li>
          </ul>
        </section>

        <section aria-labelledby="browse-title" className="mt-20">
          <h2 id="browse-title" className="font-serif text-display-sm font-normal">Browse by area</h2>
          <div className="mt-8 grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {groups.map((group) => (
              <div key={group.id}>
                <h3 className="flex items-center gap-2 text-[15px] font-semibold text-ink"><Icon name={group.icon} size={18} className="text-dim" />{group.title}</h3>
                <ul className="mt-3 space-y-1 border-s border-line ps-4">
                  {group.items.map((item) => (
                    <li key={item.slug}>
                      <Link href={`/docs/${item.slug}/`} className="flex items-center gap-2 py-1 text-[14.5px] text-dim transition-colors hover:text-accent-strong">
                        {item.label}
                        {item.status !== "live" && <StatusBadge status={item.status} size="xs" />}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="notes-title" className="mt-20 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-line bg-subtle p-6">
            <h2 id="notes-title" className="flex items-center gap-2 text-[17px] font-semibold text-ink"><Icon name="list" size={19} />Two notes on this release</h2>
            <p className="mt-3 text-[15px] leading-relaxed text-body"><strong className="text-ink">The Dashboard screen is a preview.</strong> It shows the shape of the executive view with illustrative figures. Every live number lives on the module you are looking at.</p>
            <p className="mt-3 text-[15px] leading-relaxed text-body"><strong className="text-ink">Screens marked “Soon” are not built yet.</strong> They show where the product is going; nothing behind a Soon badge holds real data.</p>
            <Link href="/docs/reference/release-notes/" className="link-arrow mt-4 text-[14px]">Read the release notes<Icon name="arrow-right" size={13} weight="bold" className="btn-arrow" /></Link>
          </div>
          <div className="rounded-2xl border border-dashed border-indigo-300 bg-indigo-50/50 p-6 [[data-docs-theme=dark]_&]:border-indigo-800 [[data-docs-theme=dark]_&]:bg-indigo-950/30">
            <h2 className="flex items-center gap-2 text-[17px] font-semibold text-ink"><Icon name="map" size={19} />Coming soon</h2>
            <p className="mt-3 text-[15px] leading-relaxed text-body">We document planned features too, so you can plan ahead. Each page says clearly that the feature is not available yet.</p>
            <ul className="mt-4 flex flex-wrap gap-2">
              {soon.map((page) => <li key={page.slug}><Link href={`/docs/${page.slug}/`} className="chip hover:border-line-strong hover:text-ink">{page.label}</Link></li>)}
            </ul>
          </div>
        </section>

        <p className="mt-14 text-center text-[13.5px] text-dim">Screenshots come from a demonstration workspace, so the names, numbers and people in them are invented. Your workspace shows your own data in the same places.</p>
      </div>
    </main>
  );
}
