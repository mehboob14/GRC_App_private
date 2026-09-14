import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  PersonSelect,
  SegmentedControl,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Switch,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { createRegister, getOptions, saveCategories, updateRegister } from "../api";
import type { Band, BandKey, Register, RegisterInput, RegisterType, ScaleLevel } from "../types";
import { REGISTER_TYPES } from "../types";
import { BAND_TONE, REGISTER_TYPE_LABEL } from "../tokens";
import { BandLegend, Heatmap } from "./heatmap";
import { useRisksOutlet } from "./risks-outlet";
import { SoonBadge } from "./soon";

const LEVELS = [3, 4, 5, 6] as const;

/** Registers and how each one scores, classifies and reviews. */
export function RisksSettingsPage() {
  const { register, registers, selectRegister, canConfigure } = useRisksOutlet();
  const [editing, setEditing] = useState<Register | "new" | null>(null);
  const [taxonomy, setTaxonomy] = useState<Register | null>(null);

  return (
    <div className="space-y-5">
      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-title-md text-text-primary">Registers</h2>
            <p className="text-body-sm text-text-subtle">Each register keeps its own matrix, bands and categories.</p>
          </div>
          {canConfigure ? (
            <Button onClick={() => setEditing("new")}>
              <Icon name="plus" className="size-4" />
              New register
            </Button>
          ) : null}
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {registers.map((r) => (
            <article
              key={r.id}
              className={cn(
                "rounded-lg border bg-surface-primary p-4",
                r.id === register.id ? "border-action-accent ring-1 ring-action-accent" : "border-border",
              )}
            >
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
                  <Icon name="layers" className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-body-md font-semibold text-text-primary">
                    {r.name}
                    {r.is_default ? <Badge variant="role">Default</Badge> : null}
                    {r.status === "archived" ? <Badge variant="neutral">Archived</Badge> : null}
                  </p>
                  <p className="mt-0.5 text-caption text-text-subtle">
                    {REGISTER_TYPE_LABEL[r.register_type]} · {r.risk_count} risks · {r.likelihood_levels} by {r.impact_levels} ·
                    review every {r.review_cadence_days} days
                  </p>
                  {r.description ? <p className="mt-1.5 line-clamp-2 text-body-sm text-text-secondary">{r.description}</p> : null}
                </div>
                <div className="hidden shrink-0 sm:block">
                  <MiniMatrix register={r} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
                {r.id !== register.id && r.status === "active" ? (
                  <Button size="sm" variant="secondary" onClick={() => selectRegister(r.id)}>
                    Open
                  </Button>
                ) : (
                  <span className="text-caption font-semibold text-action-accent">Current</span>
                )}
                {canConfigure ? (
                  <>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(r)}>
                      <Icon name="heatmap" className="size-4" />
                      Matrix and settings
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setTaxonomy(r)}>
                      <Icon name="list" className="size-4" />
                      Categories
                    </Button>
                  </>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-display text-title-md text-text-primary">More configuration</h2>
        <div className="divide-y divide-border rounded-lg border border-border bg-surface-primary">
          {[
            { icon: "textbox" as const, title: "Custom fields", text: "Extra fields per register on the form, filters and import." },
            { icon: "formula" as const, title: "Scoring formula", text: "Weighted or additive scoring instead of likelihood times impact." },
            { icon: "target" as const, title: "Risk appetite", text: "Appetite and tolerance thresholds per category." },
            { icon: "workflow" as const, title: "Approval workflows", text: "Multi step sign off for acceptance and closure." },
            { icon: "lock" as const, title: "Register permissions", text: "Who can read or manage each register." },
          ].map((row) => (
            <div key={row.title} className="flex items-center gap-3 px-4 py-3">
              <span className="grid size-8 place-items-center rounded-md bg-surface-sunken text-text-subtle">
                <Icon name={row.icon} className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-label-md text-text-primary">{row.title}</p>
                <p className="truncate text-caption text-text-subtle">{row.text}</p>
              </div>
              <SoonBadge />
            </div>
          ))}
        </div>
      </section>

      <RegisterDialog
        open={editing !== null}
        onOpenChange={(o) => !o && setEditing(null)}
        register={editing === "new" ? null : editing}
        onCreated={(r) => selectRegister(r.id)}
      />
      <TaxonomyDialog open={taxonomy !== null} onOpenChange={(o) => !o && setTaxonomy(null)} register={taxonomy} />
    </div>
  );
}

function MiniMatrix({ register }: { register: Register }) {
  const rows = Array.from({ length: register.likelihood_levels }, (_, i) => register.likelihood_levels - i);
  return (
    <div
      className="grid gap-0.5"
      style={{ gridTemplateColumns: `repeat(${register.impact_levels}, 0.6rem)` }}
      aria-hidden
    >
      {rows.flatMap((l) =>
        Array.from({ length: register.impact_levels }, (_, i) => {
          const score = l * (i + 1);
          const band = [...register.severity_bands].reverse().find((b) => b.min_score <= score);
          return <span key={`${l}-${i}`} className={cn("size-2.5 rounded-[2px]", band ? BAND_TONE[band.key].dot : "bg-surface-sunken")} />;
        }),
      )}
    </div>
  );
}

// -- register and matrix ------------------------------------------------------------------

function defaultScale(kind: "likelihood" | "impact", levels: number, current: ScaleLevel[]): ScaleLevel[] {
  const names: Record<number, string[]> = {
    3: kind === "likelihood" ? ["Unlikely", "Possible", "Likely"] : ["Minor", "Moderate", "Major"],
    4: kind === "likelihood" ? ["Unlikely", "Possible", "Likely", "Almost certain"] : ["Minor", "Moderate", "Major", "Severe"],
    5:
      kind === "likelihood"
        ? ["Rare", "Unlikely", "Possible", "Likely", "Almost certain"]
        : ["Negligible", "Minor", "Moderate", "Major", "Severe"],
    6:
      kind === "likelihood"
        ? ["Rare", "Very unlikely", "Unlikely", "Possible", "Likely", "Almost certain"]
        : ["Negligible", "Minor", "Moderate", "Significant", "Major", "Severe"],
  };
  if (current.length === levels) return current;
  return names[levels].map((label, i) => ({ level: i + 1, label, description: "" }));
}

function defaultBands(max: number, current?: Band[]): Band[] {
  if (current && current.length === 4 && current[3].min_score <= max) return current;
  const mins = [1, ...[0.2, 0.4, 0.6].map((f) => Math.max(2, Math.ceil(max * f)))];
  for (let i = 1; i < mins.length; i++) mins[i] = Math.max(mins[i], mins[i - 1] + 1);
  const keys: BandKey[] = ["low", "medium", "high", "critical"];
  const labels = ["Low", "Medium", "High", "Critical"];
  return keys.map((key, i) => ({ key, label: current?.[i]?.label ?? labels[i], min_score: mins[i] }));
}

type RegisterForm = {
  name: string;
  register_type: RegisterType;
  description: string;
  owner_membership_id: string | null;
  likelihood_levels: number;
  impact_levels: number;
  likelihood_scale: ScaleLevel[];
  impact_scale: ScaleLevel[];
  severity_bands: Band[];
  review_cadence_days: number;
  is_default: boolean;
  archived: boolean;
};

function RegisterDialog({
  open,
  onOpenChange,
  register,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  register: Register | null;
  onCreated: (register: Register) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState<RegisterForm | null>(null);
  const [axis, setAxis] = useState<"likelihood" | "impact">("likelihood");
  const optionsQuery = useQuery({ queryKey: ["risk-options"], queryFn: getOptions, staleTime: 60_000, enabled: open });
  const people = (optionsQuery.data?.members ?? []).map((m) => ({ id: m.membership_id, name: m.name }));

  useEffect(() => {
    if (!open) return;
    const likelihood = register?.likelihood_levels ?? 5;
    const impact = register?.impact_levels ?? 5;
    setForm({
      name: register?.name ?? "",
      register_type: register?.register_type ?? "enterprise",
      description: register?.description ?? "",
      owner_membership_id: register?.owner_membership_id ?? null,
      likelihood_levels: likelihood,
      impact_levels: impact,
      likelihood_scale: register?.likelihood_scale ?? defaultScale("likelihood", 5, []),
      impact_scale: register?.impact_scale ?? defaultScale("impact", 5, []),
      severity_bands: register?.severity_bands ?? defaultBands(25),
      review_cadence_days: register?.review_cadence_days ?? 90,
      is_default: register?.is_default ?? false,
      archived: register?.status === "archived",
    });
    setAxis("likelihood");
  }, [open, register]);

  const save = useMutation({
    mutationFn: async () => {
      const f = form!;
      const body: RegisterInput = {
        name: f.name.trim(),
        register_type: f.register_type,
        description: f.description.trim() || null,
        owner_membership_id: f.owner_membership_id,
        likelihood_levels: f.likelihood_levels,
        impact_levels: f.impact_levels,
        likelihood_scale: f.likelihood_scale.map((s) => ({ label: s.label, description: s.description })),
        impact_scale: f.impact_scale.map((s) => ({ label: s.label, description: s.description })),
        severity_bands: f.severity_bands,
        review_cadence_days: f.review_cadence_days,
        is_default: f.is_default,
        status: f.archived ? "archived" : "active",
      };
      return register ? updateRegister(register.id, body) : createRegister(body);
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      toast({ title: register ? "Register saved" : "Register created", tone: "success" });
      if (!register) onCreated(saved);
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "register"), tone: "danger" }),
  });

  if (!form) return null;
  const max = form.likelihood_levels * form.impact_levels;
  const set = <K extends keyof RegisterForm>(key: K, value: RegisterForm[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));
  const resize = (kind: "likelihood" | "impact", levels: number) =>
    setForm((f) => {
      if (!f) return f;
      const next = { ...f, [`${kind}_levels`]: levels, [`${kind}_scale`]: defaultScale(kind, levels, []) } as RegisterForm;
      next.severity_bands = defaultBands(next.likelihood_levels * next.impact_levels, f.severity_bands);
      return next;
    });
  const scale = axis === "likelihood" ? form.likelihood_scale : form.impact_scale;
  const setScale = (index: number, patch: Partial<ScaleLevel>) =>
    set(
      axis === "likelihood" ? "likelihood_scale" : "impact_scale",
      scale.map((s, i) => (i === index ? { ...s, ...patch } : s)),
    );
  const bandsValid = form.severity_bands.every(
    (b, i) => b.min_score >= 1 && b.min_score <= max && (i === 0 || b.min_score > form.severity_bands[i - 1].min_score),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[94vh] w-[min(1000px,calc(100vw-2rem))] p-0">
        <DialogHeader className="border-b border-border px-6 pb-4 pt-5">
          <DialogTitle>{register ? register.name : "New register"}</DialogTitle>
          <DialogDescription>Type, owner, scoring matrix and review cadence.</DialogDescription>
        </DialogHeader>
        <DialogBody className="mx-0 px-6 py-5">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="space-y-4">
              <div className="grid gap-3.5 sm:grid-cols-2">
                <TextField label="Name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="ISO 27001 risks" autoFocus />
                <SelectField label="Register type">
                  <Select value={form.register_type} onValueChange={(v) => set("register_type", v as RegisterType)}>
                    <SelectTrigger aria-label="Register type" />
                    <SelectContent>
                      {REGISTER_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {REGISTER_TYPE_LABEL[t]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
              </div>
              <TextArea label="Description" optional rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
              <div className="grid gap-3.5 sm:grid-cols-2">
                <div>
                  <p className="mb-1.5 text-label-sm text-text-secondary">Owner</p>
                  <PersonSelect people={people} value={form.owner_membership_id} onChange={(v) => set("owner_membership_id", v)} placeholder="Select owner" clearLabel="No owner" aria-label="Owner" />
                </div>
                <TextField
                  label="Review every (days)"
                  type="number"
                  min={7}
                  max={730}
                  value={String(form.review_cadence_days)}
                  onChange={(e) => set("review_cadence_days", Math.max(7, Math.min(730, Number(e.target.value) || 90)))}
                />
              </div>

              <div className="rounded-lg border border-border p-4">
                <p className="mb-3 text-label-md text-text-primary">Matrix size</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {(["likelihood", "impact"] as const).map((kind) => (
                    <div key={kind}>
                      <p className="mb-1.5 text-label-sm text-text-secondary">{kind === "likelihood" ? "Likelihood levels" : "Impact levels"}</p>
                      <SegmentedControl
                        label={`${kind} levels`}
                        value={String(form[`${kind}_levels`])}
                        onChange={(v) => resize(kind, Number(v))}
                        items={LEVELS.map((n) => ({ id: String(n), label: String(n) }))}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-border p-4">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <p className="text-label-md text-text-primary">Level labels</p>
                  <SegmentedControl
                    label="Axis"
                    value={axis}
                    onChange={setAxis}
                    items={[
                      { id: "likelihood", label: "Likelihood" },
                      { id: "impact", label: "Impact" },
                    ]}
                  />
                </div>
                <div className="space-y-2">
                  {scale.map((s, i) => (
                    <div key={s.level} className="grid grid-cols-[2rem_10rem_minmax(0,1fr)] items-center gap-2">
                      <span className="tabular grid size-8 place-items-center rounded-md bg-surface-sunken text-label-sm text-text-secondary">
                        {s.level}
                      </span>
                      <input
                        value={s.label}
                        onChange={(e) => setScale(i, { label: e.target.value })}
                        aria-label={`Level ${s.level} label`}
                        className="h-8 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary focus:border-action-accent focus:outline-none"
                      />
                      <input
                        value={s.description}
                        onChange={(e) => setScale(i, { description: e.target.value })}
                        placeholder="What this level means"
                        aria-label={`Level ${s.level} meaning`}
                        className="h-8 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary placeholder:text-text-faint focus:border-action-accent focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-lg border border-border p-4">
                <p className="mb-3 text-label-md text-text-primary">Severity bands</p>
                <div className="space-y-2">
                  {form.severity_bands.map((b, i) => (
                    <div key={b.key} className="grid grid-cols-[0.75rem_minmax(0,1fr)_5.5rem] items-center gap-2">
                      <span className={cn("h-7 w-3 rounded-sm", BAND_TONE[b.key].dot)} />
                      <input
                        value={b.label}
                        onChange={(e) =>
                          set("severity_bands", form.severity_bands.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))
                        }
                        aria-label={`${b.key} label`}
                        className="h-8 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary focus:border-action-accent focus:outline-none"
                      />
                      <label className="flex items-center gap-1.5 text-caption text-text-subtle">
                        from
                        <input
                          type="number"
                          min={1}
                          max={max}
                          disabled={i === 0}
                          value={b.min_score}
                          onChange={(e) =>
                            set(
                              "severity_bands",
                              form.severity_bands.map((x, j) => (j === i ? { ...x, min_score: Number(e.target.value) || 1 } : x)),
                            )
                          }
                          aria-label={`${b.label} starts at`}
                          className="tabular h-8 w-12 rounded-sm border border-border bg-surface-primary px-1.5 text-body-sm text-text-primary disabled:bg-surface-sunken focus:border-action-accent focus:outline-none"
                        />
                      </label>
                    </div>
                  ))}
                </div>
                {!bandsValid ? (
                  <p className="mt-2 text-caption text-status-danger-text">Thresholds must rise and stay within {max}.</p>
                ) : null}
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="mb-3 text-label-md text-text-primary">Preview</p>
                <Heatmap
                  compact
                  likelihoodScale={form.likelihood_scale}
                  impactScale={form.impact_scale}
                  bands={form.severity_bands}
                />
                <div className="mt-3">
                  <BandLegend bands={form.severity_bands} />
                </div>
              </div>
              <div className="space-y-3 rounded-lg border border-border p-4">
                <label className="flex items-center justify-between gap-3">
                  <span className="text-label-sm text-text-secondary">Default register</span>
                  <Switch checked={form.is_default} onCheckedChange={(v) => set("is_default", v)} aria-label="Default register" />
                </label>
                {register && !register.is_default ? (
                  <label className="flex items-center justify-between gap-3">
                    <span className="text-label-sm text-text-secondary">Archived</span>
                    <Switch checked={form.archived} onCheckedChange={(v) => set("archived", v)} aria-label="Archived" />
                  </label>
                ) : null}
              </div>
            </div>
          </div>
        </DialogBody>
        <DialogFooter className="mt-0 border-t border-border px-6 py-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!form.name.trim() || !bandsValid} loading={save.isPending} onClick={() => save.mutate()}>
            {register ? "Save register" : "Create register"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -- taxonomy ------------------------------------------------------------------------------------

type EditableSub = { key: string; id?: string; name: string; used: number };
type EditableCategory = { key: string; id?: string; name: string; used: number; children: EditableSub[] };

function TaxonomyDialog({
  open,
  onOpenChange,
  register,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  register: Register | null;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [tree, setTree] = useState<EditableCategory[]>([]);
  const [selected, setSelected] = useState(0);
  const [draftCategory, setDraftCategory] = useState("");
  const [draftSub, setDraftSub] = useState("");

  useEffect(() => {
    if (!open || !register) return;
    setTree(
      register.categories
        .filter((c) => !c.archived)
        .map((c) => ({
          key: c.id,
          id: c.id,
          name: c.name,
          used: c.risk_count,
          children: c.children.filter((s) => !s.archived).map((s) => ({ key: s.id, id: s.id, name: s.name, used: s.risk_count })),
        })),
    );
    setSelected(0);
    setDraftCategory("");
    setDraftSub("");
  }, [open, register]);

  const save = useMutation({
    mutationFn: () =>
      saveCategories(
        register!.id,
        tree.map((c) => ({ id: c.id, name: c.name.trim(), children: c.children.map((s) => ({ id: s.id, name: s.name.trim() })) })),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      toast({ title: "Categories saved", tone: "success" });
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "categories"), tone: "danger" }),
  });

  if (!register) return null;
  const current = tree[selected];
  const uid = () => `new_${Math.random().toString(36).slice(2, 9)}`;
  const move = (index: number, by: number) =>
    setTree((t) => {
      const next = [...t];
      const [row] = next.splice(index, 1);
      next.splice(Math.max(0, Math.min(next.length, index + by)), 0, row);
      setSelected(Math.max(0, Math.min(next.length - 1, index + by)));
      return next;
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[90vh] w-[min(880px,calc(100vw-2rem))]">
        <DialogHeader>
          <DialogTitle>Categories</DialogTitle>
          <DialogDescription>
            {register.name}. Categories still used by risks are archived instead of deleted.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="grid min-h-[22rem] gap-4 md:grid-cols-[18rem_minmax(0,1fr)]">
            <div className="flex flex-col rounded-lg border border-border">
              <ul className="flex-1 space-y-0.5 overflow-y-auto p-1.5">
                {tree.map((c, i) => (
                  <li key={c.key}>
                    <button
                      type="button"
                      onClick={() => setSelected(i)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left",
                        i === selected ? "bg-action-accent-tint text-action-accent" : "text-text-primary hover:bg-surface-hover",
                      )}
                    >
                      <span className="min-w-0 flex-1 truncate text-body-sm font-semibold">{c.name || "Untitled"}</span>
                      <span className="tabular text-caption text-text-subtle">{c.children.length}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <form
                className="flex gap-1.5 border-t border-border p-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!draftCategory.trim()) return;
                  setTree((t) => [...t, { key: uid(), name: draftCategory.trim(), used: 0, children: [] }]);
                  setSelected(tree.length);
                  setDraftCategory("");
                }}
              >
                <input
                  value={draftCategory}
                  onChange={(e) => setDraftCategory(e.target.value)}
                  placeholder="New category"
                  aria-label="New category"
                  className="h-8 min-w-0 flex-1 rounded-sm border border-border bg-surface-primary px-2 text-body-sm focus:border-action-accent focus:outline-none"
                />
                <Button size="sm" type="submit" variant="secondary" disabled={!draftCategory.trim()}>
                  Add
                </Button>
              </form>
            </div>

            {current ? (
              <div className="space-y-3">
                <div className="flex items-end gap-2">
                  <div className="min-w-0 flex-1">
                    <TextField
                      label="Category name"
                      value={current.name}
                      onChange={(e) =>
                        setTree((t) => t.map((c, i) => (i === selected ? { ...c, name: e.target.value } : c)))
                      }
                    />
                  </div>
                  <Button size="icon" variant="ghost" aria-label="Move up" disabled={selected === 0} onClick={() => move(selected, -1)}>
                    <Icon name="arrowup" className="size-4" />
                  </Button>
                  <Button size="icon" variant="ghost" aria-label="Move down" disabled={selected === tree.length - 1} onClick={() => move(selected, 1)}>
                    <Icon name="arrowdown" className="size-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label="Remove category"
                    disabled={tree.length === 1}
                    onClick={() => {
                      setTree((t) => t.filter((_, i) => i !== selected));
                      setSelected(0);
                    }}
                  >
                    <Icon name="trash" className="size-4" />
                  </Button>
                </div>
                {current.used ? (
                  <p className="text-caption text-text-subtle">
                    {current.used} {current.used === 1 ? "risk uses" : "risks use"} this category. Removing it archives it.
                  </p>
                ) : null}
                <div>
                  <p className="mb-1.5 text-label-sm text-text-secondary">Subcategories</p>
                  <ul className="space-y-1.5">
                    {current.children.map((s, j) => (
                      <li key={s.key} className="flex items-center gap-2">
                        <input
                          value={s.name}
                          onChange={(e) =>
                            setTree((t) =>
                              t.map((c, i) =>
                                i === selected
                                  ? { ...c, children: c.children.map((x, k) => (k === j ? { ...x, name: e.target.value } : x)) }
                                  : c,
                              ),
                            )
                          }
                          aria-label={`Subcategory ${j + 1}`}
                          className="h-8 min-w-0 flex-1 rounded-sm border border-border bg-surface-primary px-2 text-body-sm focus:border-action-accent focus:outline-none"
                        />
                        {s.used ? <span className="tabular w-14 text-right text-caption text-text-subtle">{s.used} used</span> : null}
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          aria-label={`Remove ${s.name}`}
                          onClick={() =>
                            setTree((t) =>
                              t.map((c, i) => (i === selected ? { ...c, children: c.children.filter((_, k) => k !== j) } : c)),
                            )
                          }
                        >
                          <Icon name="x" className="size-4" />
                        </Button>
                      </li>
                    ))}
                  </ul>
                  <form
                    className="mt-2 flex gap-1.5"
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (!draftSub.trim()) return;
                      setTree((t) =>
                        t.map((c, i) =>
                          i === selected ? { ...c, children: [...c.children, { key: uid(), name: draftSub.trim(), used: 0 }] } : c,
                        ),
                      );
                      setDraftSub("");
                    }}
                  >
                    <input
                      value={draftSub}
                      onChange={(e) => setDraftSub(e.target.value)}
                      placeholder="New subcategory"
                      aria-label="New subcategory"
                      className="h-8 min-w-0 flex-1 rounded-sm border border-border bg-surface-primary px-2 text-body-sm focus:border-action-accent focus:outline-none"
                    />
                    <Button size="sm" type="submit" variant="secondary" disabled={!draftSub.trim()}>
                      Add
                    </Button>
                  </form>
                </div>
              </div>
            ) : null}
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} disabled={tree.some((c) => !c.name.trim())} onClick={() => save.mutate()}>
            Save categories
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
