import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Gauge,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextArea,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { getFacets, tierEngagement } from "../api";
import type { TieringInput, VendorDetail } from "../types";
import { TIERS, TIERING_FACTORS } from "../types";
import { fmtDate, TIER_META } from "../tokens";
import { Panel } from "./panel";
import { ThresholdRuler } from "./threshold-ruler";

/**
 * Tier is criticality, not health, so the low band is neutral rather than green:
 * a low-tier vendor is not a good vendor, it is one that can hurt you less. The
 * ramp matches `TIER_META` exactly, so the same word is the same colour on the
 * gauge, the ruler, the pill and the register.
 */
const TIER_ZONES = [
  { to: 25, strokeClass: "stroke-status-neutral-base", textClass: "text-status-neutral-text" },
  { to: 50, strokeClass: "stroke-status-pending-base", textClass: "text-status-pending-text" },
  { to: 75, strokeClass: "stroke-status-warning-base", textClass: "text-status-warning-text" },
  { to: 100, strokeClass: "stroke-status-danger-base", textClass: "text-status-danger-text" },
];

/** What each answer on the 0-4 scale actually means, so the form is answerable. */
const SCALE: Record<string, string[]> = {
  data_sensitivity: [
    "No data is shared",
    "Public or non-identifying data",
    "Internal business data",
    "Personal data",
    "Special category, health or payment data",
  ],
  business_criticality: [
    "No business process depends on them",
    "A convenience — work continues without them",
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

const BLANK: Record<string, number> = Object.fromEntries(TIERING_FACTORS.map((k) => [k, 0]));

/**
 * The tiering panel, in the shape the vulnerabilities risk panel proved out:
 * every step of the arithmetic is on screen, in order, so the number is
 * reproducible by eye. A gauge for the outcome, a per-factor table for how it
 * got there, and the bands it is being measured against.
 *
 * The recompute is live. A reviewer changing an answer sees the score and the
 * band move before they commit, which is the difference between a form and a
 * model they can argue with.
 */
export function TieringPanel({
  vendor,
  engagementId,
  canAssess,
  onApply,
}: {
  vendor: VendorDetail;
  engagementId: string | null;
  canAssess: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });

  const latest = useMemo(() => {
    const rows = vendor.tierings.filter(
      (t) => engagementId === null || t.engagement_id === engagementId,
    );
    return rows.length > 0 ? rows.reduce((a, b) => (b.cycle >= a.cycle ? b : a)) : null;
  }, [vendor.tierings, engagementId]);

  const [editing, setEditing] = useState(false);
  const [answers, setAnswers] = useState<Record<string, number>>(BLANK);
  const [overrideTier, setOverrideTier] = useState<string>("");
  const [justification, setJustification] = useState("");

  useEffect(() => {
    if (!editing) return;
    setAnswers(
      latest
        ? Object.fromEntries(latest.factors.map((f) => [f.key, f.answer]))
        : { ...BLANK },
    );
    setOverrideTier(latest?.override_tier ?? "");
    setJustification(latest?.override_justification ?? "");
  }, [editing, latest]);

  const weights = useMemo(() => {
    const specs = facetsQuery.data?.tiering_factors ?? [];
    return Object.fromEntries(specs.map((s) => [s.key, s.weight]));
  }, [facetsQuery.data]);

  // Memoised because it feeds the live-recompute below: a fresh object literal
  // every render would re-run the preview on every keystroke elsewhere.
  const thresholds = useMemo(
    () =>
      facetsQuery.data?.tier_thresholds ??
      latest?.thresholds ?? { critical: 75, high: 50, medium: 25 },
    [facetsQuery.data, latest],
  );

  // The same arithmetic the backend runs, so the preview and the saved result
  // agree: sum(clamp(answer, 0, 4) / 4 * weight) * 100.
  const preview = useMemo(() => {
    const factors = TIERING_FACTORS.map((key) => {
      const clamped = Math.max(0, Math.min(4, answers[key] ?? 0));
      const weight = weights[key] ?? 0;
      return {
        key,
        clamped,
        weight,
        points: (clamped / 4) * weight * 100,
        maxPoints: weight * 100,
      };
    });
    const score = Math.round(factors.reduce((sum, f) => sum + f.points, 0) * 100) / 100;
    const tier =
      score >= (thresholds.critical ?? 75)
        ? "critical"
        : score >= (thresholds.high ?? 50)
          ? "high"
          : score >= (thresholds.medium ?? 25)
            ? "medium"
            : "low";
    return { factors, score, tier };
  }, [answers, weights, thresholds]);

  const save = useMutation({
    mutationFn: () => {
      const body = {
        ...(Object.fromEntries(
          TIERING_FACTORS.map((k) => [k, answers[k] ?? 0]),
        ) as unknown as TieringInput),
        override_tier: overrideTier || null,
        override_justification: overrideTier ? justification.trim() || null : null,
      };
      return tierEngagement(vendor.id, engagementId!, body);
    },
    onSuccess: (next) => {
      onApply(next);
      void queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setEditing(false);
      toast({ title: "Tier recorded", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "tiering"), tone: "danger" }),
  });

  if (!engagementId) {
    return (
      <Panel title="Tiering">
        <p className="text-body-md text-text-secondary">
          Tiering runs per engagement, so this vendor needs one first. One vendor can be critical
          for payroll and low for a marketing pilot.
        </p>
      </Panel>
    );
  }

  if (editing) {
    return (
      <Panel
        title={latest ? "Re-tier this engagement" : "Tier this engagement"}
        description="Five factors, weighted. The score updates as you answer."
        action={
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        }
      >
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
          <div className="shrink-0 lg:w-[19rem]">
            <Gauge
              value={preview.score}
              zones={TIER_ZONES}
              label="Inherent score"
              unit=""
              size={190}
              badge={{
                text: TIER_META[preview.tier]?.label ?? preview.tier,
                toneClass: TIER_ZONES[Math.min(3, Math.floor(preview.score / 25))].textClass,
              }}
            />
            <ThresholdRuler
              className="mt-3"
              score={preview.score}
              thresholds={thresholds}
              effectiveTier={preview.tier}
            />
            {latest && latest.effective_tier !== preview.tier ? (
              <p className="mt-3 flex items-start gap-1.5 rounded-md border border-status-warning-border bg-status-warning-bg p-3 text-body-sm text-status-warning-text">
                <Icon name="alert" className="mt-px size-4 shrink-0" />
                This moves the engagement from {TIER_META[latest.effective_tier]?.label} to{" "}
                {TIER_META[preview.tier]?.label}, which changes which stages it needs and how often
                it is reassessed.
              </p>
            ) : null}
          </div>

          <form
            className="min-w-0 flex-1 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            {TIERING_FACTORS.map((key) => {
              const spec = facetsQuery.data?.tiering_factors.find((f) => f.key === key);
              const value = answers[key] ?? 0;
              return (
                <div key={key}>
                  <div className="flex items-baseline justify-between gap-3">
                    <label
                      htmlFor={`tiering-${key}`}
                      className="font-sans text-label-sm text-text-secondary"
                    >
                      {spec?.label ?? key}
                    </label>
                    <span className="tabular text-caption text-text-subtle">
                      weight {Math.round((spec?.weight ?? 0) * 100)}%
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3">
                    <input
                      id={`tiering-${key}`}
                      type="range"
                      min={0}
                      max={4}
                      step={1}
                      value={value}
                      onChange={(e) =>
                        setAnswers((a) => ({ ...a, [key]: Number(e.target.value) }))
                      }
                      className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-surface-sunken accent-action-accent"
                      aria-describedby={`tiering-${key}-desc`}
                    />
                    <span className="tabular w-8 shrink-0 text-right text-body-md font-semibold text-text-primary">
                      {value}
                    </span>
                  </div>
                  <p id={`tiering-${key}-desc`} className="mt-1 text-body-sm text-text-subtle">
                    {SCALE[key]?.[value] ?? ""}
                  </p>
                </div>
              );
            })}

            <div className="rounded-md border border-border bg-surface-sunken p-3.5">
              <SelectField label="Override the computed tier" optional>
                <Select
                  value={overrideTier || "__none__"}
                  onValueChange={(v) => setOverrideTier(v === "__none__" ? "" : v)}
                >
                  <SelectTrigger aria-label="Override tier" />
                  <SelectContent>
                    <SelectItem value="__none__">Use the computed tier</SelectItem>
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
                  className="mt-3"
                  label="Why the model is wrong here"
                  hint="An override without a reason is unauditable. Say what the five factors miss."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  rows={3}
                  maxLength={4000}
                />
              ) : null}
            </div>

            <div className="flex gap-2">
              <Button
                type="submit"
                loading={save.isPending}
                disabled={Boolean(overrideTier) && !justification.trim()}
              >
                {latest ? "Save the new tier" : "Set the tier"}
              </Button>
              <Button variant="secondary" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            </div>
            {!latest ? (
              <p className="text-caption text-text-subtle">
                Setting the tier lays out the twelve lifecycle stages for this engagement and skips
                the ones this tier does not need.
              </p>
            ) : null}
          </form>
        </div>
      </Panel>
    );
  }

  if (!latest) {
    return (
      <Panel title="Tiering">
        <p className="text-body-md text-text-secondary">
          This engagement has not been tiered. The tier decides how deep the assessment goes, how
          many reviewers sign off, and how often it comes back around — nothing else in the
          lifecycle can start without it.
        </p>
        {canAssess ? (
          <Button className="mt-3" onClick={() => setEditing(true)}>
            Tier this engagement
          </Button>
        ) : (
          <p className="mt-3 text-caption text-text-subtle">
            Tiering needs the Assess vendors permission.
          </p>
        )}
      </Panel>
    );
  }

  const overridden = latest.override_tier !== null;

  return (
    <Panel
      title="Tiering"
      action={
        canAssess ? (
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            Re-tier
          </Button>
        ) : null
      }
    >
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
        <div className="shrink-0 sm:w-[19rem]">
          <Gauge
            value={latest.score}
            zones={TIER_ZONES}
            label="Inherent score"
            unit=""
            size={190}
            badge={{
              text: TIER_META[latest.effective_tier]?.label ?? latest.effective_tier,
              toneClass: TIER_ZONES[Math.min(3, Math.floor(latest.score / 25))].textClass,
            }}
          />
          <ThresholdRuler
            className="mt-3"
            score={latest.score}
            thresholds={latest.thresholds}
            effectiveTier={latest.effective_tier}
            pointsToHigher={latest.points_to_higher_tier}
            pointsToLower={latest.points_to_lower_tier}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill
              status={TIER_META[latest.effective_tier]?.family ?? "neutral"}
              label={`${TIER_META[latest.effective_tier]?.label ?? latest.effective_tier} tier`}
            />
            {overridden ? (
              <Tooltip content={`The model computed ${TIER_META[latest.computed_tier]?.label}`}>
                <span>
                  <Badge variant="countWarn">Overridden</Badge>
                </span>
              </Tooltip>
            ) : null}
            <span className="text-caption text-text-subtle">
              Cycle {latest.cycle}
              {latest.assessed_by_name ? ` · ${latest.assessed_by_name}` : ""}
              {latest.assessed_at ? ` · ${fmtDate(latest.assessed_at)}` : ""}
            </span>
          </div>

          {overridden ? (
            <div className="mt-3 rounded-md border border-status-warning-border bg-status-warning-bg p-3">
              <p className="text-label-sm text-status-warning-text">
                A person set this tier, not the model
              </p>
              <p className="mt-1 text-body-sm text-text-secondary">
                {latest.override_justification || "No reason was recorded."}
              </p>
            </div>
          ) : null}

          <p className="type-overline mt-4">How this was calculated</p>
          <ul className="mt-2 space-y-2.5">
            {latest.factors.map((f) => (
              <li
                key={f.key}
                className="grid grid-cols-[minmax(8rem,11rem)_1fr_auto] items-center gap-3"
              >
                <span className="min-w-0">
                  <span className="block truncate text-body-sm text-text-primary">{f.label}</span>
                  <span className="tabular block text-caption text-text-subtle">
                    {f.clamped} of 4 · weight {Math.round(f.weight * 100)}%
                  </span>
                </span>
                <span
                  className="h-1.5 rounded-full bg-surface-sunken"
                  role="img"
                  aria-label={`${f.points} of ${f.max_points} points`}
                >
                  <span
                    className={cn("block h-1.5 rounded-full bg-action-accent")}
                    // A non-zero contribution must be visible, so floor the width.
                    style={{
                      width: `${f.points === 0 ? 0 : Math.max(2, (f.points / (f.max_points || 1)) * 100)}%`,
                    }}
                  />
                </span>
                <span className="tabular shrink-0 text-body-sm text-text-secondary">
                  {f.points} / {f.max_points}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center justify-between border-t border-border pt-2.5">
            <span className="text-body-sm text-text-secondary">Inherent score</span>
            <span className="tabular text-body-md font-semibold text-text-primary">
              {latest.score} / 100
            </span>
          </div>
        </div>
      </div>
    </Panel>
  );
}
