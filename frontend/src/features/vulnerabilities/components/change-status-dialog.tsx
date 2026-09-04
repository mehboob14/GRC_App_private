import { useState } from "react";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";
import { STATE_LABEL } from "../tokens";
import type { InstanceState } from "../types";

/**
 * Move a finding to another state, with an optional note.
 *
 * Only states the server will actually accept are offered — the legal-move map
 * lives in the service (`_MANUAL_TRANSITIONS`) and reaches here as
 * `allowed_transitions`, so the dialog cannot offer a move that will 400. The
 * note is optional and is recorded on the transition row, which is what the
 * activity timeline reads.
 */
export function ChangeStatusDialog({
  open,
  onOpenChange,
  currentState,
  allowed,
  pending,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentState: InstanceState;
  allowed: InstanceState[];
  pending: boolean;
  onConfirm: (to: InstanceState, note: string | undefined) => void;
}) {
  const [to, setTo] = useState<InstanceState | "">(allowed[0] ?? "");
  const [note, setNote] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setNote("");
          setTo(allowed[0] ?? "");
        }
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change status</DialogTitle>
          <DialogDescription>
            Currently {STATE_LABEL[currentState]}. The change and your note are
            recorded on the finding&rsquo;s timeline.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <div>
            <label
              className="mb-1 block text-label-md font-semibold text-text-primary"
              htmlFor="new-state"
            >
              New status
            </label>
            <Select value={to} onValueChange={(next) => setTo(next as InstanceState)}>
              <SelectTrigger id="new-state">
                <SelectValue placeholder="Choose a status" />
              </SelectTrigger>
              <SelectContent>
                {allowed.map((state) => (
                  <SelectItem key={state} value={state}>
                    {STATE_LABEL[state]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label
              className="mb-1 block text-label-md font-semibold text-text-primary"
              htmlFor="state-note"
            >
              Note <span className="font-normal text-text-subtle">(optional)</span>
            </label>
            <textarea
              id="state-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="What changed, and why — the next person to open this will read it."
              className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary placeholder:text-text-faint focus:border-action-accent focus:outline-none"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={pending}
            disabled={!to}
            onClick={() => to && onConfirm(to, note.trim() || undefined)}
          >
            Change status
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
