import { useRef, useState, type ReactNode } from "react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { Icon } from "@/components/ui/icon";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Names the object: "Delete this evidence item?" */
  title: string;
  /** Names the consequence — what is linked and what will be lost (§7.3). */
  consequence: ReactNode;
  /** Verb + object: "Delete evidence". */
  confirmLabel: string;
  onConfirm: () => void;
  loading?: boolean;
  /**
   * Type-to-confirm phrase for bulk destructives — the confirm button stays
   * disabled until the user types it exactly.
   */
  typeToConfirm?: string;
};

/**
 * DS §7.3 destructive confirm — initial focus lands on Cancel so Enter
 * cannot destroy anything by reflex.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  consequence,
  confirmLabel,
  onConfirm,
  loading = false,
  typeToConfirm,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const [typed, setTyped] = useState("");
  const confirmBlocked = typeToConfirm !== undefined && typed !== typeToConfirm;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped("");
        onOpenChange(next);
      }}
    >
      <DialogContent
        size="sm"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          cancelRef.current?.focus();
        }}
      >
        <div className="flex flex-col gap-3">
          <span className="flex size-9 items-center justify-center rounded-md bg-action-danger-tint">
            <Icon name="trash" className="size-[18px] text-action-danger" />
          </span>
          <DialogTitle className="font-display text-title-md font-extrabold text-text-primary">
            {title}
          </DialogTitle>
          <div className="text-body-sm text-text-subtle">{consequence}</div>
          {typeToConfirm !== undefined ? (
            <TextField
              label={`Type "${typeToConfirm}" to confirm`}
              value={typed}
              onChange={(event) => setTyped(event.target.value)}
              placeholder={typeToConfirm}
              autoComplete="off"
            />
          ) : null}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button ref={cancelRef} variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={loading}
            disabled={confirmBlocked}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
