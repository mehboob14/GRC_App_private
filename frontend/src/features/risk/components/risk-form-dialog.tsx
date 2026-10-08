import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { assistDraft, createRisk, getOptions, updateRisk } from "../api";
import type {
  AssistDraft,
  Register,
  RiskDetail,
  RiskInput,
  RiskStatus,
  Treatment,
} from "../types";
import { REGISTER_TYPE_LABEL, STATUS_META, TREATMENT_META } from "../tokens";
import { AssetPicker } from "./asset-picker";
import { CustomFieldInputs } from "@/features/custom-fields/components/custom-field-inputs";
import { useCustomFields } from "@/features/custom-fields/hooks";
import { scoreOf } from "../scoring";
import { ScorePairInput } from "./score";
import { SoonBadge } from "./soon";

const NONE = "__none__";
const EDITABLE_STATUSES: RiskStatus[] = ["open", "in_treatment", "mitigated"];

type Form = Omit<RiskInput, "asset_ids"> & { asset_ids: string[] };

function blank(register: Register): Form {
  const operational = register.categories.find((c) => !c.archived && c.name === "Operational");
  const first = operational ?? register.categories.find((c) => !c.archived);
  return {
    register_id: register.id,
    title: "",
    description: "",
    category_id: first?.id ?? "",
    sub_category_id: null,
    status: "open",
    treatment: null,
    inherent_likelihood: null,
    inherent_impact: null,
    residual_likelihood: null,
    residual_impact: null,
    root_cause: null,
    consequences: null,
    recommendations: null,
    treatment_plan: null,
    owner_membership_id: null,
    department_group_id: null,
    treatment_due_on: null,
    next_review_on: null,
    asset_ids: [],
    custom_fields: {},
  };
}

function fromRisk(risk: RiskDetail): Form {
  return {
    register_id: risk.register_id,
    title: risk.title,
    description: risk.description,
    category_id: risk.category_id,
    sub_category_id: risk.sub_category_id,
    status: risk.status,
    treatment: risk.treatment,
    inherent_likelihood: risk.inherent_likelihood,
    inherent_impact: risk.inherent_impact,
    residual_likelihood: risk.residual_likelihood,
    residual_impact: risk.residual_impact,
    root_cause: risk.root_cause,
    consequences: risk.consequences,
    recommendations: risk.recommendations,
    treatment_plan: risk.treatment_plan,
    owner_membership_id: risk.owner?.membership_id ?? null,
    department_group_id: risk.department_group_id,
    treatment_due_on: risk.treatment_due_on,
    next_review_on: risk.next_review_on,
    asset_ids: risk.links.filter((l) => l.target_type === "asset").map((l) => l.target_id),
    custom_fields: { ...(risk.custom_fields ?? {}) },
  };
}

export type RiskPrefill = Partial<Form>;

/**
 * The risk, in one popup. Narrative on the left, classification on the right,
 * scoring and treatment across the bottom, so a person fills it top to bottom
 * without hunting. AI Assist drafts from the title; nothing it suggests lands
 * in the form until someone applies it, and nothing is saved until they save.
 */
export function RiskFormDialog({
  open,
  onOpenChange,
  registers,
  register,
  risk,
  prefill,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  registers: Register[];
  register: Register;
  /** Present means edit. */
  risk?: RiskDetail;
  prefill?: RiskPrefill;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const editing = risk !== undefined;
  const [form, setForm] = useState<Form>(() => blank(register));
  const [draft, setDraft] = useState<AssistDraft | null>(null);
  const [applied, setApplied] = useState<Set<string>>(new Set());
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(risk ? fromRisk(risk) : { ...blank(register), ...prefill });
    setDraft(null);
    setApplied(new Set());
    setTouched(false);
  }, [open, risk, register, prefill]);

  const active = registers.find((r) => r.id === form.register_id) ?? register;
  const categories = active.categories.filter((c) => !c.archived || c.id === form.category_id);
  const category = active.categories.find((c) => c.id === form.category_id);
  const subcategories = (category?.children ?? []).filter((s) => !s.archived || s.id === form.sub_category_id);

  const optionsQuery = useQuery({ queryKey: ["risk-options"], queryFn: getOptions, staleTime: 60_000 });
  const people = (optionsQuery.data?.members ?? []).map((m) => ({ id: m.membership_id, name: m.name }));
  const units = optionsQuery.data?.business_units ?? [];

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => ({ ...f, [key]: value }));

  const switchRegister = (id: string) => {
    const next = registers.find((r) => r.id === id);
    if (!next) return;
    const base = blank(next);
    setForm((f) => ({
      ...f,
      register_id: id,
      category_id: base.category_id,
      sub_category_id: null,
      inherent_likelihood: null,
      inherent_impact: null,
      residual_likelihood: null,
      residual_impact: null,
    }));
  };

  const assist = useMutation({
    mutationFn: () => assistDraft(form.register_id, form.title.trim(), form.description.trim()),
    onSuccess: (result) => {
      setDraft(result);
      setApplied(new Set());
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "draft"), tone: "danger" }),
  });

  const customFields = useCustomFields("risks").data ?? [];
  const suggestions = useMemo(() => (draft ? draftRows(draft, active) : []), [draft, active]);

  const apply = (key: string) => {
    if (!draft) return;
    setForm((f) => applyDraft(f, draft, key));
    setApplied((s) => new Set(s).add(key));
  };
  const applyAll = () => {
    if (!draft) return;
    setForm((f) => suggestions.reduce((acc, row) => applyDraft(acc, draft, row.key), f));
    setApplied(new Set(suggestions.map((r) => r.key)));
  };

  const save = useMutation({
    mutationFn: () => {
      const body: RiskInput = {
        ...form,
        title: form.title.trim(),
        description: form.description.trim(),
        root_cause: form.root_cause?.trim() || null,
        consequences: form.consequences?.trim() || null,
        recommendations: form.recommendations?.trim() || null,
        treatment_plan: form.treatment_plan?.trim() || null,
        asset_ids: form.asset_ids,
      };
      return editing ? updateRisk(risk.id, body) : createRisk(body);
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(["risk", saved.id], saved);
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      toast({ title: editing ? "Risk updated" : `${saved.code} added`, tone: "success" });
      onOpenChange(false);
      if (!editing) navigate(`/risks/${saved.id}`);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "risk"), tone: "danger" }),
  });

  const titleMissing = touched && !form.title.trim();
  const statusLocked = editing && !EDITABLE_STATUSES.includes(risk.status);
  const statusOptions = editing
    ? EDITABLE_STATUSES.filter((s) => s === risk.status || risk.allowed_statuses.includes(s))
    : EDITABLE_STATUSES;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="2xl" scrollBody className="max-h-[94vh] p-0">
        <DialogHeader className="border-b border-border px-6 pb-4 pt-5">
          <DialogTitle>{editing ? `Edit ${risk.code}` : "Add risk"}</DialogTitle>
          <DialogDescription>
            {active.name} · {REGISTER_TYPE_LABEL[active.register_type]}
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            setTouched(true);
            if (form.title.trim() && form.category_id) save.mutate();
          }}
        >
          <DialogBody className="mx-0 space-y-5 px-6 py-5">
            <div>
              <div className="flex items-end gap-2">
                <div className="min-w-0 flex-1">
                  <TextField
                    label="Title"
                    value={form.title}
                    onChange={(e) => set("title", e.target.value)}
                    placeholder="Customer data exposed through a misconfigured storage bucket"
                    error={titleMissing ? "Give the risk a title." : undefined}
                    autoFocus
                  />
                </div>
                <Button
                  type="button"
                  variant="accent"
                  onClick={() => assist.mutate()}
                  loading={assist.isPending}
                  disabled={form.title.trim().length < 4}
                >
                  <Icon name="sparkle" className="size-4" />
                  AI Assist
                </Button>
              </div>
              {draft ? (
                <AssistPanel
                  draft={draft}
                  rows={suggestions}
                  applied={applied}
                  onApply={apply}
                  onApplyAll={applyAll}
                  onDismiss={() => setDraft(null)}
                />
              ) : null}
            </div>

            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_21rem]">
              <div className="space-y-4">
                <TextArea
                  label="Description"
                  optional
                  rows={3}
                  value={form.description}
                  onChange={(e) => set("description", e.target.value)}
                  placeholder="What could happen, to what, and how"
                />
                <div className="grid gap-4 md:grid-cols-2">
                  <TextArea
                    label="Root cause"
                    optional
                    rows={3}
                    value={form.root_cause ?? ""}
                    onChange={(e) => set("root_cause", e.target.value)}
                    placeholder="Why it could happen"
                  />
                  <TextArea
                    label="Consequences"
                    optional
                    rows={3}
                    value={form.consequences ?? ""}
                    onChange={(e) => set("consequences", e.target.value)}
                    placeholder="What it would cost the business"
                  />
                </div>
                <TextArea
                  label="Recommendations"
                  optional
                  rows={2}
                  value={form.recommendations ?? ""}
                  onChange={(e) => set("recommendations", e.target.value)}
                  placeholder="What would reduce it"
                />
              </div>

              <div className="space-y-3.5 rounded-lg border border-border bg-surface-sunken p-4">
                {!editing && registers.length > 1 ? (
                  <SelectField label="Register">
                    <Select value={form.register_id} onValueChange={switchRegister}>
                      <SelectTrigger aria-label="Register" />
                      <SelectContent>
                        {registers
                          .filter((r) => r.status === "active")
                          .map((r) => (
                            <SelectItem key={r.id} value={r.id}>
                              {r.name} · {REGISTER_TYPE_LABEL[r.register_type]}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </SelectField>
                ) : (
                  <div>
                    <p className="text-label-sm text-text-secondary">Register type</p>
                    <p className="mt-1 flex items-center gap-2 text-body-md text-text-primary">
                      <Badge variant="neutral">{REGISTER_TYPE_LABEL[active.register_type]}</Badge>
                      <span className="truncate text-text-subtle">{active.name}</span>
                    </p>
                  </div>
                )}
                <SelectField label="Category">
                  <Select
                    value={form.category_id || undefined}
                    onValueChange={(v) => setForm((f) => ({ ...f, category_id: v, sub_category_id: null }))}
                  >
                    <SelectTrigger aria-label="Category" />
                    <SelectContent>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                <SelectField label="Subcategory" optional>
                  <Select
                    value={form.sub_category_id ?? NONE}
                    onValueChange={(v) => set("sub_category_id", v === NONE ? null : v)}
                    disabled={!subcategories.length}
                  >
                    <SelectTrigger aria-label="Subcategory" />
                    <SelectContent>
                      <SelectItem value={NONE}>Select subcategory</SelectItem>
                      {subcategories.map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                <SelectField label="Status">
                  {statusLocked ? (
                    <p className="flex h-9 items-center text-body-md text-text-primary">
                      {STATUS_META[risk.status].label}
                    </p>
                  ) : (
                    <Select value={form.status} onValueChange={(v) => set("status", v as RiskStatus)}>
                      <SelectTrigger aria-label="Status" />
                      <SelectContent>
                        {statusOptions.map((s) => (
                          <SelectItem key={s} value={s}>
                            {STATUS_META[s].label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </SelectField>
                <div>
                  <p className="mb-1.5 text-label-sm text-text-secondary">Business owner</p>
                  <PersonSelect
                    people={people}
                    value={form.owner_membership_id}
                    onChange={(v) => set("owner_membership_id", v)}
                    placeholder="Select owner"
                    clearLabel="No owner"
                    aria-label="Business owner"
                  />
                </div>
                <SelectField label="Business unit" optional>
                  <Select
                    value={form.department_group_id ?? NONE}
                    onValueChange={(v) => set("department_group_id", v === NONE ? null : v)}
                  >
                    <SelectTrigger aria-label="Business unit" />
                    <SelectContent>
                      <SelectItem value={NONE}>{units.length ? "Select department" : "No groups yet"}</SelectItem>
                      {units.map((u) => (
                        <SelectItem key={u.id} value={u.id}>
                          {u.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                <div>
                  <p className="mb-1.5 flex items-center justify-between text-label-sm text-text-secondary">
                    Linked assets
                    <span className="text-caption font-normal text-text-subtle">Optional</span>
                  </p>
                  <AssetPicker value={form.asset_ids} onChange={(ids) => set("asset_ids", ids)} />
                </div>
              </div>
            </div>

            <section>
              <SectionTitle icon="heatmap" title="Assessment" />
              <div className="grid gap-3 lg:grid-cols-2">
                <ScorePairInput
                  title="Inherent risk"
                  likelihoodScale={active.likelihood_scale}
                  impactScale={active.impact_scale}
                  bands={active.severity_bands}
                  formula={active.scoring_formula}
                  likelihood={form.inherent_likelihood}
                  impact={form.inherent_impact}
                  onChange={(l, i) => setForm((f) => ({ ...f, inherent_likelihood: l, inherent_impact: i }))}
                />
                <ScorePairInput
                  title="Residual risk"
                  likelihoodScale={active.likelihood_scale}
                  impactScale={active.impact_scale}
                  bands={active.severity_bands}
                  likelihood={form.residual_likelihood}
                  impact={form.residual_impact}
                  onChange={(l, i) => setForm((f) => ({ ...f, residual_likelihood: l, residual_impact: i }))}
                />
              </div>
            </section>

            {customFields.length > 0 ? (
              <section>
                <SectionTitle icon="textbox" title="More details" />
                <CustomFieldInputs
                  fields={customFields}
                  values={form.custom_fields ?? {}}
                  onChange={(values) => set("custom_fields", values)}
                />
              </section>
            ) : null}

            <section>
              <SectionTitle icon="shield" title="Treatment" />
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_21rem]">
                <div className="space-y-3">
                  <div role="radiogroup" aria-label="Treatment" className="grid grid-cols-2 gap-2 md:grid-cols-4">
                    {(Object.keys(TREATMENT_META) as Treatment[]).map((t) => {
                      const on = form.treatment === t;
                      return (
                        <button
                          key={t}
                          type="button"
                          role="radio"
                          aria-checked={on}
                          onClick={() => set("treatment", on ? null : t)}
                          className={cn(
                            "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150",
                            on
                              ? "border-action-accent bg-action-accent-tint"
                              : "border-border bg-surface-primary hover:bg-surface-hover",
                          )}
                        >
                          <span
                            className={cn(
                              "grid size-8 shrink-0 place-items-center rounded-md",
                              on ? "bg-action-accent text-white" : "bg-surface-sunken text-text-subtle",
                            )}
                          >
                            <Icon name={TREATMENT_META[t].icon} className="size-4" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-label-md text-text-primary">{TREATMENT_META[t].label}</span>
                            <span className="block truncate text-caption text-text-subtle">{TREATMENT_META[t].hint}</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <TextArea
                    label="Treatment plan"
                    optional
                    rows={3}
                    value={form.treatment_plan ?? ""}
                    onChange={(e) => set("treatment_plan", e.target.value)}
                    placeholder="The steps, who owns them, and by when"
                  />
                </div>
                <div className="space-y-3.5">
                  <TextField
                    label="Treatment due"
                    optional
                    type="date"
                    value={form.treatment_due_on ?? ""}
                    onChange={(e) => set("treatment_due_on", e.target.value || null)}
                  />
                  <TextField
                    label="Next review"
                    optional
                    type="date"
                    hint={form.next_review_on ? undefined : `Defaults to ${active.review_cadence_days} days from today`}
                    value={form.next_review_on ?? ""}
                    onChange={(e) => set("next_review_on", e.target.value || null)}
                  />
                  <div className="flex items-center justify-between rounded-lg border border-border bg-surface-primary px-3 py-2.5">
                    <span className="flex items-center gap-2 text-label-sm text-text-secondary">
                      <Icon name="textbox" className="size-4 text-text-subtle" />
                      Custom fields
                    </span>
                    <SoonBadge />
                  </div>
                </div>
              </div>
            </section>
          </DialogBody>

          <DialogFooter className="mt-0 border-t border-border px-6 py-4">
            <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              {editing ? "Save changes" : "Add risk"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SectionTitle({ icon, title }: { icon: "heatmap" | "shield" | "textbox"; title: string }) {
  return (
    <h3 className="mb-2.5 flex items-center gap-2 text-label-md text-text-primary">
      <Icon name={icon} className="size-4 text-text-subtle" />
      {title}
    </h3>
  );
}

// -- AI Assist -------------------------------------------------------------------

type DraftRow = { key: string; label: string; value: string };

function draftRows(draft: AssistDraft, register: Register): DraftRow[] {
  const rows: DraftRow[] = [];
  const category = register.categories.find((c) => c.id === draft.category_id);
  const sub = category?.children.find((s) => s.id === draft.sub_category_id);
  if (category) rows.push({ key: "category", label: "Category", value: sub ? `${category.name} · ${sub.name}` : category.name });
  const text: [keyof AssistDraft, string][] = [
    ["description", "Description"],
    ["root_cause", "Root cause"],
    ["consequences", "Consequences"],
    ["recommendations", "Recommendations"],
    ["treatment_plan", "Treatment plan"],
  ];
  for (const [key, label] of text) {
    const value = draft[key];
    if (typeof value === "string" && value) rows.push({ key, label, value });
  }
  if (draft.inherent_likelihood && draft.inherent_impact) {
    rows.push({
      key: "inherent",
      label: "Inherent",
      value: `Likelihood ${draft.inherent_likelihood} · Impact ${draft.inherent_impact} · Score ${scoreOf(register.scoring_formula, draft.inherent_likelihood, draft.inherent_impact)}`,
    });
  }
  if (draft.residual_likelihood && draft.residual_impact) {
    rows.push({
      key: "residual",
      label: "Residual",
      value: `Likelihood ${draft.residual_likelihood} · Impact ${draft.residual_impact} · Score ${scoreOf(register.scoring_formula, draft.residual_likelihood, draft.residual_impact)}`,
    });
  }
  if (draft.treatment) rows.push({ key: "treatment", label: "Treatment", value: TREATMENT_META[draft.treatment].label });
  return rows;
}

function applyDraft(form: Form, draft: AssistDraft, key: string): Form {
  switch (key) {
    case "category":
      return draft.category_id
        ? { ...form, category_id: draft.category_id, sub_category_id: draft.sub_category_id }
        : form;
    case "inherent":
      return { ...form, inherent_likelihood: draft.inherent_likelihood, inherent_impact: draft.inherent_impact };
    case "residual":
      return { ...form, residual_likelihood: draft.residual_likelihood, residual_impact: draft.residual_impact };
    case "treatment":
      return { ...form, treatment: draft.treatment };
    case "description":
      return { ...form, description: draft.description ?? form.description };
    default:
      return { ...form, [key]: (draft[key as keyof AssistDraft] as string | null) ?? null };
  }
}

function AssistPanel({
  draft,
  rows,
  applied,
  onApply,
  onApplyAll,
  onDismiss,
}: {
  draft: AssistDraft;
  rows: DraftRow[];
  applied: Set<string>;
  onApply: (key: string) => void;
  onApplyAll: () => void;
  onDismiss: () => void;
}) {
  const heading =
    draft.source === "ai" ? "AI draft" : draft.source === "library" ? "Closest library match" : "No close match";
  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-action-accent-border bg-action-accent-tint/40">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-action-accent-border px-4 py-2.5">
        <p className="flex items-center gap-2 text-label-md text-text-primary">
          <Icon name="sparkle" className="size-4 text-action-accent" />
          {heading}
          <span className="text-caption font-normal text-text-subtle">Review before saving</span>
        </p>
        <div className="flex items-center gap-1.5">
          {rows.length ? (
            <Button size="sm" variant="secondary" type="button" onClick={onApplyAll}>
              Use all
            </Button>
          ) : null}
          <Button size="icon-sm" variant="ghost" type="button" onClick={onDismiss} aria-label="Dismiss suggestions">
            <Icon name="x" className="size-4" />
          </Button>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-3 text-body-sm text-text-subtle">Try a more specific title, then ask again.</p>
      ) : (
        <ul className="max-h-72 divide-y divide-border overflow-y-auto bg-surface-primary">
          {rows.map((row) => {
            const done = applied.has(row.key);
            return (
              <li key={row.key} className="flex items-start gap-3 px-4 py-2.5">
                <span className="w-28 shrink-0 pt-0.5 text-label-sm text-text-secondary">{row.label}</span>
                <span className="line-clamp-2 min-w-0 flex-1 text-body-sm text-text-primary">{row.value}</span>
                <Button
                  size="sm"
                  variant={done ? "ghost" : "secondary"}
                  type="button"
                  onClick={() => onApply(row.key)}
                  disabled={done}
                >
                  {done ? (
                    <>
                      <Icon name="check" className="size-3.5" />
                      Added
                    </>
                  ) : (
                    "Use"
                  )}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
      {draft.similar.length ? (
        <p className="border-t border-action-accent-border px-4 py-2 text-caption text-text-subtle">
          Similar in the library: {draft.similar.map((s) => s.title).join(", ")}
        </p>
      ) : null}
    </div>
  );
}
