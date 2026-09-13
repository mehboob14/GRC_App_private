import { useEffect, useMemo, useState } from "react";
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
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  TextArea,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { getFacets, getQuestionnaire, listQuestionnaires, tierEngagement } from "../api";
import { isEmpty, pickedKeys, previewTier, toLogic, visibleIds } from "../questionnaire-logic";
import type { AnswerValue, Tiering, TieringAnswer, VendorDetail } from "../types";
import { TIERS } from "../types";
import { fmtDate, TIER_META } from "../tokens";
import { QuestionField } from "./question-field";
import { ThresholdRuler } from "./threshold-ruler";
import { TierBadge } from "./tier-badge";

const DEFAULT_THRESHOLDS = { critical: 75, high: 50, medium: 25 };
const OVERRIDE = "__override__";

/**
 * Tiering as a focused popup, driven by the tenant's own tiering questionnaire:
 * one question at a time on the right, every question and the live score on
 * the left. Follow-up questions appear as the answers that open them are picked.
 *
 * Closing keeps the answers so the tiering can be finished later. The score here
 * is a preview; the server scores the same answers again and stores its number.
 */
export function TieringDialog({
  open,
  onOpenChange,
  vendor,
  engagementId,
  latest,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor: VendorDetail;
  engagementId: string;
  latest: Tiering | null;
  onApply: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets, enabled: open });
  const list = useQuery({
    queryKey: ["vendor-questionnaires", "tiering"],
    queryFn: () => listQuestionnaires("tiering"),
    enabled: open,
  });
  const fallback = list.data?.find((q) => q.is_default) ?? list.data?.[0];

  const [chosenId, setChosenId] = useState<string | null>(null);
  const questionnaireId =
    chosenId ??
    (latest?.questionnaire_id && list.data?.some((q) => q.id === latest.questionnaire_id)
      ? latest.questionnaire_id
      : (fallback?.id ?? null));
  const detail = useQuery({
    queryKey: ["vendor-questionnaire", questionnaireId],
    queryFn: () => getQuestionnaire(questionnaireId!),
    enabled: open && Boolean(questionnaireId),
  });
  const questionnaire = detail.data;

  const [draftFor, setDraftFor] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, AnswerValue>>({});
  const [comments, setComments] = useState<Record<string, string>>({});
  const [overrideTier, setOverrideTier] = useState("");
  const [justification, setJustification] = useState("");
  const [step, setStep] = useState<string | null>(null);

  // Seed once per engagement and questionnaire. Closing means "finish later",
  // so an unsaved draft for the same pair is kept rather than overwritten.
  const draftKey = questionnaire ? `${engagementId}:${questionnaire.id}` : null;
  useEffect(() => {
    if (!open || !questionnaire || draftFor === draftKey) return;
    const stored = latest?.questionnaire_id === questionnaire.id ? latest.answers : {};
    setValues(Object.fromEntries(Object.entries(stored).map(([k, v]) => [k, v.value])));
    setComments(Object.fromEntries(Object.entries(stored).map(([k, v]) => [k, v.comment ?? ""])));
    setOverrideTier(latest?.override_tier ?? "");
    setJustification(latest?.override_justification ?? "");
    setStep(null);
    setDraftFor(draftKey);
    // Reseeding on every `latest` identity change would wipe a half-filled form
    // whenever anything else on the page wrote.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, draftKey]);

  const questions = useMemo(() => questionnaire?.questions ?? [], [questionnaire]);
  const logic = useMemo(() => questions.map(toLogic), [questions]);
  const shown = visibleIds(logic, values);
  const asked = questions.filter((q) => shown.has(q.id));
  const thresholds =
    questionnaire && Object.keys(questionnaire.tier_thresholds).length
      ? questionnaire.tier_thresholds
      : (facetsQuery.data?.tier_thresholds ?? latest?.thresholds ?? DEFAULT_THRESHOLDS);
  const preview = previewTier(logic, values, thresholds);

  const needsNote = (id: string) => {
    const q = questions.find((x) => x.id === id);
    return Boolean(q?.options.some((o) => o.comment_required && pickedKeys(values[id]).includes(o.key)));
  };
  const answered = (id: string) => !isEmpty(values[id]);
  const done = (id: string) => answered(id) && (!needsNote(id) || Boolean(comments[id]?.trim()));
  const missing = asked.filter((q) => (q.required && !answered(q.id)) || (answered(q.id) && !done(q.id)));
  const complete = asked.length > 0 && missing.length === 0;
  const anyAnswer = asked.some((q) => answered(q.id));

  const computed = preview.tier;
  const effective = overrideTier || computed;
  const needsReason = Boolean(overrideTier) && !justification.trim();

  const current = step === OVERRIDE ? null : (asked.find((q) => q.id === step) ?? asked[0] ?? null);
  const currentIndex = current ? asked.indexOf(current) : asked.length;
  const goTo = (index: number) =>
    setStep(index >= asked.length ? OVERRIDE : (asked[Math.max(0, index)]?.id ?? null));

  const save = useMutation({
    mutationFn: () => {
      const answers: Record<string, TieringAnswer> = {};
      for (const q of asked) {
        if (!answered(q.id)) continue;
        const note = comments[q.id]?.trim();
        answers[q.id] = note ? { value: values[q.id], comment: note } : { value: values[q.id] };
      }
      return tierEngagement(vendor.id, engagementId, {
        questionnaire_id: questionnaire!.id,
        answers,
        override_tier: overrideTier || null,
        override_justification: overrideTier ? justification.trim() || null : null,
      });
    },
    onSuccess: (next) => {
      onApply(next);
      void queryClient.invalidateQueries({ queryKey: ["vendor-summary"] });
      setDraftFor(null);
      onOpenChange(false);
      const saved = next.tierings.find((t) => t.engagement_id === engagementId);
      const tier = saved?.effective_tier ?? effective;
      toast({ title: `Tier set to ${TIER_META[tier]?.label ?? tier}`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "tiering"), tone: "danger" }),
  });

  const commit = (id: string, value: AnswerValue, firstPick: boolean) => {
    setValues((v) => ({ ...v, [id]: value }));
    // A first single choice moves on by itself; changing an answer stays put.
    if (firstPick) window.setTimeout(() => goTo(currentIndex + 1), 160);
  };

  const engagement = vendor.engagements.find((e) => e.id === engagementId);
  const sectionCount = new Set(asked.map((q) => q.section)).size;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[min(44rem,92vh)]">
        <DialogHeader>
          <DialogTitle>
            {latest ? "Re-tier" : "Tier"} {engagement?.name ?? vendor.name}
          </DialogTitle>
          <DialogDescription>
            {questionnaire
              ? `${asked.length} ${asked.length === 1 ? "question" : "questions"} from ${questionnaire.name}. The tier sets stages and reviewers.`
              : "The tier sets stages and reviewers."}
          </DialogDescription>
        </DialogHeader>

        <DialogBody>
          {list.isSuccess && !fallback ? (
            <p className="rounded-md bg-status-warning-bg px-3 py-2.5 text-body-sm text-status-warning-text">
              There is no tiering questionnaire yet. Build one under Vendors, Questionnaires.
            </p>
          ) : !questionnaire ? (
            <Skeleton className="h-72" />
          ) : (
            <>
              <div className="rounded-md border border-border p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                  {anyAnswer ? (
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="tabular font-display text-numeral-md text-text-primary">
                        {preview.score}
                      </span>
                      <TierBadge tier={effective} label={`${TIER_META[effective]?.label ?? effective} tier`} />
                      {overrideTier ? <Badge variant="countWarn">Overridden</Badge> : null}
                      {preview.floorTier && !overrideTier ? (
                        <Tooltip content="An answer sets a minimum tier, whatever the score.">
                          <span>
                            <Badge variant="countWarn">Minimum {TIER_META[preview.floorTier]?.label}</Badge>
                          </span>
                        </Tooltip>
                      ) : null}
                      {latest && latest.effective_tier !== effective ? (
                        <span className="flex items-center gap-1 text-caption font-semibold text-status-warning-text">
                          <Icon name="alert" className="size-3.5 shrink-0" />
                          Changes from {TIER_META[latest.effective_tier]?.label}
                        </span>
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-label-md text-text-secondary">Answer to see the tier</p>
                  )}
                  <div className="flex items-center gap-3">
                    <span className="tabular text-caption text-text-subtle">
                      {asked.filter((q) => done(q.id)).length}/{asked.length}
                    </span>
                    {(list.data?.length ?? 0) > 1 ? (
                      <Select value={questionnaire.id} onValueChange={(id) => setChosenId(id)}>
                        <SelectTrigger
                          aria-label="Questionnaire"
                          className="h-8 w-48 text-left text-body-sm [&>span]:truncate"
                        />
                        <SelectContent>
                          {list.data?.map((q) => (
                            <SelectItem key={q.id} value={q.id}>
                              {q.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : null}
                  </div>
                </div>
                <ThresholdRuler
                  score={anyAnswer ? preview.score : null}
                  thresholds={thresholds}
                  effectiveTier={anyAnswer ? preview.bandTier : null}
                />
              </div>

              <div className="mt-4 grid gap-5 sm:grid-cols-[13.5rem_minmax(0,1fr)]">
                <ol className="max-h-[22rem] space-y-0.5 self-start overflow-y-auto pr-1" aria-label="Questions">
                  {asked.map((q, index) => {
                    const previous = asked[index - 1];
                    const labels = q.options
                      .filter((o) => pickedKeys(values[q.id]).includes(o.key))
                      .map((o) => o.label);
                    return (
                      <li key={q.id}>
                        {sectionCount > 1 && previous?.section !== q.section ? (
                          <p className="type-overline mt-2 px-2 pb-0.5">{q.section}</p>
                        ) : null}
                        <StepButton
                          active={current?.id === q.id}
                          done={done(q.id)}
                          onClick={() => setStep(q.id)}
                          label={q.prompt}
                          meta={labels.length ? labels.join(", ") : q.required ? undefined : "Optional"}
                        />
                      </li>
                    );
                  })}
                  <li className="mt-1 border-t border-border pt-1">
                    <StepButton
                      active={step === OVERRIDE}
                      done={Boolean(overrideTier)}
                      onClick={() => setStep(OVERRIDE)}
                      label="Override"
                      meta={overrideTier ? TIER_META[overrideTier]?.label : "Optional"}
                    />
                  </li>
                </ol>

                <div className="min-w-0">
                  {current ? (
                    <>
                      <p className="type-overline">
                        {current.section} · {currentIndex + 1} of {asked.length}
                      </p>
                      <h3 className="mt-1 font-display text-title-md text-text-primary">{current.prompt}</h3>
                      {current.help_text ? (
                        <p className="mt-1 text-body-sm text-text-subtle">{current.help_text}</p>
                      ) : null}
                      <div className="mt-3">
                        <QuestionField
                          key={current.id}
                          label={current.prompt}
                          type={current.answer_type}
                          options={current.options}
                          layout="cards"
                          value={values[current.id]}
                          onCommit={(value) =>
                            commit(
                              current.id,
                              value,
                              current.answer_type === "single_choice" && !answered(current.id),
                            )
                          }
                          optionMeta={
                            preview.ceiling
                              ? (o) => {
                                  const score = current.options.find((x) => x.key === o.key)?.score ?? 0;
                                  return `+${Math.round(((score * current.weight) / preview.ceiling) * 100)}`;
                                }
                              : undefined
                          }
                        />
                      </div>
                      {needsNote(current.id) ? (
                        <div className="mt-3">
                          <TextArea
                            label="Note"
                            hint="Required for this answer."
                            value={comments[current.id] ?? ""}
                            onChange={(e) => setComments((c) => ({ ...c, [current.id]: e.target.value }))}
                            rows={2}
                            maxLength={4000}
                          />
                        </div>
                      ) : null}
                      {current.options.some((o) => o.min_tier) ? (
                        <p className="mt-3 flex items-center gap-1.5 text-caption text-text-subtle">
                          <Icon name="gauge" className="size-3.5" />
                          Some answers set a minimum tier.
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <h3 className="font-display text-title-md text-text-primary">Override</h3>
                      <p className="mt-1 text-body-sm text-text-subtle">
                        Computed tier is {TIER_META[computed]?.label}.
                      </p>
                      <div className="mt-4 space-y-3">
                        <SelectField label="Tier">
                          <Select
                            value={overrideTier || "__none__"}
                            onValueChange={(v) => setOverrideTier(v === "__none__" ? "" : v)}
                          >
                            <SelectTrigger aria-label="Override tier" />
                            <SelectContent>
                              <SelectItem value="__none__">Use computed tier</SelectItem>
                              {TIERS.map((t) => (
                                <SelectItem key={t} value={t}>
                                  {TIER_META[t].label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </SelectField>
                        {overrideTier ? (
                          <TextArea
                            label="Reason"
                            hint="Required. Say what the answers miss."
                            value={justification}
                            onChange={(e) => setJustification(e.target.value)}
                            rows={3}
                            maxLength={4000}
                          />
                        ) : null}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </DialogBody>

        <DialogFooter className="justify-between">
          <Button
            variant="ghost"
            disabled={currentIndex === 0 || !questionnaire}
            onClick={() => goTo(currentIndex - 1)}
          >
            <Icon name="arrowl" className="size-4" />
            Back
          </Button>
          <div className="flex items-center gap-2">
            {questionnaire && missing.length ? (
              <span className="hidden text-caption text-text-subtle sm:inline">{missing.length} to answer</span>
            ) : null}
            {step !== OVERRIDE && questionnaire ? (
              <Button variant="secondary" onClick={() => goTo(currentIndex + 1)}>
                Next
                <Icon name="arrowr" className="size-4" />
              </Button>
            ) : null}
            <Button
              loading={save.isPending}
              disabled={!questionnaire || !complete || needsReason}
              onClick={() => save.mutate()}
            >
              {latest ? "Save tier" : "Set tier"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StepButton({
  active,
  done,
  label,
  meta,
  onClick,
}: {
  active: boolean;
  done: boolean;
  label: string;
  meta?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "step" : undefined}
      title={label}
      className={cn(
        "flex w-full items-start gap-2 rounded-sm px-2 py-1.5 text-left transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        active ? "bg-action-accent-tint" : "hover:bg-surface-hover",
      )}
    >
      <span
        className={cn(
          "mt-0.5 grid size-4 shrink-0 place-items-center rounded-full",
          done ? "bg-status-success-base text-white" : "border-1.5 border-border-strong",
        )}
        aria-hidden
      >
        {done ? <Icon name="check" className="size-2.5" /> : null}
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn("block truncate text-body-sm", active ? "font-semibold text-text-primary" : "text-text-secondary")}
        >
          {label}
        </span>
        {meta ? <span className="block truncate text-caption text-text-subtle">{meta}</span> : null}
      </span>
    </button>
  );
}

/**
 * The saved tier, compact: score and tier on one line, the bands, then what
 * each answer put in. Everything on it is reproducible by eye.
 */
export function TierSummary({
  latest,
  canAssess,
  onRetier,
}: {
  latest: Tiering;
  canAssess: boolean;
  onRetier: () => void;
}) {
  const overridden = latest.override_tier !== null;
  const lines = latest.questions.filter((q) => q.answer_labels.length > 0);
  return (
    <div className="rounded-md border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="tabular font-display text-numeral-md text-text-primary">{latest.score}</span>
          <TierBadge tier={latest.effective_tier} />
          {overridden ? (
            <Tooltip
              content={`Computed ${TIER_META[latest.computed_tier]?.label}. ${latest.override_justification ?? ""}`}
            >
              <span>
                <Badge variant="countWarn">Overridden</Badge>
              </span>
            </Tooltip>
          ) : null}
          {latest.floor_tier ? (
            <Badge variant="countWarn">Minimum {TIER_META[latest.floor_tier]?.label} from an answer</Badge>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-caption text-text-subtle">
            {[latest.questionnaire_name, latest.assessed_by_name, fmtDate(latest.assessed_at)]
              .filter(Boolean)
              .join(" · ")}
          </span>
          {canAssess ? (
            <Button variant="secondary" size="sm" onClick={onRetier}>
              Re-tier
            </Button>
          ) : null}
        </div>
      </div>

      <ThresholdRuler
        className="mt-3"
        score={latest.score}
        thresholds={latest.thresholds}
        effectiveTier={latest.computed_tier}
        pointsToHigher={latest.points_to_higher_tier}
      />

      {lines.length ? (
        <ul className="mt-4 grid gap-x-8 gap-y-3 border-t border-border pt-4 sm:grid-cols-2">
          {lines.map((line) => (
            <li key={line.id} className="grid grid-cols-[minmax(0,1fr)_4.5rem_2.75rem] items-center gap-3">
              <span className="min-w-0">
                <span className="block truncate text-body-sm text-text-secondary" title={line.prompt}>
                  {line.prompt}
                </span>
                <span className="block truncate text-caption text-text-subtle">
                  {line.answer_labels.join(", ")}
                </span>
              </span>
              {line.counted ? (
                <>
                  <span
                    className="h-2 rounded-full bg-surface-sunken"
                    role="img"
                    aria-label={`${line.points} of ${line.max_points} points`}
                  >
                    <span
                      className="block h-2 rounded-full bg-action-accent"
                      style={{
                        width: `${line.points === 0 ? 0 : Math.max(3, (line.points / (line.max_points || 1)) * 100)}%`,
                      }}
                    />
                  </span>
                  <span className="tabular text-right text-caption text-text-subtle">
                    {line.points}/{line.max_points}
                  </span>
                </>
              ) : (
                <span className="col-span-2 text-right text-caption text-text-faint">Not scored</span>
              )}
            </li>
          ))}
        </ul>
      ) : latest.factors.length ? (
        <ul className="mt-4 grid gap-x-8 gap-y-2.5 border-t border-border pt-4 sm:grid-cols-2">
          {latest.factors.map((f) => (
            <li key={f.key} className="grid grid-cols-[minmax(6rem,9rem)_1fr_2.75rem] items-center gap-3">
              <span className="truncate text-body-sm text-text-secondary">{f.label}</span>
              <span
                className="h-2 rounded-full bg-surface-sunken"
                role="img"
                aria-label={`${f.points} of ${f.max_points} points`}
              >
                <span
                  className="block h-2 rounded-full bg-action-accent"
                  style={{
                    width: `${f.points === 0 ? 0 : Math.max(3, (f.points / (f.max_points || 1)) * 100)}%`,
                  }}
                />
              </span>
              <span className="tabular text-right text-caption text-text-subtle">
                {f.points}/{f.max_points}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
