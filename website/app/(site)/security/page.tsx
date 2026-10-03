import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { FaqSection, FinalCta, PageHero } from "@/components/sections/common";
import { SectionShell } from "@/components/sections/pillar";
import { SectionHeading } from "@/components/ui/section-heading";
import { Icon, type IconName } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { Panel, Pill } from "@/components/visuals/ui-kit";

export const metadata: Metadata = {
  title: "Security at Verity",
  description: "How Verity protects your workspace: database-enforced isolation, least-privilege access, an append-only audit log, encrypted secrets and read-only connections.",
  alternates: { canonical: "/security/" },
};

const areas: { icon: IconName; title: string; points: string[] }[] = [
  { icon: "lock", title: "Workspace isolation", points: ["Every workspace is sealed by the database itself, on every query, not by the interface.", "A person in two organisations sees one at a time; no screen, filter or export shows two workspaces together.", "Automated isolation tests run on every change to prove one workspace cannot read another."] },
  { icon: "users", title: "Access control", points: ["Six built-in roles, groups and granular permissions for each module and action.", "Two-factor sign-in can be required for administrators; passwords need 12 characters with mixed case, a digit and a symbol by default.", "External auditors and consultants get access windows that close on their own.", "Leavers are disabled, not deleted, so their approvals and evidence stay attributable."] },
  { icon: "scroll", title: "A history you can trust", points: ["Every state-changing action writes who, when, and the record before and after.", "The audit log is append-only, enforced by the database: nobody can edit or delete it, administrators included.", "Controls, risks, documents and vendors are retired with a recorded reason, never deleted."] },
  { icon: "key", title: "Secrets and connections", points: ["Connection tokens and two-factor secrets are encrypted in the application before they reach the database, and never written to logs.", "Connections ask for read-only, least-privilege access. Disconnecting destroys the token; the history stays.", "A broken connection is reported as an error, never as a failed control."] },
  { icon: "folder", title: "Evidence handling", points: ["Evidence files are kept in object storage, not in the database.", "A file you upload cannot change underneath you, which is what an auditor needs.", "Evidence carries renewal dates, so stale proof is visible."] },
  { icon: "sparkle", title: "AI governance", points: ["AI drafts and suggests; a person approves, publishes and decides.", "AI content is marked as an AI draft and goes through the same approval as anything a person writes.", "If an AI provider is unavailable, you can always do the work by hand."] },
];

const faqs = [
  { q: "Is Verity SOC 2 or ISO 27001 certified?", a: "We do not claim certifications on this site. If your procurement process needs our security documentation, talk to our team and we will tell you what is available and when." },
  { q: "Where is our data hosted?", a: "Talk to our team about hosting and data-residency requirements, especially if you are a regulated institution with in-country obligations." },
  { q: "Can our auditor see our workspace?", a: "Yes. Invite them with an access window: they can sign in between the dates you set, with the role you choose, and every action they take is in the audit log." },
  { q: "Do you support single sign-on?", a: "Single sign-on through your identity provider is coming soon. Today Verity uses email and password sign-in, with two-factor authentication that you can require for administrators." },
];

export default function SecurityPage() {
  return (
    <main id="main-content">
      <PageHero
        eyebrow="Security at Verity"
        title="Built like the controls it tracks."
        lead={<p>You trust Verity with the evidence that proves your organisation keeps its promises. These are the properties the platform is built around, written plainly so your security and procurement teams can check them.</p>}
        visual={
          <Panel title="Audit log" icon="scroll" meta={<Pill tone="success">Append-only</Pill>} className="mx-auto max-w-md">
            <ul className="space-y-3 text-[13px]">
              {[
                ["Dana Okafor", "approved evidence", "Q3 access review sign-off"],
                ["Ayesha Raza", "changed control status", "IAM-02 · In progress → Implemented"],
                ["Omar Haddad", "accepted a risk until 31 Mar", "Legacy VPN appliance"],
                ["Sofia Martins", "decided a vendor", "Harbor Cloud Hosting · Approved with conditions"],
              ].map(([who, what, record]) => (
                <li key={record} className="flex gap-3">
                  <Icon name="clock" size={15} className="mt-0.5 shrink-0 text-faint" />
                  <span><span className="font-medium text-ink">{who}</span> <span className="text-dim">{what}</span><span className="block text-dim">{record}</span></span>
                </li>
              ))}
            </ul>
            <p className="mt-4 border-t border-line pt-3 font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">Sample entries · before and after kept for each</p>
          </Panel>
        }
      />

      <SectionShell id="properties" labelledBy="properties-title">
        <SectionHeading eyebrow="How the platform protects you" title="Six properties, and how each one holds." id="properties-title" />
        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2">
          {areas.map((area, index) => (
            <section key={area.title} className="rounded-2xl border border-line bg-surface p-7 shadow-card" data-reveal style={{ ["--reveal-delay" as string]: `${(index % 2) * 90}ms` } as CSSProperties} aria-labelledby={`area-${index}`}>
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-sky-50 text-sky-700"><Icon name={area.icon} size={21} /></span>
                <h3 id={`area-${index}`} className="text-[18px] font-semibold">{area.title}</h3>
              </div>
              <ul className="mt-5 space-y-3">
                {area.points.map((point) => (
                  <li key={point} className="flex gap-3 text-[15px] leading-relaxed text-body"><Icon name="check-plain" size={16} weight="bold" className="mt-1 shrink-0 text-emerald-600" />{point}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <div className="mt-10 flex flex-wrap items-center gap-3 rounded-2xl border border-dashed border-indigo-300 bg-indigo-50/50 p-5 text-[15px]">
          <StatusBadge status="soon" />
          <span className="text-body">Coming next: single sign-on through your identity provider, periodic access reviews, and read-only auditor access scoped to an engagement.</span>
          <Link href="/docs/roadmap/single-sign-on/" className="link-arrow ms-auto text-[14px]">Read the roadmap pages<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></Link>
        </div>
      </SectionShell>

      <FaqSection items={faqs} title="Security questions." lead="If your procurement team has a questionnaire, send it to us." />
      <FinalCta title="Bring your security questionnaire." lead="We will walk your team through how Verity protects the evidence you keep with us." source="security-final" />
    </main>
  );
}
