import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, useToast } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { getSummary, updateRegister } from "../api";
import { METHOD_META, scoreOf, type Appetite, type ScoringFormula, type ScoringMethod } from "../scoring";
import type { Register } from "../types";

/** A save that touches one setting and leaves the rest of the register as it was. */
function useRegisterSave(register: Register, what: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (extra: { scoring_formula?: ScoringFormula; appetite?: Appetite }) =>
      updateRegister(register.id, {
        name: register.name,
        register_type: register.register_type,
        description: register.description,
        owner_membership_id: register.owner_membership_id,
        ...extra,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      void queryClient.invalidateQueries({ queryKey: ["risk"] });
      toast({ title: `${what} saved`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "register"), tone: "danger" }),
  });
}

const input =
  "tabular h-8 w-16 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary focus:border-action-accent focus:outline-none disabled:bg-surface-sunken";

/** Product, additive or weighted. Saving rescores the register's risks and resets its bands. */
export function ScoringFormulaCard({ register, canEdit }: { register: Register; canEdit: boolean }) {
  const [formula, setFormula] = useState<ScoringFormula>(register.scoring_formula);
  useEffect(() => setFormula(register.scoring_formula), [register.id, register.scoring_formula]);
  const save = useRegisterSave(register, "Scoring formula");
  const weighted = formula.method === "weighted";
  const lw = formula.likelihood_weight ?? 1;
  const iw = formula.impact_weight ?? 1;
  const top = scoreOf(formula, register.likelihood_levels, register.impact_levels);
  const current = register.scoring_formula;
  const dirty =
    formula.method !== current.method ||
    (weighted && (lw !== (current.likelihood_weight ?? 1) || iw !== (current.impact_weight ?? 1)));
  const pick = (method: ScoringMethod) =>
    setFormula(method === "weighted" ? { method, likelihood_weight: lw, impact_weight: iw } : { method });

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="font-display text-title-sm text-text-primary">Scoring formula</h2>
      <p className="mt-1 text-body-sm text-text-secondary">How {register.name} turns likelihood and impact into a score.</p>
      <div className="mt-4 grid gap-2 md:grid-cols-3">
        {(Object.keys(METHOD_META) as ScoringMethod[]).map((m) => (
          <button
            key={m}
            type="button"
            disabled={!canEdit}
            onClick={() => pick(m)}
            aria-pressed={formula.method === m}
            className={cn(
              "rounded-md border p-3 text-left transition-colors",
              formula.method === m
                ? "border-action-accent bg-action-accent-tint"
                : "border-border hover:bg-surface-hover disabled:hover:bg-transparent",
            )}
          >
            <span className="block text-label-md text-text-primary">{METHOD_META[m].label}</span>
            <span className="mt-0.5 block text-caption text-text-subtle">{METHOD_META[m].text}</span>
          </button>
        ))}
      </div>
      {weighted ? (
        <div className="mt-4 flex flex-wrap items-center gap-3 text-body-sm text-text-secondary">
          <label className="flex items-center gap-2">
            Likelihood weight
            <input
              type="number"
              min={1}
              max={10}
              value={lw}
              disabled={!canEdit}
              onChange={(e) => setFormula({ ...formula, likelihood_weight: Number(e.target.value) || 1 })}
              className={input}
            />
          </label>
          <label className="flex items-center gap-2">
            Impact weight
            <input
              type="number"
              min={1}
              max={10}
              value={iw}
              disabled={!canEdit}
              onChange={(e) => setFormula({ ...formula, impact_weight: Number(e.target.value) || 1 })}
              className={input}
            />
          </label>
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-caption text-text-subtle">
          Top score on this matrix: <span className="tabular font-semibold text-text-primary">{top}</span>.
          {dirty ? " Saving rescores every risk here and resets the severity bands." : ""}
        </p>
        {canEdit ? (
          <Button disabled={!dirty} loading={save.isPending} onClick={() => save.mutate({ scoring_formula: formula })}>
            Save formula
          </Button>
        ) : null}
      </div>
    </section>
  );
}

type Row = { appetite: string; tolerance: string };

/** Appetite and tolerance per top level category, in this register's score units. */
export function AppetiteCard({ register, canEdit }: { register: Register; canEdit: boolean }) {
  const categories = register.categories.filter((c) => !c.archived);
  const toRows = (): Record<string, Row> =>
    Object.fromEntries(
      categories.map((c) => {
        const a = register.appetite[c.id];
        return [c.id, { appetite: a ? String(a.appetite) : "", tolerance: a ? String(a.tolerance) : "" }];
      }),
    );
  const [rows, setRows] = useState<Record<string, Row>>(toRows);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setRows(toRows()), [register.id, register.appetite, register.categories]);
  const save = useRegisterSave(register, "Risk appetite");
  const summary = useQuery({ queryKey: ["risk-summary", register.id], queryFn: () => getSummary(register.id) });
  const top = register.max_score;

  const parsed = categories.map((c) => {
    const { appetite, tolerance } = rows[c.id] ?? { appetite: "", tolerance: "" };
    if (appetite === "" && tolerance === "") return { id: c.id, empty: true, ok: true } as const;
    const a = Number(appetite);
    const t = Number(tolerance);
    const ok = Number.isInteger(a) && Number.isInteger(t) && a >= 1 && a <= t && t <= top;
    return { id: c.id, empty: false, ok, a, t } as const;
  });
  const valid = parsed.every((p) => p.ok);
  const body: Appetite = {};
  for (const p of parsed) if (!p.empty && p.ok) body[p.id] = { appetite: p.a, tolerance: p.t };
  const dirty = JSON.stringify(body) !== JSON.stringify(register.appetite);
  const set = (id: string, patch: Partial<Row>) => setRows((r) => ({ ...r, [id]: { ...r[id], ...patch } }));
  const counts = summary.data?.by_appetite ?? {};

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-title-sm text-text-primary">Risk appetite</h2>
          <p className="mt-1 text-body-sm text-text-secondary">
            Scores up to appetite are fine. Up to tolerance is carried with care. Above tolerance is a breach. Scores here run 1 to {top}.
          </p>
        </div>
        {(counts.tolerated ?? 0) + (counts.breach ?? 0) > 0 ? (
          <p className="text-caption text-text-subtle">
            {counts.breach ?? 0} beyond tolerance, {counts.tolerated ?? 0} above appetite
          </p>
        ) : null}
      </div>
      <div className="mt-4 divide-y divide-border rounded-md border border-border">
        <div className="grid grid-cols-[minmax(0,1fr)_5rem_5rem] items-center gap-3 px-3 py-2 text-caption text-text-subtle">
          <span>Category</span>
          <span>Appetite</span>
          <span>Tolerance</span>
        </div>
        {categories.map((c, i) => (
          <div key={c.id} className="grid grid-cols-[minmax(0,1fr)_5rem_5rem] items-center gap-3 px-3 py-2">
            <span className="truncate text-body-sm text-text-primary">{c.name}</span>
            {(["appetite", "tolerance"] as const).map((k) => (
              <input
                key={k}
                type="number"
                min={1}
                max={top}
                value={rows[c.id]?.[k] ?? ""}
                disabled={!canEdit}
                onChange={(e) => set(c.id, { [k]: e.target.value })}
                aria-label={`${c.name} ${k}`}
                className={cn(input, "w-full", !parsed[i].ok && "border-status-danger-border")}
              />
            ))}
          </div>
        ))}
      </div>
      {!valid ? (
        <p className="mt-2 text-caption text-status-danger-text">
          Appetite must be at least 1 and no higher than tolerance, and tolerance no higher than {top}.
        </p>
      ) : null}
      {canEdit ? (
        <div className="mt-4 flex justify-end">
          <Button disabled={!dirty || !valid} loading={save.isPending} onClick={() => save.mutate({ appetite: body })}>
            Save appetite
          </Button>
        </div>
      ) : null}
    </section>
  );
}
