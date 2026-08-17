import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextField,
  useToast,
} from "@/components/ui";
import { controlsApi, evidenceApi, iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import type { Control, ControlStatus } from "@/lib/api/types";

const STATUS_LABEL: Record<string, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  implemented: "Implemented",
  not_applicable: "Not applicable",
};

/** Edit the control in place. Uses the same PATCH the library uses, so there is
 *  one write path rather than a second, diverging editor. */
export function EditControlDialog({
  control,
  open,
  onOpenChange,
  onSaved,
}: {
  control: Control;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => Promise<void>;
}) {
  const { toast } = useToast();
  const [name, setName] = useState(control.name);
  const [description, setDescription] = useState(control.description);
  const [guidance, setGuidance] = useState(control.implementation_guidance ?? "");
  const [status, setStatus] = useState<string>(control.status);
  const [ownerId, setOwnerId] = useState(control.owner_membership_id ?? "");

  // Re-seed on open, or the dialog keeps showing the previously edited values.
  useEffect(() => {
    if (!open) return;
    setName(control.name);
    setDescription(control.description);
    setGuidance(control.implementation_guidance ?? "");
    setStatus(control.status);
    setOwnerId(control.owner_membership_id ?? "");
  }, [open, control]);

  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: open,
  });
  const vocabularyQuery = useQuery({
    queryKey: ["control-vocabulary"],
    queryFn: () => controlsApi.vocabulary(),
    enabled: open,
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      controlsApi.update(control.id, {
        name,
        description,
        implementation_guidance: guidance || null,
        status: status as ControlStatus,
        // An empty picker means "unassign", which a null owner_membership_id
        // cannot express in a patch body — hence the explicit flag.
        ...(ownerId ? { owner_membership_id: ownerId } : { clear_owner: true }),
      }),
    onSuccess: async () => {
      await onSaved();
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't save the control.",
        tone: "danger",
      }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit {control.code}</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <TextField
            label="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />

          <div>
            <label
              htmlFor="control-statement"
              className="mb-1.5 block font-sans text-label-sm text-text-secondary"
            >
              Control statement
            </label>
            <textarea
              id="control-statement"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              className="block w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-body-md text-text-primary outline-none focus-visible:border-action-accent"
            />
          </div>

          <div>
            <label
              htmlFor="control-guidance"
              className="mb-1.5 block font-sans text-label-sm text-text-secondary"
            >
              Implementation guidance
            </label>
            <textarea
              id="control-guidance"
              value={guidance}
              onChange={(event) => setGuidance(event.target.value)}
              rows={5}
              className="block w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-body-md text-text-primary outline-none focus-visible:border-action-accent"
            />
            <p className="mt-1 text-caption text-text-subtle">
              One step per line renders as a list on the control.
            </p>
          </div>

          <SelectField label="Status">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger aria-label="Status" />
              <SelectContent>
                {(vocabularyQuery.data?.statuses ?? []).map((value) => (
                  <SelectItem key={value} value={value}>
                    {STATUS_LABEL[value] ?? value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>

          <SelectField label="Owner" optional>
            <Select value={ownerId} onValueChange={setOwnerId}>
              <SelectTrigger aria-label="Owner" />
              <SelectContent>
                {(membersQuery.data ?? []).map((member) => (
                  <SelectItem key={member.membership_id} value={member.membership_id}>
                    {member.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={saveMutation.isPending}
            disabled={!name.trim() || !description.trim()}
            onClick={() => saveMutation.mutate()}
          >
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Link EXISTING evidence to this control. Uploading a new item is the
 *  evidence library's own dialog, reused as-is — this one only picks. */
export function AttachEvidenceDialog({
  controlId,
  open,
  onOpenChange,
  onDone,
}: {
  controlId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDone: () => Promise<void>;
}) {
  const { toast } = useToast();
  const [picked, setPicked] = useState<string[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) return;
    setPicked([]);
    setSearch("");
  }, [open]);

  const libraryQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => evidenceApi.list(),
    enabled: open,
  });

  // Items not already attached. Offering an already-linked one would be a
  // no-op the user could not tell apart from a failure.
  const candidates = (libraryQuery.data ?? []).filter(
    (item) =>
      !item.control_ids.includes(controlId) &&
      (search.trim() === "" ||
        item.title.toLowerCase().includes(search.trim().toLowerCase())),
  );

  const attachMutation = useMutation({
    mutationFn: async () => {
      // control_ids REPLACES the set, so each item's existing links are carried
      // through — sending only this control would silently detach the others.
      const library = libraryQuery.data ?? [];
      await Promise.all(
        picked.map((id) => {
          const item = library.find((candidate) => candidate.id === id);
          return evidenceApi.update(id, {
            control_ids: [...(item?.control_ids ?? []), controlId],
          });
        }),
      );
    },
    onSuccess: async () => {
      await onDone();
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError
            ? error.message
            : "Couldn't attach the evidence.",
        tone: "danger",
      }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Link existing evidence</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <TextField
            label="Search the library"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Filter by title…"
          />
          <div className="max-h-80 overflow-y-auto rounded-md border border-border">
            {candidates.length === 0 ? (
              <p className="p-4 text-body-sm text-text-subtle">
                {(libraryQuery.data ?? []).length === 0
                  ? "The library is empty — use Add evidence to upload one."
                  : "Every matching item is already attached to this control."}
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {candidates.map((item) => {
                  const checked = picked.includes(item.id);
                  return (
                    <li key={item.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) =>
                            setPicked((previous) =>
                              event.target.checked
                                ? [...previous, item.id]
                                : previous.filter((id) => id !== item.id),
                            )
                          }
                          className="size-4 rounded-xs border-border"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-body-md text-text-primary">
                            {item.title}
                          </span>
                          <span className="block truncate text-caption text-text-subtle">
                            {item.evidence_type.replace(/_/g, " ")}
                            {item.control_codes.length
                              ? ` · already on ${item.control_codes.length} control(s)`
                              : ""}
                          </span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          <p className="text-caption text-text-subtle">
            One item can support several controls — linking here does not remove
            it from any control it already supports.
          </p>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={attachMutation.isPending}
            disabled={picked.length === 0}
            onClick={() => attachMutation.mutate()}
          >
            Link{picked.length ? ` ${picked.length}` : ""}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
