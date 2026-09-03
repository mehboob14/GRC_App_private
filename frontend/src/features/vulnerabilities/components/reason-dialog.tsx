import { useState } from "react";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui";

/**
 * A short "say why" step in front of an action that is recorded on the audit
 * trail. Replaces `window.prompt`, which cannot be styled, is blocked by some
 * browsers, and offers no way to mark the note required.
 */
export function ReasonDialog({
  open,
  onOpenChange,
  title,
  label,
  placeholder,
  confirmLabel,
  required = false,
  loading = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  label: string;
  placeholder?: string;
  confirmLabel: string;
  /** When true the action stays disabled until a note is written. */
  required?: boolean;
  loading?: boolean;
  onConfirm: (note: string | undefined) => void;
}) {
  const [note, setNote] = useState("");
  const trimmed = note.trim();

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setNote("");
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <label className="mb-1 block text-label-md font-semibold text-text-primary" htmlFor="reason-note">
            {label}
            {required ? "" : <span className="ml-1 font-normal text-text-subtle">(optional)</span>}
          </label>
          <textarea
            id="reason-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            placeholder={placeholder}
            className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={loading}
            disabled={required && trimmed === ""}
            onClick={() => onConfirm(trimmed || undefined)}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
