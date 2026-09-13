import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
} from "@/components/ui";
import { pickedKeys, previewTier, toLogic, visibleIds } from "../questionnaire-logic";
import type { AnswerValue, Questionnaire } from "../types";
import { TIER_META } from "../tokens";
import { QuestionField } from "./question-field";
import { ThresholdRuler } from "./threshold-ruler";
import { TierBadge } from "./tier-badge";

/**
 * The questionnaire as whoever answers it will see it, with follow-ups opening
 * as answers are picked. Nothing here is saved. For tiering, the score and tier
 * move with every answer, so the scoring can be checked before it is used.
 */
export function QuestionnairePreviewDialog({
  open,
  onOpenChange,
  questionnaire,
  workspaceThresholds,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  questionnaire: Questionnaire;
  workspaceThresholds: Record<string, number>;
}) {
  const [values, setValues] = useState<Record<string, AnswerValue>>({});
  const tiering = questionnaire.purpose === "tiering";
  const logic = useMemo(() => questionnaire.questions.map(toLogic), [questionnaire.questions]);
  const shown = visibleIds(logic, values);
  const thresholds = Object.keys(questionnaire.tier_thresholds).length
    ? questionnaire.tier_thresholds
    : workspaceThresholds;
  const preview = tiering ? previewTier(logic, values, thresholds) : null;
  const asked = questionnaire.questions.filter((q) => shown.has(q.id));

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setValues({});
        onOpenChange(next);
      }}
    >
      <DialogContent size="lg" scrollBody className="max-h-[min(48rem,92vh)]">
        <DialogHeader>
          <DialogTitle>Preview</DialogTitle>
        </DialogHeader>

        {preview ? (
          <div className="border-b border-border px-5 pb-3">
            <div className="mb-1 flex items-center gap-3">
              <span className="tabular font-display text-numeral-md text-text-primary">{preview.score}</span>
              <TierBadge tier={preview.tier} label={`${TIER_META[preview.tier]?.label ?? preview.tier} tier`} />
              {preview.floorTier ? <Badge variant="countWarn">Minimum applied</Badge> : null}
            </div>
            <ThresholdRuler score={preview.score} thresholds={thresholds} effectiveTier={preview.bandTier} />
          </div>
        ) : null}

        <DialogBody className="space-y-5">
          {asked.map((q, index) => {
            const previous = asked[index - 1];
            const needsNote = q.options.some((o) => o.comment_required && pickedKeys(values[q.id]).includes(o.key));
            return (
              <div key={q.id}>
                {!previous || previous.section !== q.section ? (
                  <h3 className="mb-3 border-b border-border pb-1.5 font-display text-title-md text-text-primary">
                    {q.section}
                  </h3>
                ) : null}
                <p className="text-body-lg text-text-primary">
                  {q.prompt}
                  {q.required ? null : <span className="ml-1.5 text-caption text-text-faint">Optional</span>}
                </p>
                {q.help_text ? <p className="mt-0.5 text-body-sm text-text-subtle">{q.help_text}</p> : null}
                <div className="mt-2">
                  {q.answer_type === "file" ? (
                    <span className="inline-flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-body-sm text-text-subtle">
                      <Icon name="upload" className="size-4" />
                      The vendor uploads a document here
                    </span>
                  ) : (
                    <QuestionField
                      label={q.prompt}
                      type={q.answer_type}
                      options={q.options}
                      value={values[q.id]}
                      onCommit={(value) => setValues((v) => ({ ...v, [q.id]: value }))}
                      optionMeta={
                        tiering && preview?.ceiling
                          ? (o) => {
                              const score = q.options.find((x) => x.key === o.key)?.score ?? 0;
                              return `+${Math.round(((score * q.weight) / preview.ceiling) * 100)}`;
                            }
                          : undefined
                      }
                    />
                  )}
                </div>
                {needsNote ? (
                  <p className="mt-2 text-caption text-status-warning-text">This answer asks for a note.</p>
                ) : null}
                {!tiering && q.evidence !== "none" && q.answer_type !== "file" ? (
                  <p className="mt-2 flex items-center gap-1.5 text-caption text-text-subtle">
                    <Icon name="paperclip" className="size-3.5" />
                    {q.evidence === "required" ? "Asks for a supporting document" : "A document can be attached"}
                  </p>
                ) : null}
              </div>
            );
          })}
        </DialogBody>

        <DialogFooter className="justify-between">
          <span className="text-caption text-text-subtle">
            {asked.length} of {questionnaire.question_count} questions showing
          </span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setValues({})}>
              Clear answers
            </Button>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
