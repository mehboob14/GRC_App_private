import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { requestVendor } from "../api";
import type { DuplicateMatch } from "../types";
import { duplicateReason } from "../tokens";

const BLANK = { vendor_name: "", department: "", proposed_service: "", urgency: "normal" };

/**
 * Asking for a vendor is not the same as adding one.
 *
 * This is the only vendors write that needs no more than `vendors:read` —
 * anyone who can see the register can ask, and someone with `vendors:manage`
 * decides. The screening result and any duplicate matches come back with the
 * request so the requester learns immediately, not a week later.
 */
export function RequestVendorDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState(BLANK);
  const [matches, setMatches] = useState<DuplicateMatch[] | null>(null);

  useEffect(() => {
    if (open) {
      setForm(BLANK);
      setMatches(null);
    }
  }, [open]);

  const submit = useMutation({
    mutationFn: () =>
      requestVendor({
        vendor_name: form.vendor_name.trim(),
        department: form.department.trim() || null,
        proposed_service: form.proposed_service.trim(),
        urgency: form.urgency,
      }),
    onSuccess: (request) => {
      void queryClient.invalidateQueries({ queryKey: ["vendor-intake"] });
      if (request.duplicates.length > 0) {
        // Keep the dialog open: the requester needs to see that this may already
        // be in the register before they walk away thinking it is new.
        setMatches(request.duplicates);
        toast({ title: "Request submitted. Possible duplicates found.", tone: "neutral" });
        return;
      }
      toast({ title: "Request submitted for review", tone: "success" });
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "vendor request"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Request a vendor</DialogTitle>
          <DialogDescription>The third-party risk team reviews every request.</DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (form.vendor_name.trim()) submit.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="Vendor name"
              value={form.vendor_name}
              onChange={(e) => setForm((f) => ({ ...f, vendor_name: e.target.value }))}
              placeholder="Acme Analytics"
              autoFocus
              disabled={matches !== null}
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Your department"
                optional
                value={form.department}
                onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
                placeholder="Marketing"
                disabled={matches !== null}
              />
              <SelectField label="Urgency">
                <Select
                  value={form.urgency}
                  onValueChange={(v) => setForm((f) => ({ ...f, urgency: v }))}
                >
                  <SelectTrigger aria-label="Urgency" disabled={matches !== null} />
                  <SelectContent>
                    <SelectItem value="low">Low: no fixed date</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High: blocked without it</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
            <TextField
              label="Intended use"
              optional
              hint="Include any data they would see."
              value={form.proposed_service}
              onChange={(e) => setForm((f) => ({ ...f, proposed_service: e.target.value }))}
              placeholder="Campaign attribution using hashed email addresses."
              disabled={matches !== null}
            />

            {matches ? (
              <div className="rounded-md border border-status-warning-border bg-status-warning-bg p-3">
                <p className="flex items-center gap-1.5 text-label-sm text-status-warning-text">
                  <Icon name="alert" className="size-4 shrink-0" />
                  This may already be approved
                </p>
                <ul className="mt-2 space-y-1">
                  {matches.map((m) => (
                    <li key={m.id} className="text-body-sm text-text-secondary">
                      <span className="font-semibold text-text-primary">{m.name}</span>:{" "}
                      {duplicateReason(m.reason)}
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-caption text-text-subtle">
                  Your request was still submitted.
                </p>
              </div>
            ) : null}
          </DialogBody>

          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              {matches ? "Done" : "Cancel"}
            </Button>
            {matches ? null : (
              <Button type="submit" loading={submit.isPending} disabled={!form.vendor_name.trim()}>
                Submit request
              </Button>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
