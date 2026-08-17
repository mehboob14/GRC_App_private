import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  TextField,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import type { Control } from "@/lib/api/types";

/**
 * Choose which controls a piece of evidence supports.
 *
 * The dialog edits the WHOLE set and saves it in one write, because the API's
 * `control_ids` replaces rather than merges. Editing a copy and saving once is
 * what keeps "unlink" and "link" from needing two different code paths.
 */
export function LinkControlsDialog({
  open,
  onOpenChange,
  controls,
  linkedIds,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  controls: Control[];
  linkedIds: string[];
  onSave: (ids: string[]) => Promise<void>;
  /** Present for callers that unlink from outside the dialog; unused here. */
  onUnlink?: (id: string) => void;
}) {
  const { toast } = useToast();
  const [selected, setSelected] = useState<string[]>(linkedIds);
  const [search, setSearch] = useState("");

  // linkedIds is a fresh array each render, so the effect keys on its CONTENT.
  // Keying on the array itself would reset the user's in-progress selection on
  // every parent re-render.
  const linkedKey = linkedIds.join(",");
  useEffect(() => {
    if (!open) return;
    setSelected(linkedKey ? linkedKey.split(",") : []);
    setSearch("");
  }, [open, linkedKey]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return controls.slice(0, 300);
    return controls
      .filter(
        (control) =>
          control.name.toLowerCase().includes(query) ||
          control.code.toLowerCase().includes(query) ||
          control.requirement_keys.some((key) => key.toLowerCase().includes(query)),
      )
      .slice(0, 300);
  }, [controls, search]);

  const saveMutation = useMutation({
    mutationFn: () => onSave(selected),
    onSuccess: () => onOpenChange(false),
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't update the links.",
        tone: "danger",
      }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Link controls</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <TextField
            label="Search controls"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="By name, code or criterion…"
          />
          <p className="text-caption text-text-subtle">
            <span className="tabular font-semibold text-text-primary">
              {selected.length}
            </span>{" "}
            selected. One item can support as many controls as it evidences.
          </p>
          <div className="max-h-80 overflow-y-auto rounded-md border border-border">
            {visible.length === 0 ? (
              <p className="p-4 text-body-sm text-text-subtle">
                No controls match that search.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {visible.map((control) => {
                  const checked = selected.includes(control.id);
                  return (
                    <li key={control.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) =>
                            setSelected((previous) =>
                              event.target.checked
                                ? [...previous, control.id]
                                : previous.filter((id) => id !== control.id),
                            )
                          }
                          className="size-4 rounded-xs border-border"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-body-md text-text-primary">
                            <span className="mr-2 font-display text-caption font-bold text-text-link">
                              {control.code}
                            </span>
                            {control.name}
                          </span>
                          <span className="block truncate text-caption text-text-subtle">
                            {control.requirement_keys
                              .map((key) => key.replace(/^[^:]+:/, ""))
                              .join(" · ") || "no criterion"}
                          </span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            Save links
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
