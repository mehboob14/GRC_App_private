import { useEffect, useMemo, useState } from "react";
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
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
  TextArea,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { getFacets, tierEngagement } from "../api";
import type { Tiering, TieringInput, VendorDetail } from "../types";
import { TIERS, TIERING_FACTORS } from "../types";
import { fmtDate, TIER_META } from "../tokens";
import { ThresholdRuler } from "./threshold-ruler";
import { TierBadge } from "./tier-badge";

/** What each answer on the 0 to 4 scale means, so the question is answerable. */
const SCALE: Record<string, string[]> = {
  data_sensitivity: [
    "No data is shared",
    "Public or non-identifying data",
    "Internal business data",
    "Personal data",
    "Special category, health or payment data",
  ],
  business_criticality: [
    "Nothing depends on them",
    "A convenience, work continues without them",
    "A team is degraded within days",
    "A revenue or delivery process stops",
    "The business stops",
  ],
  system_access: [
    "No access to our systems",
    "Read-only access to one system",
    "Write access to one system",
    "Access across several systems",
    "Privileged or administrative access",
  ],
  regulatory_scope: [
    "Out of scope for everything",
    "Internal policy only",
    "In scope for one framework",
    "In scope for several frameworks",
    "Named in a regulatory filing or audit",
  ],
  fourth_party_reliance: [
    "No subprocessors",
    "One known subprocessor",
    "Several, all declared",
    "Several, some undeclared",
    "Unknown or unmanaged chain",
  ],
};

const DEFAULT_THRESHOLDS = { critical: 75, high: 50, medium: 25 };

/**
 * Unanswered, not zero. Seeding every factor to 0 made the form arrive at a
 * confident Low with a live submit button, and one click skipped four stages
 * "by policy".
 */
type Answers = Record<string, number | null>;
const BLANK: Answers = Object.fromEntries(TIERING_FACTORS.map((k) => [k, null]));

/** The five factors come first, then the optional override. */
const OVERRIDE_STEP = TIERING_FACTORS.length;

function tierFor(score: number, thresholds: Record<string, number>): string {
  if (score >= (thresholds.critical ?? 75)) return "critical";
  if (score >= (thresholds.high ?? 50)) return "high";
  if (score >= (thresholds.medium ?? 25)) return "medium";
  return "low";
}

/**
 * Tiering as a focused popup: one factor at a time on the right, every answer
 * and the live score on the left.
 *
 * Inline, the form stacked twenty-five radios under the lifecycle and pushed
 * everything else off screen. Here each question fits without scrolling, the
 * list on the left is how a reviewer jumps back to change an answer, and closing
 * the dialog keeps the answers so it can be finished later.
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
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });

  const [draftFor, setDraftFor] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answers>(BLANK);
  const [overrideTier, setOverrideTier] = useState("");
  const [justification, setJustification] = useState("");
  const [step, setStep] = useState(0);

  // Seed on the way in, and only when there is no unsaved draft for this
  // engagement. Closing the dialog means "finish later", not "throw it away".
  useEffect(() => {
    if (!open || draftFor === engagementId) return;
    const seeded: Answers = latest
      ? Object.fromEntries(latest.factors.map((f) => [f.key, f.answer]))
      : { ...BLANK };
    setAnswers(seeded);
    setOverrideTier(latest?.override_tier ?? "");
    setJustification(latest?.override_justification ?? "");
    setStep(0);
    setDraftFor(engagementId);
    // Reseeding on every `latest` identity change would wipe a half-filled form
    // whenever anything else on the page wrote.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, engagementId]);

  const specs = useMemo(() => facetsQuery.data?.tiering_factors ?? [], [facetsQuery.data]);
  const weights = useMemo(() => Object.fromEntries(specs.map((s) => [s.key, s.weight])), [specs]);
  const thresholds = facetsQuery.data?.tier_thresholds ?? latest?.thresholds ?? DEFAULT_THRESHOLDS;

  const answered = TIERING_FACTORS.filter((k) => answers[k] !== null).length;
  const complete = answered === TIERING_FACTORS.length;

  // The same arithmetic the backend runs: sum(clamp(answer, 0, 4) / 4 * weight) * 100.
  const score =
    Math.round(
      TIERING_FACTORS.reduce(
        (sum, k) => sum + (Math.max(0, Math.min(4, answers[k] ?? 0)) / 4) * (weights[k] ?? 0) * 100,
        0,
      ) * 100,
    ) / 100;
  const computed = tierFor(score, thresholds);
  const effective = overrideTier || computed;
  const needsReason = Boolean(overrideTier) && !justification.trim();

  const save = useMutation({
    mutationFn: () => {
      const body = {
        ...(Object.fromEntries(
          TIERING_FACTORS.map((k) => [k, answers[k] ?? 0]),
        ) as unknown as TieringInput),
        override_tier: overrideTier || null,
        override_justification: overrideTier ? justification.trim() || null : null,
      };
      return tierEngagement(vendor.id, engagementId, body);
    },
    onSuccess: (next) => {
      onApply(next);
      void queryClient.invalidateQueries({ queryKey: ["vendor-summary"] });
      setDraftFor(null);
      onOpenChange(false);
      toast({ title: `Tier set to ${TIER_META[effective]?.label ?? effective}`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "tiering"), tone: "danger" }),
  });

  const pick = (factor: string, value: number, wasUnanswered: boolean) => {
    setAnswers((a) => ({ ...a, [factor]: value }));
    // The first pass moves on by itself. Changing an earlier answer stays put,
    // so the reviewer sees what they changed.
    if (wasUnanswered) {
      window.setTimeout(() => setStep((s) => Math.min(s + 1, OVERRIDE_STEP)), 160);
    }
  };

  const factor = TIERING_FACTORS[step];
  const spec = specs.find((s) => s.key === factor);
  const weight = factor ? (weights[factor] ?? 0) : 0;
  const engagement = vendor.engagements.find((e) => e.id === engagementId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[min(40rem,90vh)]">
        <DialogHeader>
          <DialogTitle>
            {latest ? "Re-tier" : "Tier"} {engagement?.name ?? vendor.name}
          </DialogTitle>
          <DialogDescription>Five questions. The tier sets stages and reviewers.</DialogDescription>
        </DialogHeader>

        <DialogBody>
          <div className="grid gap-5 sm:grid-cols-[13rem_1fr]">
            <div className="space-y-3">
              <ol className="space-y-0.5" aria-label="Factors">
                {TIERING_FACTORS.map((k, index) => {
                  const value = answers[k];
                  return (
                    <li key={k}>
                      <StepButton
                        active={step === index}
                        done={value !== null}
                        onClick={() => setStep(index)}
                        label={specs.find((s) => s.key === k)?.label ?? k}
                        meta={value !== null ? `${value}/4` : undefined}
                      />
                    </li>
                  );
                })}
                <li>
                  <StepButton
                    active={step === OVERRIDE_STEP}
                    done={Boolean(overrideTier)}
                    onClick={() => setStep(OVERRIDE_STEP)}
                    label="Override"
                    meta={overrideTier ? TIER_META[overrideTier]?.label : "Optional"}
                  />
                </li>
              </ol>

              <div className="rounded-md bg-surface-sunken p-3">
                {complete ? (
                  <>
                    <div className="flex items-center justify-between gap-2">
                      <span className="tabular font-display text-numeral-md text-text-primary">
                        {score}
                      </span>
                      <TierBadge tier={effective} />
                    </div>
                    <ThresholdRuler
                      className="mt-1"
                      hideScore
                      score={score}
                      thresholds={thresholds}
                      effectiveTier={computed}
                    />
                    {latest && latest.effective_tier !== effective ? (
                      <p className="mt-2 flex items-center gap-1.5 text-caption font-semibold text-status-warning-text">
                        <Icon name="alert" className="size-3.5 shrink-0" />
                        Changes from {TIER_META[latest.effective_tier]?.label}
                      </p>
                    ) : null}
                  </>
                ) : (
                  <>
                    <p className="text-label-sm text-text-secondary">
                      {answered} of {TIERING_FACTORS.length} answered
                    </p>
                    <span className="mt-2 flex gap-1" aria-hidden>
                      {TIERING_FACTORS.map((k) => (
                        <span
                          key={k}
                          className={cn(
                            "h-1.5 flex-1 rounded-full",
                            answers[k] !== null ? "bg-action-accent" : "bg-border",
                          )}
                        />
                      ))}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="min-w-0">
              {factor ? (
                <>
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="font-display text-title-md text-text-primary">
                      {spec?.label ?? factor}
                    </h3>
                    <span className="tabular shrink-0 text-caption text-text-subtle">
                      {Math.round(weight * 100)}% of score
                    </span>
                  </div>
                  <RadioGroupPrimitive.Root
                    className="mt-3 space-y-1.5"
                    value={answers[factor] === null ? "" : String(answers[factor])}
                    onValueChange={(v) => setAnswers((a) => ({ ...a, [factor]: Number(v) }))}
                    aria-label={spec?.label ?? factor}
                  >
                    {(SCALE[factor] ?? []).map((sentence, value) => (
                      <RadioGroupPrimitive.Item
                        key={value}
                        value={String(value)}
                        onClick={() => pick(factor, value, answers[factor] === null)}
                        className={cn(
                          "group flex w-full items-center gap-3 rounded-md border border-border px-3 py-2.5 text-left",
                          "transition-colors duration-80 ease-state hover:bg-surface-hover",
                          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                          "data-[state=checked]:border-action-accent data-[state=checked]:bg-action-accent-tint",
                        )}
                      >
                        <span className="tabular grid size-6 shrink-0 place-items-center rounded-full bg-surface-sunken text-caption font-bold text-text-secondary group-data-[state=checked]:bg-action-accent group-data-[state=checked]:text-white">
                          {value}
                        </span>
                        <span className="min-w-0 flex-1 text-body-md text-text-primary">
                          {sentence}
                        </span>
                        <span className="tabular shrink-0 text-caption text-text-subtle">
                          +{Math.round((value / 4) * weight * 100)}
                        </span>
                      </RadioGroupPrimitive.Item>
                    ))}
                  </RadioGroupPrimitive.Root>
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
                        hint="Required. Say what the five factors miss."
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
        </DialogBody>

        <DialogFooter className="justify-between">
          <Button
            variant="ghost"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
          >
            <Icon name="arrowl" className="size-4" />
            Back
          </Button>
          <div className="flex gap-2">
            {step < OVERRIDE_STEP ? (
              <Button variant="secondary" onClick={() => setStep((s) => s + 1)}>
                Next
                <Icon name="arrowr" className="size-4" />
              </Button>
            ) : null}
            <Button
              loading={save.isPending}
              disabled={!complete || needsReason}
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
      className={cn(
        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        active ? "bg-action-accent-tint" : "hover:bg-surface-hover",
      )}
    >
      <span
        className={cn(
          "grid size-4 shrink-0 place-items-center rounded-full",
          done ? "bg-status-success-base text-white" : "border-1.5 border-border-strong",
        )}
        aria-hidden
      >
        {done ? <Icon name="check" className="size-2.5" /> : null}
      </span>
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-body-sm",
          active ? "font-semibold text-text-primary" : "text-text-secondary",
        )}
      >
        {label}
      </span>
      {meta ? <span className="tabular shrink-0 text-caption text-text-subtle">{meta}</span> : null}
    </button>
  );
}

/**
 * The saved tier, compact: score and tier on one line, the bands, then each
 * factor's contribution. Everything on it is reproducible by eye.
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
  return (
    <div className="rounded-md border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="tabular font-display text-numeral-md text-text-primary">
            {latest.score}
          </span>
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
        </div>
        <div className="flex items-center gap-3">
          <span className="text-caption text-text-subtle">
            {[latest.assessed_by_name, fmtDate(latest.assessed_at)].filter(Boolean).join(" · ")}
          </span>
          {canAssess ? (
            <Button variant="secondary" size="sm" onClick={onRetier}>
              Re-tier
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-3 grid gap-5 md:grid-cols-[minmax(0,17rem)_1fr]">
        <ThresholdRuler
          score={latest.score}
          thresholds={latest.thresholds}
          effectiveTier={latest.computed_tier}
          pointsToHigher={latest.points_to_higher_tier}
        />
        <ul className="space-y-2 self-center">
          {latest.factors.map((f) => (
            <li
              key={f.key}
              className="grid grid-cols-[minmax(6rem,9rem)_1fr_2.75rem] items-center gap-3"
            >
              <span className="truncate text-body-sm text-text-secondary">{f.label}</span>
              <span
                className="h-1.5 rounded-full bg-surface-sunken"
                role="img"
                aria-label={`${f.points} of ${f.max_points} points`}
              >
                <span
                  className="block h-1.5 rounded-full bg-action-accent"
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
      </div>
    </div>
  );
}
