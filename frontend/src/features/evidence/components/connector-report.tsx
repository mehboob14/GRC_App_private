import { useMemo } from "react";
import { Icon, type IconName } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { ConnectorSnapshot, SnapshotOutcome } from "./connector-snapshot";

/**
 * A file a connector filed as evidence, read as a report.
 *
 * The file is JSON so a machine can read it, and an auditor cannot. This turns it
 * into what they came for: what was looked at, what was left out and why, and what
 * the check found. The raw file stays one click away and is what is stored, so
 * nothing here is a second source.
 *
 * A file holds one check. Files filed before each check had its own held every check
 * of the run, and are still read: they show a section per check.
 */

type Outcome = SnapshotOutcome;

const PROVIDER: Record<string, string> = { github: "GitHub" };

const OUTCOME: Record<Outcome, { icon: IconName; className: string }> = {
  pass: { icon: "check", className: "text-status-success-text" },
  fail: { icon: "x", className: "text-status-danger-text" },
  error: { icon: "alert", className: "text-status-warning-text" },
  not_applicable: { icon: "info", className: "text-text-faint" },
};

type Row = ConnectorSnapshot["results"][number];

const notOffered = (row: Row) => row.reason === "plan";

/** "check.key" read as words, for a file filed before checks carried a name. */
function checkName(row: Row): string {
  if (row.name) return row.name;
  const words = row.check?.replace(/[._]/g, " ") ?? "Other";
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="rounded-md bg-surface-sunken px-3 py-2.5">
      <dt className="text-caption text-text-subtle">{label}</dt>
      <dd
        className={cn(
          "font-display text-title-md tabular text-text-primary",
          value > 0 && tone,
        )}
      >
        {value}
      </dd>
    </div>
  );
}

/** Names behind a count, folded away until asked for: there can be hundreds. */
function Names({ summary, names }: { summary: string; names: string[] }) {
  return (
    <details className="group">
      <summary className="flex cursor-pointer items-center gap-1.5 text-body-sm text-text-secondary">
        <Icon
          name="chevr"
          className="size-3.5 shrink-0 text-text-subtle transition-transform group-open:rotate-90"
          aria-hidden
        />
        {summary}
      </summary>
      <ul className="mt-1.5 columns-1 gap-6 pl-5 text-caption text-text-secondary sm:columns-2">
        {names.map((name) => (
          <li key={name} className="truncate">
            {name}
          </li>
        ))}
      </ul>
    </details>
  );
}

/** What a check found, resource by resource, with the plan limited ones folded. */
function Findings({ rows }: { rows: Row[] }) {
  const offered = rows.filter((row) => !notOffered(row));
  const limited = rows.filter(notOffered);
  return (
    <div className="space-y-2">
      {offered.length > 0 ? (
        <ul className="divide-y divide-border">
          {offered.map((row) => {
            const mark = OUTCOME[row.outcome];
            return (
              <li key={row.resource} className="flex items-start gap-2.5 py-2">
                <Icon
                  name={mark.icon}
                  className={cn("mt-0.5 size-4 shrink-0", mark.className)}
                  aria-hidden
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-body-sm font-semibold text-text-primary">
                    {row.resource}
                  </span>
                  {row.summary ? (
                    <span className="block text-caption text-text-secondary">{row.summary}</span>
                  ) : null}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
      {limited.length > 0 ? (
        <Names
          summary={`${limited.length} ${limited.length === 1 ? "repository" : "repositories"} where GitHub does not offer this on the plan`}
          names={limited.map((row) => row.resource)}
        />
      ) : null}
    </div>
  );
}

/** The outcomes of one check as short coloured counts. */
function Counts({ rows }: { rows: Row[] }) {
  const offered = rows.filter((row) => !notOffered(row));
  const limited = rows.filter(notOffered).length;
  const count = (outcome: Outcome) => offered.filter((row) => row.outcome === outcome).length;
  return (
    <span className="flex flex-wrap gap-x-3 text-caption tabular">
      {count("pass") > 0 ? (
        <span className="text-status-success-text">{count("pass")} passed</span>
      ) : null}
      {count("fail") > 0 ? (
        <span className="text-status-danger-text">{count("fail")} failed</span>
      ) : null}
      {count("error") > 0 ? (
        <span className="text-status-warning-text">{count("error")} not checked</span>
      ) : null}
      {limited > 0 ? (
        <span className="text-status-warning-text">{limited} not offered on the plan</span>
      ) : null}
      {count("not_applicable") > 0 ? (
        <span className="text-text-subtle">{count("not_applicable")} not applicable</span>
      ) : null}
    </span>
  );
}

/** One check of an older file that holds several: its name and counts, its findings inside. */
function Check({ name, rows }: { name: string; rows: Row[] }) {
  const worried = rows.some(
    (row) => !notOffered(row) && (row.outcome === "fail" || row.outcome === "error"),
  );
  return (
    <details className="group rounded-md border border-border" open={worried}>
      <summary className="flex cursor-pointer items-start gap-3 px-3 py-2.5">
        <span className="min-w-0 flex-1">
          <span className="block text-body-md font-semibold text-text-primary">{name}</span>
          <span className="mt-0.5 block">
            <Counts rows={rows} />
          </span>
        </span>
        <Icon
          name="chev"
          className="mt-1 size-4 shrink-0 text-text-subtle transition-transform group-open:rotate-180"
          aria-hidden
        />
      </summary>
      <div className="border-t border-border px-3 py-2">
        <Findings rows={rows} />
      </div>
    </details>
  );
}

export function ConnectorReport({
  snapshot,
  heightClass,
}: {
  snapshot: ConnectorSnapshot;
  heightClass?: string;
}) {
  const { connection, scope, results, check } = snapshot;
  const tally = useMemo(() => {
    const among = (outcome: Outcome) =>
      results.filter((r) => r.outcome === outcome && !notOffered(r)).length;
    return {
      pass: among("pass"),
      fail: among("fail"),
      error: among("error"),
      plan: results.filter(notOffered).length,
    };
  }, [results]);
  const checks = useMemo(() => {
    const byName = new Map<string, Row[]>();
    for (const row of results) {
      const name = checkName(row);
      byName.set(name, [...(byName.get(name) ?? []), row]);
    }
    return [...byName];
  }, [results]);
  const leftOut = useMemo(() => {
    const byReason = new Map<string, string[]>();
    for (const entry of scope.excluded) {
      const reason = entry.reason?.trim() || "No reason recorded";
      byReason.set(reason, [...(byReason.get(reason) ?? []), entry.resource]);
    }
    return [...byReason];
  }, [scope.excluded]);
  const provider = PROVIDER[connection.provider] ?? connection.provider;
  const collected = new Date(snapshot.collected_at);
  const when = Number.isNaN(collected.getTime())
    ? snapshot.collected_at
    : collected.toLocaleString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });

  return (
    <div
      className={cn(
        "space-y-5 overflow-auto rounded-lg border border-border bg-surface-primary p-5",
        heightClass,
      )}
    >
      <header>
        <p className="font-display text-title-md text-text-primary">
          {check ? check.name : `${provider} checks on ${connection.account}`}
        </p>
        <p className="text-body-sm text-text-subtle">
          {check ? `${provider} ${connection.account}. ` : ""}Collected {when}
          {snapshot.access ? `, ${snapshot.access}` : ""}.
        </p>
        {check?.description ? (
          <p className="mt-1.5 text-body-sm text-text-secondary">{check.description}</p>
        ) : null}
      </header>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Passed" value={tally.pass} tone="text-status-success-text" />
        <Tile label="Failed" value={tally.fail} tone="text-status-danger-text" />
        <Tile
          label="Not offered on the plan"
          value={tally.plan}
          tone="text-status-warning-text"
        />
        <Tile
          label="Could not check"
          value={tally.error}
          tone="text-status-warning-text"
        />
      </dl>

      <section>
        <h3 className="type-overline mb-1">What was checked</h3>
        <p className="text-body-sm text-text-secondary">
          <span className="font-semibold text-text-primary">{scope.checked}</span> of{" "}
          {scope.listed} repositories
          {scope.excluded.length > 0 ? `, ${scope.excluded.length} left out` : ""}.
        </p>
        {leftOut.length > 0 ? (
          <div className="mt-2 space-y-1.5">
            {leftOut.map(([reason, names]) => (
              <Names
                key={reason}
                summary={`${names.length} left out: ${reason}`}
                names={names}
              />
            ))}
          </div>
        ) : null}
      </section>

      {check ? (
        <section>
          <h3 className="type-overline mb-2">What it found</h3>
          <Findings rows={results} />
        </section>
      ) : (
        <section>
          <h3 className="type-overline mb-2">What each check found</h3>
          <div className="space-y-2">
            {checks.map(([name, rows]) => (
              <Check key={name} name={name} rows={rows} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
