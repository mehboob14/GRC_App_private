import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { countryName } from "@/lib/countries";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";

/**
 * Laws that may apply (guided onboarding part 4, JC-1 to JC-9). Matched from the company profile
 * against a reviewed reference list: chips by country, a matrix by topic, a card per law with
 * its duties, dates, the controls you already run that help, and your own call on it.
 */

type Duty = { topic: string; text: string; clock_hours: number | null };
type Milestone = { date: string | null; precision: string; kind: string; description: string; confirmed: boolean };
type Source = { url: string; publisher: string; kind: string; verified: string };

type Regulation = {
  key: string;
  jurisdiction: string;
  short_name: string;
  official_name: string;
  regulator: string | null;
  topic_column: string;
  state: string;
  state_note: string | null;
  tier: string;
  applies_to: string;
  duties: Duty[];
  assurance: { kind?: string; note?: string };
  iso27001: { relation?: string; note?: string };
  soc2: { relation?: string; note?: string };
  helps: string[];
  not_covered: string[];
  milestones: Milestone[];
  sources: Source[];
  review_status: string;
  review_overdue: boolean;
  confidence: "applies" | "likely_applies" | "check";
  because: string[];
  relevance: "relevant" | "not_relevant" | null;
  note: string | null;
  decided_by_name: string | null;
  in_register_since: string | null;
};

type Panel = { regulations: Regulation[]; hidden_drafts: number; uncovered: string[]; disclaimer: string };

const CONFIDENCE: Record<Regulation["confidence"], { family: StatusFamily; label: string }> = {
  applies: { family: "warning", label: "Applies to you" },
  likely_applies: { family: "pending", label: "Likely applies" },
  check: { family: "neutral", label: "Check whether it applies" },
};

const TOPICS: { key: string; label: string }[] = [
  { key: "privacy", label: "Privacy" },
  { key: "security_baseline", label: "Security baseline" },
  { key: "breach_clock", label: "Breach reporting" },
  { key: "data_location", label: "Data location" },
  { key: "sector", label: "Sector rules" },
  { key: "ai", label: "AI" },
];

const RELATION: Record<string, string> = {
  referenced_or_accepted: "Named or accepted",
  helps_partially: "Helps, not enough alone",
  not_relevant: "Not relevant",
  not_a_substitute: "No substitute",
};

const place = (code: string) => (code === "GLOBAL" ? "Global" : code === "EU" ? "European Union" : countryName(code));

export function RegulationsPage() {
  const { principal } = useAuth();
  const canDecide = hasPermission(principal, "tenant:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["regulations", principal?.tenant_id],
    queryFn: () => apiFetch<Panel>("/regulations"),
  });
  const [where, setWhere] = useState<string | null>(null);
  const [open, setOpen] = useState<Regulation | null>(null);
  const [declining, setDeclining] = useState(false);
  const [note, setNote] = useState("");
  const decide = useMutation({
    mutationFn: (a: { key: string; relevance: "relevant" | "not_relevant"; note?: string }) =>
      apiFetch<void>(`/regulations/${a.key}`, {
        method: "PUT",
        body: JSON.stringify({ relevance: a.relevance, note: a.note ?? null }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["regulations"] });
      setDeclining(false);
      setOpen(null);
      toast({ title: "Saved", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "decision"), tone: "danger" }),
  });

  const [register, setRegister] = useState(false);
  const all = useMemo(() => query.data?.regulations ?? [], [query.data]);
  const places = useMemo(() => [...new Set(all.map((r) => r.jurisdiction))], [all]);
  const obligations = all.filter((r) => r.in_register_since);
  const shown = (register ? obligations : all).filter((r) => !where || r.jurisdiction === where);

  if (query.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "laws");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  const data = query.data;

  return (
    <div className="mx-auto w-full max-w-[1100px]">
      <PageHeader title="Laws that may apply" />
      <p className="mt-2 rounded-md bg-surface-sunken px-4 py-2.5 text-body-sm text-text-secondary">
        {data.disclaimer}{" "}
        <Link to="/settings/organization/profile" className="text-text-link">
          Change your answers
        </Link>
      </p>
      {data.hidden_drafts ? (
        <p className="mt-2 text-body-sm text-text-secondary">
          {data.hidden_drafts} more are waiting for legal review and are not shown yet.
        </p>
      ) : null}
      {data.uncovered.length ? (
        <p className="mt-2 text-body-sm text-text-secondary">
          Not covered yet: {data.uncovered.map(place).join(", ")}. Ask a local adviser.
        </p>
      ) : null}

      {all.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="Nothing to show yet"
            description="Add your countries and customers to the company profile to see what may apply."
          />
        </div>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Countries">
            <Chip
              active={register}
              onClick={() => setRegister(!register)}
              label={`Your obligations ${obligations.length}`}
            />
            <Chip active={where === null} onClick={() => setWhere(null)} label={`All ${all.length}`} />
            {places.map((p) => (
              <Chip key={p} active={where === p} onClick={() => setWhere(p)} label={place(p)} />
            ))}
          </div>

          <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-surface-primary">
            <table className="w-full min-w-[760px] text-left text-body-sm">
              <thead className="border-b border-border text-caption text-text-subtle">
                <tr>
                  <th className="px-4 py-2.5 font-normal">Where</th>
                  {TOPICS.map((t) => (
                    <th key={t.key} className="px-4 py-2.5 font-normal">
                      {t.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(where ? [where] : places).map((p) => (
                  <tr key={p} className="border-b border-border align-top last:border-b-0">
                    <td className="px-4 py-3 font-semibold text-text-primary">{place(p)}</td>
                    {TOPICS.map((t) => (
                      <td key={t.key} className="px-4 py-3">
                        <span className="flex flex-col items-start gap-1">
                          {all
                            .filter((r) => r.jurisdiction === p && r.topic_column === t.key)
                            .map((r) => (
                              <button
                                key={r.key}
                                type="button"
                                onClick={() => setOpen(r)}
                                className="text-left text-text-link hover:underline"
                              >
                                {r.short_name}
                              </button>
                            ))}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {shown.map((r) => (
              <button
                key={r.key}
                type="button"
                onClick={() => setOpen(r)}
                className="rounded-lg border border-border bg-surface-primary p-4 text-left hover:border-action-primary"
              >
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-text-primary">{r.short_name}</span>
                  <StatusPill status={CONFIDENCE[r.confidence].family} label={CONFIDENCE[r.confidence].label} />
                  {r.relevance ? (
                    <StatusPill
                      status={r.relevance === "relevant" ? "success" : "neutral"}
                      label={r.relevance === "relevant" ? "Relevant to us" : "Not relevant"}
                    />
                  ) : null}
                </span>
                <span className="mt-1 block text-body-sm text-text-secondary">
                  {place(r.jurisdiction)}. {r.applies_to}
                </span>
                <span className="mt-2 block text-caption text-text-subtle">From: {r.because.join(", ")}</span>
              </button>
            ))}
          </div>
        </>
      )}

      <Drawer open={open !== null} onOpenChange={(v) => (v ? null : setOpen(null))}>
        <DrawerContent size="lg" className="text-body-sm">
          {open ? (
            <>
              <DrawerHeader>
                <DrawerTitle>{open.short_name}</DrawerTitle>
              </DrawerHeader>
              <DrawerBody className="space-y-4">
                <p className="text-text-secondary">{open.official_name}</p>
                <div className="flex flex-wrap gap-2">
                  <StatusPill status={CONFIDENCE[open.confidence].family} label={CONFIDENCE[open.confidence].label} />
                  {open.review_status !== "reviewed" ? <StatusPill status="pending" label="Not yet legally reviewed" /> : null}
                  {open.review_overdue ? <StatusPill status="warning" label="Review overdue" /> : null}
                </div>
                {open.state_note ? <p className="text-text-secondary">{open.state_note}</p> : null}
                <Section title="What it asks">
                  <ul className="space-y-1.5">
                    {open.duties.map((d) => (
                      <li key={d.text} className="text-text-primary">
                        {d.clock_hours ? <strong>{d.clock_hours} hours. </strong> : null}
                        {d.text}
                      </li>
                    ))}
                  </ul>
                </Section>
                {open.milestones.length ? (
                  <Section title="Dates">
                    <ol className="flex flex-wrap gap-2">
                      {open.milestones.map((m) => (
                        <li key={`${m.date}${m.description}`} className="rounded-md bg-surface-sunken px-2.5 py-1.5">
                          <span className="block font-semibold tabular text-text-primary">
                            {m.date ?? "Date not set"}
                            {m.confirmed ? "" : " (expected)"}
                          </span>
                          <span className="text-caption text-text-secondary">{m.description}</span>
                        </li>
                      ))}
                    </ol>
                  </Section>
                ) : null}
                <Section title="Your frameworks">
                  <p className="text-text-primary">
                    ISO 27001: {RELATION[open.iso27001.relation ?? ""] ?? "Not stated"}. SOC 2:{" "}
                    {RELATION[open.soc2.relation ?? ""] ?? "Not stated"}.
                  </p>
                  {open.helps.length ? (
                    <p className="mt-2 text-text-secondary">
                      Controls you run that help:{" "}
                      {open.helps.map((c) => (
                        <span key={c} className="mr-1 rounded-sm bg-surface-sunken px-1.5 py-px font-mono text-caption">
                          {c}
                        </span>
                      ))}
                    </p>
                  ) : null}
                  {open.not_covered.length ? (
                    <p className="mt-2 text-text-secondary">Not covered by your controls: {open.not_covered.join(", ")}.</p>
                  ) : null}
                </Section>
                <Section title="Sources">
                  <ul className="space-y-1">
                    {open.sources.map((s) => (
                      <li key={s.url}>
                        <a href={s.url} target="_blank" rel="noreferrer noopener" className="text-text-link">
                          {s.publisher}
                        </a>
                      </li>
                    ))}
                  </ul>
                </Section>
                {open.note ? (
                  <p className="text-text-secondary">
                    Your note{open.decided_by_name ? ` (${open.decided_by_name})` : ""}: {open.note}
                  </p>
                ) : null}
                {canDecide ? (
                  <div className="flex gap-2 border-t border-border pt-4">
                    <Button loading={decide.isPending} onClick={() => decide.mutate({ key: open.key, relevance: "relevant" })}>
                      Relevant to us
                    </Button>
                    <Button variant="secondary" onClick={() => { setNote(""); setDeclining(true); }}>
                      Not relevant
                    </Button>
                  </div>
                ) : null}
              </DrawerBody>
            </>
          ) : null}
        </DrawerContent>
      </Drawer>

      <Dialog open={declining} onOpenChange={setDeclining}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Why does this not apply?</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <TextArea label="Reason" rows={4} value={note} onChange={(e) => setNote(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDeclining(false)}>
              Cancel
            </Button>
            <Button
              disabled={!note.trim()}
              loading={decide.isPending}
              onClick={() => open && decide.mutate({ key: open.key, relevance: "not_relevant", note })}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Chip({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-caption ${
        active ? "bg-action-primary text-action-primary-fg" : "bg-surface-sunken text-text-primary"
      }`}
    >
      {label}
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-caption text-text-subtle">{title}</h3>
      {children}
    </section>
  );
}
