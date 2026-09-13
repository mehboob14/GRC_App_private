import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  Icon,
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
import { addQuestion, updateQuestion } from "../api";
import { isChoice, TYPE_META } from "../questionnaire-logic";
import {
  QUESTION_TYPES,
  TIERS,
  type BuilderQuestion,
  type EvidenceRule,
  type QuestionInput,
  type QuestionOption,
  type Questionnaire,
  type QuestionType,
} from "../types";
import { TIER_META } from "../tokens";

type OptionDraft = Omit<QuestionOption, "min_tier"> & { min_tier: string | null; uid: string };

let uidCounter = 0;
const uid = () => `o${++uidCounter}`;
/** A stable key from the start, so evidence and branching rules can point at a new answer. */
const newKey = () => `answer_${Date.now().toString(36)}${(++uidCounter).toString(36)}`;

const blankOption = (label: string, score: number, extra: Partial<QuestionOption> = {}): OptionDraft => ({
  uid: uid(),
  key: newKey(),
  label,
  score,
  flag: false,
  not_applicable: false,
  comment_required: false,
  min_tier: null,
  ...extra,
});

/** Starting answers a person picks from instead of typing the same four every time. */
const PRESETS = {
  due_diligence: [
    {
      label: "Yes, partially, no, n/a",
      make: () => [
        blankOption("Yes", 100, { key: "yes" }),
        blankOption("Partially", 50, { key: "partial" }),
        blankOption("No", 0, { key: "no", flag: true }),
        blankOption("Not applicable", 0, { key: "na", not_applicable: true, comment_required: true }),
      ],
    },
    {
      label: "Yes or no",
      make: () => [blankOption("Yes", 100, { key: "yes" }), blankOption("No", 0, { key: "no", flag: true })],
    },
  ],
  tiering: [
    {
      label: "Low to critical",
      make: () => [
        blankOption("None", 0),
        blankOption("Low", 1),
        blankOption("Moderate", 2),
        blankOption("High", 3),
        blankOption("Very high", 4),
      ],
    },
    { label: "Yes or no", make: () => [blankOption("No", 0), blankOption("Yes", 4)] },
  ],
} as const;

type Draft = {
  prompt: string;
  help_text: string;
  answer_type: QuestionType;
  section: string;
  options: OptionDraft[];
  required: boolean;
  evidence: EvidenceRule;
  evidence_on: string[];
  weight: number;
  domain: string;
  critical: boolean;
  blocking: boolean;
  condition_question_id: string;
  condition_option_keys: string[];
};

function draftFrom(questionnaire: Questionnaire, question: BuilderQuestion | null, section: string): Draft {
  if (question) {
    return {
      prompt: question.prompt,
      help_text: question.help_text ?? "",
      answer_type: question.answer_type,
      section: question.section,
      options: question.options.map((o) => ({ ...o, uid: uid() })),
      required: question.required,
      evidence: question.evidence,
      evidence_on: question.evidence_on,
      weight: question.weight,
      domain: question.domain ?? "information_security",
      critical: question.critical,
      blocking: question.blocking,
      condition_question_id: question.condition.question_id ?? "",
      condition_option_keys: question.condition.option_keys ?? [],
    };
  }
  const tiering = questionnaire.purpose === "tiering";
  return {
    prompt: "",
    help_text: "",
    answer_type: "single_choice",
    section,
    options: (tiering ? PRESETS.tiering[0] : PRESETS.due_diligence[0]).make(),
    required: true,
    evidence: "none",
    evidence_on: [],
    weight: tiering ? 10 : 1,
    domain: "information_security",
    critical: false,
    blocking: false,
    condition_question_id: "",
    condition_option_keys: [],
  };
}

/**
 * One question, edited in a side panel: what is asked on the left, the rules
 * on the right. Everything a real programme sets per question is here, and
 * nothing that does not apply to this questionnaire's purpose is shown.
 */
export function QuestionEditor({
  open,
  onOpenChange,
  questionnaire,
  question,
  afterId,
  riskDomains,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  questionnaire: Questionnaire;
  question: BuilderQuestion | null;
  afterId: string | null;
  riskDomains: { key: string; label: string }[];
  onSaved: (next: Questionnaire) => void;
}) {
  const { toast } = useToast();
  const tiering = questionnaire.purpose === "tiering";
  const questions = questionnaire.questions;
  const defaultSection =
    questions.find((q) => q.id === afterId)?.section ?? questions[questions.length - 1]?.section ?? "General";
  const [draft, setDraft] = useState<Draft>(() => draftFrom(questionnaire, question, defaultSection));

  useEffect(() => {
    if (open) setDraft(draftFrom(questionnaire, question, defaultSection));
    // Seed once per opening; a background refetch must not wipe what is being typed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, question?.id]);

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }));
  const setOption = (id: string, patch: Partial<OptionDraft>) =>
    setDraft((d) => ({ ...d, options: d.options.map((o) => (o.uid === id ? { ...o, ...patch } : o)) }));

  // A follow-up can only depend on a choice question that comes before this one.
  const position = question ? questions.findIndex((q) => q.id === question.id) : afterId ? questions.findIndex((q) => q.id === afterId) + 1 : questions.length;
  const parents = questions.slice(0, position < 0 ? questions.length : position).filter((q) => isChoice(q.answer_type));
  const parent = parents.find((q) => q.id === draft.condition_question_id);
  const sections = useMemo(() => [...new Set(questions.map((q) => q.section))], [questions]);
  const choice = isChoice(draft.answer_type);
  const number = question ? questions.findIndex((q) => q.id === question.id) + 1 : null;

  const body = (): QuestionInput => ({
    prompt: draft.prompt.trim(),
    answer_type: draft.answer_type,
    section: draft.section.trim() || "General",
    help_text: draft.help_text.trim() || null,
    options: choice
      ? draft.options.map((o) => ({
          key: o.key,
          label: o.label.trim(),
          score: o.score,
          flag: o.flag,
          not_applicable: o.not_applicable,
          comment_required: o.comment_required,
          min_tier: o.min_tier,
        }))
      : [],
    required: draft.required,
    evidence: tiering ? "none" : draft.evidence,
    evidence_on: draft.evidence === "required" && choice ? draft.evidence_on : [],
    weight: Number.isFinite(draft.weight) ? draft.weight : 1,
    domain: tiering ? null : draft.domain,
    critical: !tiering && draft.critical,
    blocking: !tiering && draft.blocking,
    condition:
      draft.condition_question_id && draft.condition_option_keys.length
        ? { question_id: draft.condition_question_id, option_keys: draft.condition_option_keys }
        : null,
  });

  const save = useMutation({
    mutationFn: () =>
      question
        ? updateQuestion(questionnaire.id, question.id, body())
        : addQuestion(questionnaire.id, { ...body(), after_question_id: afterId }),
    onSuccess: (next) => {
      onSaved(next);
      toast({ title: question ? "Question saved" : "Question added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "question"), tone: "danger" }),
  });

  const problems = [
    !draft.prompt.trim() && "Write the question.",
    choice && draft.options.length < 2 && "Add at least two answers.",
    choice && draft.options.some((o) => !o.label.trim()) && "Every answer needs a label.",
    draft.condition_question_id && !draft.condition_option_keys.length && "Pick which answers show this question.",
  ].filter(Boolean) as string[];

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent size="xl">
        <DrawerHeader>
          <DrawerTitle>{question ? `Edit Q${number}` : "New question"}</DrawerTitle>
          <DrawerDescription>
            {tiering ? "Answered by your team. Scores add up to the tier." : "Answered by the vendor in the portal."}
          </DrawerDescription>
        </DrawerHeader>

        <DrawerBody className="p-0">
          <div className="grid min-h-full md:grid-cols-[minmax(0,1fr)_16.5rem]">
            <div className="space-y-5 px-5 py-4">
              <TextArea
                label="Question"
                value={draft.prompt}
                onChange={(e) => set("prompt", e.target.value)}
                rows={2}
                maxLength={1000}
                autoFocus
              />
              <TextField
                label="Help text"
                optional
                value={draft.help_text}
                onChange={(e) => set("help_text", e.target.value)}
                maxLength={2000}
                placeholder="What a good answer includes"
              />

              <div>
                <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Answer type</p>
                <div role="radiogroup" aria-label="Answer type" className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                  {QUESTION_TYPES.filter((t) => !tiering || t !== "file").map((type) => {
                    const on = draft.answer_type === type;
                    return (
                      <button
                        key={type}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() =>
                          setDraft((d) => ({
                            ...d,
                            answer_type: type,
                            options:
                              isChoice(type) && d.options.length < 2
                                ? (tiering ? PRESETS.tiering[0] : PRESETS.due_diligence[0]).make()
                                : d.options,
                          }))
                        }
                        className={cn(
                          "flex items-center gap-2 rounded-md border px-2.5 py-2 text-left text-label-sm transition-colors duration-80 ease-state",
                          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                          on
                            ? "border-action-accent bg-action-accent-tint text-action-accent"
                            : "border-border text-text-secondary hover:bg-surface-hover",
                        )}
                      >
                        <Icon name={TYPE_META[type].icon} className="size-4" />
                        {TYPE_META[type].label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {choice ? (
                <OptionsEditor
                  tiering={tiering}
                  options={draft.options}
                  onChange={(options) => set("options", options)}
                  onPatch={setOption}
                />
              ) : (
                <p className="flex items-start gap-2 rounded-md bg-surface-sunken px-3 py-2.5 text-body-sm text-text-secondary">
                  <Icon name="info" className="mt-0.5 size-4 shrink-0 text-text-subtle" />
                  {draft.answer_type === "file"
                    ? "The vendor uploads a document as the answer."
                    : "Recorded for reviewers. It does not change the score."}
                </p>
              )}
            </div>

            <div className="space-y-4 border-t border-border bg-surface-sunken/60 px-4 py-4 md:border-l md:border-t-0">
              <div className="flex w-full flex-col gap-1.5">
                <label htmlFor="question-section" className="font-sans text-label-sm text-text-secondary">
                  Section
                </label>
                <input
                  id="question-section"
                  list="question-sections"
                  value={draft.section}
                  onChange={(e) => set("section", e.target.value)}
                  maxLength={80}
                  className="h-9 w-full rounded-sm border border-border bg-surface-primary px-3 text-body-md text-text-primary focus:border-action-accent focus:shadow-input-focus focus:outline-none"
                />
                <datalist id="question-sections">
                  {sections.map((s) => (
                    <option key={s} value={s} />
                  ))}
                </datalist>
              </div>

              <ToggleRow
                label="Required"
                hint={draft.answer_type === "file" ? "A document must be uploaded" : "Must be answered to finish"}
                checked={draft.required}
                onChange={(v) => set("required", v)}
              />

              {choice ? (
                <TextField
                  label="Weight"
                  type="number"
                  min={0}
                  max={100}
                  step={tiering ? 1 : 0.1}
                  value={String(draft.weight)}
                  onChange={(e) => set("weight", Number(e.target.value))}
                  hint={tiering ? "How much this counts toward the tier" : "How much this counts in its domain"}
                />
              ) : null}

              {!tiering && draft.answer_type !== "file" ? (
                <div className="space-y-2">
                  <p className="font-sans text-label-sm text-text-secondary">Evidence</p>
                  <SegmentedControl
                    label="Evidence"
                    className="w-full [&>button]:flex-1"
                    items={[
                      { id: "none", label: "None" },
                      { id: "optional", label: "Optional" },
                      { id: "required", label: "Required" },
                    ]}
                    value={draft.evidence}
                    onChange={(v) => set("evidence", v)}
                  />
                  {draft.evidence === "required" && choice ? (
                    <div className="rounded-md border border-border bg-surface-primary p-2.5">
                      <p className="text-caption text-text-subtle">Needed when the answer is</p>
                      <div className="mt-1.5 space-y-1">
                        {draft.options.map((o) => (
                          <label key={o.uid} className="flex items-center gap-2 text-body-sm text-text-primary">
                            <Checkbox
                              checked={draft.evidence_on.includes(o.key)}
                              disabled={!o.key}
                              onCheckedChange={(on) =>
                                set(
                                  "evidence_on",
                                  on ? [...draft.evidence_on, o.key] : draft.evidence_on.filter((k) => k !== o.key),
                                )
                              }
                              aria-label={o.label}
                            />
                            {o.label || "Untitled"}
                          </label>
                        ))}
                      </div>
                      <p className="mt-1.5 text-caption text-text-faint">None ticked means any answer.</p>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {!tiering ? (
                <>
                  <SelectField label="Risk domain">
                    <Select value={draft.domain} onValueChange={(v) => set("domain", v)}>
                      <SelectTrigger aria-label="Risk domain" className="text-left [&>span]:truncate" />
                      <SelectContent>
                        {riskDomains.map((d) => (
                          <SelectItem key={d.key} value={d.key}>
                            {d.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </SelectField>
                  {choice ? (
                    <>
                      <ToggleRow
                        label="Critical control"
                        hint="A gap holds the score at high or worse"
                        checked={draft.critical}
                        onChange={(v) => set("critical", v)}
                      />
                      <ToggleRow
                        label="Blocks approval"
                        hint="A gap must be resolved before approval"
                        checked={draft.blocking}
                        onChange={(v) => set("blocking", v)}
                      />
                    </>
                  ) : null}
                </>
              ) : null}

              <div className="space-y-2">
                <SelectField label="Show this question">
                  <Select
                    value={draft.condition_question_id || "__always__"}
                    onValueChange={(v) =>
                      setDraft((d) => ({
                        ...d,
                        condition_question_id: v === "__always__" ? "" : v,
                        condition_option_keys: [],
                      }))
                    }
                  >
                    <SelectTrigger aria-label="Show this question" className="text-left [&>span]:truncate" />
                    <SelectContent>
                      <SelectItem value="__always__">Always</SelectItem>
                      {parents.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {`Only if Q${questions.indexOf(p) + 1}: ${p.prompt.length > 42 ? `${p.prompt.slice(0, 42)}…` : p.prompt}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                {parent ? (
                  <div className="rounded-md border border-border bg-surface-primary p-2.5">
                    <p className="text-caption text-text-subtle">is answered with</p>
                    <div className="mt-1.5 space-y-1">
                      {parent.options.map((o) => (
                        <label key={o.key} className="flex items-center gap-2 text-body-sm text-text-primary">
                          <Checkbox
                            checked={draft.condition_option_keys.includes(o.key)}
                            onCheckedChange={(on) =>
                              set(
                                "condition_option_keys",
                                on
                                  ? [...draft.condition_option_keys, o.key]
                                  : draft.condition_option_keys.filter((k) => k !== o.key),
                              )
                            }
                            aria-label={o.label}
                          />
                          {o.label}
                        </label>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </DrawerBody>

        <DrawerFooter className="justify-between">
          <p className="min-w-0 truncate text-caption text-status-warning-text">{problems[0] ?? ""}</p>
          <div className="flex shrink-0 gap-2">
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button loading={save.isPending} disabled={problems.length > 0} onClick={() => save.mutate()}>
              {question ? "Save question" : "Add question"}
            </Button>
          </div>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="min-w-0">
        <span className="block text-label-sm text-text-primary">{label}</span>
        <span className="block text-caption text-text-subtle">{hint}</span>
      </span>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
    </div>
  );
}

function OptionsEditor({
  tiering,
  options,
  onChange,
  onPatch,
}: {
  tiering: boolean;
  options: OptionDraft[];
  onChange: (options: OptionDraft[]) => void;
  onPatch: (uid: string, patch: Partial<OptionDraft>) => void;
}) {
  const presets = tiering ? PRESETS.tiering : PRESETS.due_diligence;
  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <p className="mr-auto font-sans text-label-sm text-text-secondary">Answers</p>
        {presets.map((preset) => (
          <Button key={preset.label} variant="ghost" size="sm" onClick={() => onChange(preset.make())}>
            {preset.label}
          </Button>
        ))}
      </div>

      <div className="overflow-hidden rounded-md border border-border">
        <div className="grid grid-cols-[minmax(0,1fr)_4.5rem_auto_2rem] items-center gap-2 border-b border-border bg-surface-sunken px-2.5 py-1.5 text-caption text-text-subtle">
          <span>Label</span>
          <span>{tiering ? "Points" : "Credit"}</span>
          <span>{tiering ? "Rules" : "Marks"}</span>
          <span className="sr-only">Remove</span>
        </div>
        <ul className="divide-y divide-border">
          {options.map((o) => (
            <li key={o.uid} className="grid grid-cols-[minmax(0,1fr)_4.5rem_auto_2rem] items-center gap-2 px-2.5 py-1.5">
              <input
                aria-label="Answer label"
                value={o.label}
                maxLength={200}
                onChange={(e) => onPatch(o.uid, { label: e.target.value })}
                className="h-8 w-full rounded-sm border border-transparent bg-transparent px-2 text-body-md text-text-primary hover:border-border focus:border-action-accent focus:bg-surface-primary focus:outline-none"
              />
              <input
                aria-label={tiering ? "Points" : "Credit out of 100"}
                type="number"
                min={0}
                max={100}
                value={o.score}
                disabled={o.not_applicable}
                onChange={(e) => onPatch(o.uid, { score: Math.max(0, Math.min(100, Number(e.target.value) || 0)) })}
                className="tabular h-8 w-full rounded-sm border border-border bg-surface-primary px-2 text-body-md text-text-primary focus:border-action-accent focus:outline-none disabled:bg-surface-sunken disabled:text-text-faint"
              />
              <span className="flex items-center gap-1">
                {tiering ? (
                  <Select
                    value={o.min_tier ?? "__none__"}
                    onValueChange={(v) => onPatch(o.uid, { min_tier: v === "__none__" ? null : v })}
                  >
                    <SelectTrigger
                      aria-label="Minimum tier"
                      className="h-8 w-32 whitespace-nowrap text-left text-caption [&>span]:truncate"
                    />
                    <SelectContent>
                      <SelectItem value="__none__">No minimum</SelectItem>
                      {TIERS.filter((t) => t !== "low").map((t) => (
                        <SelectItem key={t} value={t}>
                          Min {TIER_META[t].label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Mark
                    label="Gap"
                    title="Picking this raises a finding"
                    on={o.flag}
                    tone="danger"
                    onClick={() => onPatch(o.uid, { flag: !o.flag })}
                  />
                )}
                <Mark
                  label="N/A"
                  title="Leaves the question out of the score"
                  on={o.not_applicable}
                  onClick={() => onPatch(o.uid, { not_applicable: !o.not_applicable })}
                />
                <Mark
                  label="Note"
                  title="Picking this asks for an explanation"
                  on={o.comment_required}
                  onClick={() => onPatch(o.uid, { comment_required: !o.comment_required })}
                />
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${o.label || "answer"}`}
                disabled={options.length <= 2}
                onClick={() => onChange(options.filter((x) => x.uid !== o.uid))}
              >
                <Icon name="x" className="size-3.5" />
              </Button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          disabled={options.length >= 50}
          onClick={() => onChange([...options, blankOption("", 0)])}
          className="flex w-full items-center gap-2 border-t border-border px-3 py-2 text-label-sm text-action-accent transition-colors duration-80 ease-state hover:bg-surface-hover disabled:text-text-faint"
        >
          <Icon name="plus" className="size-4" />
          Add answer
        </button>
      </div>
      <p className="mt-1.5 text-caption text-text-subtle">
        {tiering
          ? "More points means more risk. A minimum tier applies whatever the total."
          : "100 is full credit. Mark the answers that count as a gap."}
      </p>
    </div>
  );
}

function Mark({
  label,
  title,
  on,
  tone = "accent",
  onClick,
}: {
  label: string;
  title: string;
  on: boolean;
  tone?: "accent" | "danger";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      title={title}
      onClick={onClick}
      className={cn(
        "h-7 rounded-xs border px-1.5 text-caption font-semibold transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-action-accent",
        on
          ? tone === "danger"
            ? "border-status-danger-border bg-status-danger-bg text-status-danger-text"
            : "border-action-accent bg-action-accent-tint text-action-accent"
          : "border-border text-text-subtle hover:bg-surface-hover",
      )}
    >
      {label}
    </button>
  );
}
