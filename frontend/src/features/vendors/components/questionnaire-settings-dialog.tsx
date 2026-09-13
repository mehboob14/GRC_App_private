import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Switch,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { updateQuestionnaire } from "../api";
import { TIERS, type Questionnaire } from "../types";
import { TIER_META } from "../tokens";
import { ThresholdRuler } from "./threshold-ruler";
import { TierBadge } from "./tier-badge";

const BANDS = ["medium", "high", "critical"] as const;

/**
 * Name and use. Tiering sets whether this is the questionnaire the tiering
 * dialog opens with, and where each tier starts; due diligence sets which tiers
 * it is sent to by default.
 */
export function QuestionnaireSettingsDialog({
  open,
  onOpenChange,
  questionnaire,
  workspaceThresholds,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  questionnaire: Questionnaire;
  workspaceThresholds: Record<string, number>;
  onSaved: (next: Questionnaire) => void;
}) {
  const { toast } = useToast();
  const tiering = questionnaire.purpose === "tiering";
  const [name, setName] = useState(questionnaire.name);
  const [description, setDescription] = useState(questionnaire.description ?? "");
  const [isDefault, setIsDefault] = useState(questionnaire.is_default);
  const [tiers, setTiers] = useState<string[]>(questionnaire.default_tiers);
  const [custom, setCustom] = useState(Object.keys(questionnaire.tier_thresholds).length > 0);
  const [bands, setBands] = useState<Record<string, number>>({
    ...workspaceThresholds,
    ...questionnaire.tier_thresholds,
  });

  useEffect(() => {
    if (!open) return;
    setName(questionnaire.name);
    setDescription(questionnaire.description ?? "");
    setIsDefault(questionnaire.is_default);
    setTiers(questionnaire.default_tiers);
    setCustom(Object.keys(questionnaire.tier_thresholds).length > 0);
    setBands({ ...workspaceThresholds, ...questionnaire.tier_thresholds });
    // Seed on opening only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const ordered = bands.medium > 0 && bands.medium < bands.high && bands.high < bands.critical && bands.critical <= 100;

  const save = useMutation({
    mutationFn: () =>
      updateQuestionnaire(questionnaire.id, {
        name: name.trim(),
        description: description.trim() || null,
        default_tiers: tiering ? [] : tiers,
        tier_thresholds: tiering && custom ? bands : {},
        is_default: tiering ? isDefault : false,
      }),
    onSuccess: (next) => {
      onSaved(next);
      onOpenChange(false);
      toast({ title: "Settings saved", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} />
          <TextArea
            label="Description"
            optional
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            maxLength={2000}
          />

          {tiering ? (
            <>
              <div className="flex items-start justify-between gap-3 rounded-md border border-border p-3">
                <span>
                  <span className="block text-label-md text-text-primary">Default for tiering</span>
                  <span className="block text-caption text-text-subtle">
                    {questionnaire.is_default
                      ? "The tiering dialog opens with this one."
                      : "Open the tiering dialog with this one instead."}
                  </span>
                </span>
                <Switch
                  checked={isDefault}
                  disabled={questionnaire.is_default || questionnaire.status === "archived"}
                  onCheckedChange={setIsDefault}
                  aria-label="Default for tiering"
                />
              </div>

              <div className="rounded-md border border-border p-3">
                <div className="flex items-start justify-between gap-3">
                  <span>
                    <span className="block text-label-md text-text-primary">Own tier scale</span>
                    <span className="block text-caption text-text-subtle">
                      {custom ? "Where each tier starts for this questionnaire." : "Uses the workspace scale."}
                    </span>
                  </span>
                  <Switch checked={custom} onCheckedChange={setCustom} aria-label="Own tier scale" />
                </div>
                {custom ? (
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {BANDS.map((band) => (
                      <TextField
                        key={band}
                        label={`${TIER_META[band].label} from`}
                        type="number"
                        min={1}
                        max={100}
                        value={String(bands[band] ?? "")}
                        onChange={(e) => setBands((b) => ({ ...b, [band]: Number(e.target.value) }))}
                      />
                    ))}
                  </div>
                ) : null}
                <ThresholdRuler
                  className="mt-3"
                  score={null}
                  thresholds={custom ? bands : workspaceThresholds}
                  effectiveTier={null}
                />
                {custom && !ordered ? (
                  <p className="mt-1 text-caption text-status-warning-text">
                    Each tier has to start above the one before it.
                  </p>
                ) : null}
              </div>
            </>
          ) : (
            <div className="rounded-md border border-border p-3">
              <span className="block text-label-md text-text-primary">Send by default to</span>
              <span className="block text-caption text-text-subtle">
                A tier has one default. Picking it here moves it from another questionnaire.
              </span>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {TIERS.map((tier) => (
                  <label
                    key={tier}
                    className="flex items-center gap-2.5 rounded-sm border border-border px-2.5 py-2 hover:bg-surface-hover"
                  >
                    <Checkbox
                      checked={tiers.includes(tier)}
                      onCheckedChange={(on) =>
                        setTiers((t) => (on ? [...t, tier] : t.filter((x) => x !== tier)))
                      }
                      aria-label={`${TIER_META[tier].label} tier`}
                    />
                    <TierBadge tier={tier} label={`${TIER_META[tier].label} tier`} />
                  </label>
                ))}
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={save.isPending}
            disabled={!name.trim() || (tiering && custom && !ordered)}
            onClick={() => save.mutate()}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
