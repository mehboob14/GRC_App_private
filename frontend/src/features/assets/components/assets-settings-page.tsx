import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, ErrorState, Skeleton, TextField, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { CustomFieldsCard } from "@/features/custom-fields/components/custom-fields-card";
import { getReviewCadence, setReviewCadence } from "../api";
import type { ReviewCadence } from "../types";

type Tier = keyof ReviewCadence;

const TIER_ORDER: Tier[] = ["critical", "high", "medium", "low", "unrated"];

const TIER_LABEL: Record<Tier, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  unrated: "Not yet rated",
};

const TIER_HINT: Record<Tier, string> = {
  critical: "The estate's crown jewels.",
  high: "Material to the service.",
  medium: "Supporting systems.",
  low: "Low impact if it fails.",
  unrated: "No CIA rating yet, so no tier.",
};

/** Inventory settings: how often each criticality is reviewed, and the fields
 *  this workspace collects on top of the shipped ones. */
export function AssetsSettingsPage() {
  const { principal } = useAuth();
  const canEdit = hasPermission(principal, "assets:manage");
  return (
    <div className="mt-4 max-w-[860px] space-y-4">
      <CadenceCard canEdit={canEdit} />
      <CustomFieldsCard scope="assets" noun="asset" canEdit={canEdit} />
    </div>
  );
}

function CadenceCard({ canEdit }: { canEdit: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const cadenceQuery = useQuery({ queryKey: ["asset-review-cadence"], queryFn: getReviewCadence });

  const save = useMutation({
    mutationFn: ({ tier, days }: { tier: Tier; days: number }) => setReviewCadence({ [tier]: days }),
    onSuccess: (cadence) => {
      queryClient.setQueryData(["asset-review-cadence"], cadence);
      // The hygiene panel and the register's attention filter both read the
      // window, so they are stale the moment it changes.
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      void queryClient.invalidateQueries({ queryKey: ["asset"] });
      void queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      toast({ title: "Review cadence saved", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "review cadence"), tone: "danger" }),
  });

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="font-display text-title-sm text-text-primary">Review cadence</h2>
      <p className="mt-1 text-body-sm text-text-secondary">
        How long an asset of each criticality may go unreviewed before the inventory hygiene panel
        calls it stale. The clock starts at the last review, and "Mark reviewed" restarts it.
      </p>
      {!canEdit ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          You can view these settings. Editing needs the Manage assets permission.
        </p>
      ) : null}

      {cadenceQuery.isPending ? (
        <div className="mt-4 space-y-2">
          {TIER_ORDER.map((t) => (
            <Skeleton key={t} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : cadenceQuery.isError ? (
        <div className="mt-4">
          <ErrorState
            title={describeError(cadenceQuery.error, "review cadence").title}
            description={describeError(cadenceQuery.error, "review cadence").message}
            onRetry={() => void cadenceQuery.refetch()}
          />
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {TIER_ORDER.map((tier) => (
            <CadenceRow
              key={tier}
              tier={tier}
              days={cadenceQuery.data[tier]}
              canEdit={canEdit}
              saving={save.isPending && save.variables?.tier === tier}
              onSave={(days) => save.mutate({ tier, days })}
            />
          ))}
        </ul>
      )}

      <p className="mt-4 border-t border-border pt-3 text-caption text-text-subtle">
        Between 7 and 1095 days. A change applies at once: an asset already past its new window
        reads as stale on the next load.
      </p>
    </div>
  );
}

function CadenceRow({
  tier,
  days,
  canEdit,
  saving,
  onSave,
}: {
  tier: Tier;
  days: number;
  canEdit: boolean;
  saving: boolean;
  onSave: (days: number) => void;
}) {
  const [value, setValue] = useState(String(days));
  useEffect(() => setValue(String(days)), [days]);
  const parsed = Number(value);
  const changed = value.trim() !== "" && Number.isFinite(parsed) && parsed !== days;

  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-label-md text-text-primary">{TIER_LABEL[tier]}</p>
        <p className="text-caption text-text-subtle">{TIER_HINT[tier]}</p>
      </div>
      <div className="w-28">
        <TextField
          label="Days"
          type="number"
          min={7}
          max={1095}
          value={value}
          disabled={!canEdit}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>
      <Button
        variant="secondary"
        size="sm"
        loading={saving}
        disabled={!canEdit || !changed}
        onClick={() => onSave(Math.round(parsed))}
      >
        Save
      </Button>
    </li>
  );
}
