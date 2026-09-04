import { Badge, Icon } from "@/components/ui";
import type { VulnInstanceDetail, VulnReference } from "../types";

/**
 * Where each fact on this finding came from.
 *
 * A vulnerability page asks the reader to accept a lot on trust — that this CVE
 * is on CISA's catalogue, that EPSS puts it in the 99th percentile, that a patch
 * exists. None of that is checkable from a badge. Every link here goes to the
 * primary source for one of those claims, so an analyst deciding whether to
 * wake someone at 2am, or an auditor asking how you knew, can go and look.
 *
 * The list is built server-side and only ever contains sources for facts this
 * finding actually carries — there is no KEV link on a CVE that is not on the
 * catalogue.
 */

const GROUPS: Array<{ backs: string; title: string; blurb: string }> = [
  { backs: "kev", title: "Known exploited", blurb: "CISA's catalogue, behind the KEV badge." },
  { backs: "exploit", title: "Exploit intelligence", blurb: "Published exploits and public proof-of-concept code." },
  { backs: "epss", title: "Exploit probability", blurb: "The EPSS score, from FIRST." },
  { backs: "patch", title: "The fix", blurb: "The vendor's own advisory." },
  { backs: "cve", title: "The record", blurb: "What this CVE is, from the authorities that publish it." },
];

export function SourcesPanel({ vuln }: { vuln: VulnInstanceDetail }) {
  const refs = vuln.references ?? [];
  const kevDetail =
    vuln.kev_flag && (vuln.kev_vendor || vuln.kev_product || vuln.kev_due_at || vuln.kev_required_action);

  if (refs.length === 0 && !kevDetail) {
    return (
      <section className="rounded-lg border border-border bg-surface-primary p-5">
        <h2 className="font-display text-title-md text-text-primary">Sources</h2>
        <p className="mt-1 text-body-sm text-text-subtle">
          {vuln.cve_id
            ? "No sources resolved for this finding yet. Re-pull live intel to fetch them."
            : "This finding has no CVE, so there is no public record to link to. Sources appear once a CVE is set."}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-title-md text-text-primary">Sources</h2>
        <p className="text-caption text-text-subtle">
          Every claim on this page, and where to check it.
        </p>
      </div>

      {kevDetail ? <KevFacts vuln={vuln} /> : null}

      <div className="space-y-4">
        {GROUPS.map((group) => {
          const items = refs.filter((r) => r.backs === group.backs);
          if (items.length === 0) return null;
          return (
            <div key={group.backs}>
              <p className="type-overline text-text-subtle">{group.title}</p>
              <p className="mb-1.5 text-caption text-text-subtle">{group.blurb}</p>
              <ul className="space-y-1">
                {items.map((ref) => (
                  <ReferenceRow key={ref.url + ref.label} reference={ref} />
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** What CISA actually published about this CVE. The badge says "known
 *  exploited"; these are the specifics behind it. */
function KevFacts({ vuln }: { vuln: VulnInstanceDetail }) {
  const fmtDate = (iso: string | null) => {
    if (!iso) return null;
    try {
      return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
    } catch {
      return iso;
    }
  };
  const added = fmtDate(vuln.kev_added_at);
  const due = fmtDate(vuln.kev_due_at);

  return (
    <div className="mb-4 rounded-md border border-status-danger-border bg-status-danger-bg px-3 py-2.5">
      <p className="flex flex-wrap items-center gap-2 text-body-sm font-semibold text-status-danger-text">
        <Icon name="alert" className="size-4 shrink-0" aria-hidden />
        On CISA&rsquo;s known-exploited catalogue
        {vuln.kev_ransomware ? <Badge variant="statusFail">Used in ransomware</Badge> : null}
      </p>
      <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-caption text-status-danger-text">
        {vuln.kev_vendor || vuln.kev_product ? (
          <span>
            <dt className="inline opacity-80">Affected: </dt>
            <dd className="inline font-semibold">
              {[vuln.kev_vendor, vuln.kev_product].filter(Boolean).join(" ")}
            </dd>
          </span>
        ) : null}
        {added ? (
          <span>
            <dt className="inline opacity-80">Added: </dt>
            <dd className="inline font-semibold">{added}</dd>
          </span>
        ) : null}
        {due ? (
          <span>
            {/* CISA's own federal deadline. Shown for context only — this
                platform's SLA clock is the one the register counts. */}
            <dt className="inline opacity-80">CISA due date: </dt>
            <dd className="inline font-semibold">{due}</dd>
          </span>
        ) : null}
      </dl>
      {vuln.kev_required_action ? (
        <p className="mt-2 text-caption text-status-danger-text">
          <span className="opacity-80">Required action: </span>
          {vuln.kev_required_action}
        </p>
      ) : null}
    </div>
  );
}

function ReferenceRow({ reference }: { reference: VulnReference }) {
  return (
    <li>
      <a
        href={reference.url}
        target="_blank"
        // noreferrer as well as noopener: these are third-party sites and the
        // referrer would leak which finding was being looked at.
        rel="noopener noreferrer"
        className="group flex items-start gap-2 rounded-sm px-2 py-1.5 transition-colors hover:bg-surface-hover"
      >
        <Icon
          name="globe"
          className="mt-0.5 size-4 shrink-0 text-text-subtle group-hover:text-text-link"
          aria-hidden
        />
        <span className="min-w-0">
          <span className="flex items-center gap-1 text-body-sm text-text-link">
            <span className="truncate">{reference.label}</span>
            <Icon name="arrowr" className="size-3.5 shrink-0 -rotate-45" aria-hidden />
          </span>
          <span className="block text-caption text-text-subtle">{reference.detail}</span>
        </span>
      </a>
    </li>
  );
}
