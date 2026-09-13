import type { IconName } from "@/components/ui";
import type { AnswerValue, BuilderQuestion, EvidenceRule, QuestionOption, QuestionType } from "./types";

/**
 * Questionnaire rules the screen needs before the server answers: which
 * questions are showing, and what a tiering score comes to as it is filled in.
 *
 * Mirrors `scoring.visible_ids` and `scoring.compute_questionnaire_tier`. The
 * server recomputes both on save and is the only one whose number is stored, so
 * this is a live preview, never a source of truth.
 */

export const TYPE_META: Record<QuestionType, { label: string; icon: IconName }> = {
  single_choice: { label: "Single choice", icon: "choiceSingle" },
  multi_choice: { label: "Multiple choice", icon: "choiceMulti" },
  text: { label: "Short text", icon: "textShort" },
  paragraph: { label: "Long text", icon: "textLong" },
  number: { label: "Number", icon: "number" },
  date: { label: "Date", icon: "calendar" },
  file: { label: "File upload", icon: "paperclip" },
};

export const EVIDENCE_LABEL: Record<EvidenceRule, string> = {
  none: "No evidence",
  optional: "Evidence optional",
  required: "Evidence required",
};

export const isChoice = (type: QuestionType) => type === "single_choice" || type === "multi_choice";

export type LogicOption = Pick<QuestionOption, "key" | "label"> &
  Partial<Pick<QuestionOption, "score" | "not_applicable" | "min_tier">>;

export type LogicQuestion = {
  id: string;
  answer_type: QuestionType;
  options: LogicOption[];
  weight?: number;
  condition_question_id: string | null;
  condition_option_keys: string[];
};

export const toLogic = (q: BuilderQuestion): LogicQuestion => ({
  id: q.id,
  answer_type: q.answer_type,
  options: q.options,
  weight: q.weight,
  condition_question_id: q.condition.question_id ?? null,
  condition_option_keys: q.condition.option_keys ?? [],
});

export function pickedKeys(value: AnswerValue | undefined): string[] {
  if (typeof value === "string") return value ? [value] : [];
  if (Array.isArray(value)) return value.filter((v) => typeof v === "string" && v);
  return [];
}

export function isEmpty(value: AnswerValue | undefined): boolean {
  return value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
}

/** In order, so a follow-up can only look back; a hidden parent hides its children. */
export function visibleIds(
  questions: LogicQuestion[],
  values: Record<string, AnswerValue | undefined>,
): Set<string> {
  const shown = new Set<string>();
  for (const q of questions) {
    const parent = q.condition_question_id;
    if (parent) {
      if (!shown.has(parent)) continue;
      const picked = pickedKeys(values[parent]);
      if (!picked.some((k) => q.condition_option_keys.includes(k))) continue;
    }
    shown.add(q.id);
  }
  return shown;
}

const TIER_ORDER = ["critical", "high", "medium", "low"] as const;
const DEFAULT_BANDS: Record<string, number> = { critical: 75, high: 50, medium: 25 };

function worse(a: string | null, b: string | null): string | null {
  if (!a || !b) return a ?? b;
  return TIER_ORDER.indexOf(a as never) <= TIER_ORDER.indexOf(b as never) ? a : b;
}

export function bandFor(score: number, thresholds: Record<string, number>): string {
  for (const tier of ["critical", "high", "medium"]) {
    if (score >= (thresholds[tier] ?? DEFAULT_BANDS[tier])) return tier;
  }
  return "low";
}

export type TierPreview = {
  score: number;
  tier: string;
  bandTier: string;
  floorTier: string | null;
  floorBy: string[];
  /** The most points every shown, scoring question could give, for "+N" hints. */
  ceiling: number;
  points: Record<string, { points: number; max: number; counted: boolean }>;
};

export function previewTier(
  questions: LogicQuestion[],
  values: Record<string, AnswerValue | undefined>,
  thresholds: Record<string, number>,
): TierPreview {
  const shown = visibleIds(questions, values);
  let total = 0;
  let ceiling = 0;
  let possible = 0;
  let floor: string | null = null;
  const floors: { id: string; tier: string }[] = [];
  const points: TierPreview["points"] = {};

  for (const q of questions) {
    const keys = pickedKeys(values[q.id]);
    const picked = q.options.filter((o) => keys.includes(o.key));
    const visible = shown.has(q.id);
    const weight = q.weight ?? 1;
    if (visible) {
      for (const o of picked) {
        if (o.min_tier) {
          floor = worse(floor, o.min_tier);
          floors.push({ id: q.id, tier: o.min_tier });
        }
      }
    }
    const scale = q.options.filter((o) => !o.not_applicable).map((o) => o.score ?? 0);
    const best = scale.length ? Math.max(...scale) : 0;
    if (visible && best > 0) possible += best * weight;
    const scored = picked.filter((o) => !o.not_applicable).map((o) => o.score ?? 0);
    const counted = visible && best > 0 && scored.length > 0;
    const got = counted ? Math.max(...scored) * weight : 0;
    const max = counted ? best * weight : 0;
    total += got;
    ceiling += max;
    points[q.id] = { points: got, max, counted };
  }

  const score = ceiling ? Math.round((total / ceiling) * 10000) / 100 : 0;
  const bandTier = bandFor(score, thresholds);
  const tier = worse(bandTier, floor) ?? bandTier;
  const lifted = tier !== bandTier;
  return {
    score,
    tier,
    bandTier,
    floorTier: lifted ? floor : null,
    floorBy: lifted ? floors.filter((f) => f.tier === floor).map((f) => f.id) : [],
    ceiling: possible,
    points,
  };
}
