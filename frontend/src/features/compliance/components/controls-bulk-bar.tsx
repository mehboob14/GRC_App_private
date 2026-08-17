import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BulkActionBar,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  useToast,
} from "@/components/ui";
import { OwnerSelect } from "@/features/iam/components/owner-select";
import { controlsApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import type { Control, ControlStatus } from "@/lib/api/types";

const STATUS_OPTIONS: { value: ControlStatus; label: string }[] = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "implemented", label: "Implemented" },
  { value: "not_applicable", label: "Not applicable" },
];

/** Dark-bar button — the bar is inverse, so the DS light variants do not fit. */
function BarButton({
  icon,
  label,
  onClick,
  disabled,
  title,
}: {
  icon: "users" | "gauge" | "shield" | "activity" | "arrowup";
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 font-sans text-label-sm transition-colors duration-80",
        disabled
          ? "cursor-not-allowed text-text-inverse/35"
          : "text-text-inverse hover:bg-white/10",
      )}
    >
      <Icon name={icon} className="size-3.5" />
      {label}
      {disabled ? (
        <span className="rounded-2xs bg-white/10 px-1 text-[10px] font-bold uppercase">
          Soon
        </span>
      ) : null}
    </button>
  );
}

function toCsv(controls: Control[]): string {
  const header = [
    "Code",
    "Name",
    "Description",
    "Category",
    "Type",
    "Status",
    "Owner",
    "Criteria",
  ];
  // Quote every field and double any embedded quote — a control description
  // routinely contains commas, and an export that corrupts on them is worse
  // than no export.
  const escape = (value: string) => `"${(value ?? "").replace(/"/g, '""')}"`;
  const rows = controls.map((control) =>
    [
      control.code,
      control.name,
      control.description,
      control.category,
      control.control_type,
      control.disabled_at ? "Disabled" : control.status,
      control.owner_name ?? "",
      control.requirement_keys.join(" "),
    ]
      .map((field) => escape(String(field)))
      .join(","),
  );
  return [header.map(escape).join(","), ...rows].join("\r\n");
}

/**
 * Bulk actions for the selected controls.
 *
 * There is no bulk endpoint, so each action is N sequential PATCHes. That is
 * not atomic: partial failure is reported honestly ("7 updated, 2 failed")
 * rather than swallowed, and disabled controls are skipped up front because the
 * API refuses to patch them ("a disabled control cannot be edited").
 */
export function ControlsBulkBar({
  selected,
  onClear,
}: {
  selected: Control[];
  onClear: () => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [ownerOpen, setOwnerOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  // `touched` separates "not chosen yet" from "deliberately chose Unassigned":
  // both are a null ownerId, but only the second may fire a bulk unassign.
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [ownerTouched, setOwnerTouched] = useState(false);
  const [status, setStatus] = useState<ControlStatus>("implemented");

  // Disabled controls are retired; the API refuses to patch them.
  const editable = selected.filter((control) => !control.disabled_at);
  const skipped = selected.length - editable.length;

  const applyMutation = useMutation({
    mutationFn: async (patch: { owner_membership_id?: string | null; status?: ControlStatus }) => {
      const results = await Promise.allSettled(
        editable.map((control) =>
          controlsApi.update(
            control.id,
            patch.owner_membership_id !== undefined
              ? patch.owner_membership_id === null
                ? { clear_owner: true }
                : { owner_membership_id: patch.owner_membership_id }
              : { status: patch.status },
          ),
        ),
      );
      const failed = results.filter((r) => r.status === "rejected");
      return { ok: results.length - failed.length, failed: failed.length };
    },
    onSuccess: async ({ ok, failed }) => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      setOwnerOpen(false);
      setStatusOpen(false);
      const skipNote = skipped ? ` · ${skipped} disabled skipped` : "";
      if (failed) {
        toast({ title: `${ok} updated, ${failed} failed${skipNote}`, tone: "danger" });
      } else {
        toast({ title: `${ok} controls updated${skipNote}`, tone: "success" });
        onClear();
      }
    },
    onError: (error: unknown) =>
      toast({
        title: error instanceof ApiError ? error.message : "Couldn't update the controls.",
        tone: "danger",
      }),
  });

  function exportCsv() {
    const blob = new Blob([toCsv(selected)], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `controls-${selected.length}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    toast({ title: `Exported ${selected.length} controls`, tone: "success" });
  }

  return (
    <>
      <BulkActionBar count={selected.length} noun="controls" onClear={onClear}>
        <BarButton icon="users" label="Assign owner" onClick={() => setOwnerOpen(true)} />
        <BarButton icon="gauge" label="Set status" onClick={() => setStatusOpen(true)} />
        <BarButton
          icon="shield"
          label="Map framework"
          disabled
          title="SOC 2 is the only framework in the library today"
        />
        <BarButton
          icon="activity"
          label="Run tests"
          disabled
          title="Automated control testing arrives with the connectors module"
        />
        <BarButton icon="arrowup" label="Export" onClick={exportCsv} />
      </BulkActionBar>

      {/* Assign owner */}
      <Dialog
        open={ownerOpen}
        onOpenChange={(open) => {
          setOwnerOpen(open);
          if (!open) {
            setOwnerId(null);
            setOwnerTouched(false);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign owner</DialogTitle>
          </DialogHeader>
          <p className="mb-3 text-body-md text-text-secondary">
            {editable.length} control{editable.length === 1 ? "" : "s"} will be reassigned
            {skipped ? ` · ${skipped} disabled skipped` : ""}.
          </p>
          <OwnerSelect
            value={ownerId}
            onChange={(next) => {
              setOwnerId(next);
              setOwnerTouched(true);
            }}
            placeholder="Choose a person…"
          />
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOwnerOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={applyMutation.isPending}
              // Nothing chosen yet must not fall through to a bulk unassign.
              disabled={editable.length === 0 || !ownerTouched}
              variant={ownerTouched && ownerId === null ? "destructive" : "primary"}
              onClick={() => applyMutation.mutate({ owner_membership_id: ownerId })}
            >
              {ownerId ? "Assign owner" : "Unassign all"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Set status */}
      <Dialog open={statusOpen} onOpenChange={setStatusOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Set status</DialogTitle>
          </DialogHeader>
          <p className="mb-3 text-body-md text-text-secondary">
            {editable.length} control{editable.length === 1 ? "" : "s"} will be updated
            {skipped ? ` · ${skipped} disabled skipped` : ""}.
          </p>
          <SelectField label="Status">
            <Select value={status} onValueChange={(value) => setStatus(value as ControlStatus)}>
              <SelectTrigger aria-label="Status" />
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setStatusOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={applyMutation.isPending}
              disabled={editable.length === 0}
              onClick={() => applyMutation.mutate({ status })}
            >
              Set status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
