import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
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
  Table,
  TBody,
  TD,
  TH,
  THead,
  Tooltip,
  TR,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { addSubprocessor, removeSubprocessor } from "../api";
import type { VendorDetail } from "../types";
import { PROVENANCE_META } from "../tokens";
import { Panel } from "./panel";

/**
 * The fourth parties behind this vendor.
 *
 * Provenance is on every row because it changes what the entry is worth: a
 * vendor-declared subprocessor is a claim, an auto-detected one is an
 * observation, and the two must never look alike. The count of other vendors
 * using the same subprocessor is the concentration risk nobody sees until it is
 * on a screen.
 */
export function SubprocessorsPanel({
  vendor,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const [adding, setAdding] = useState(false);
  // Removed ones stay on the record ("who processed our data, and when") but
  // leave the working list.
  const rows = vendor.subprocessors.filter((s) => s.status !== "removed");
  const removedCount = vendor.subprocessors.length - rows.length;
  const shared = rows.filter((s) => s.also_used_by_vendors > 0);

  const remove = useMutation({
    mutationFn: (id: string) => removeSubprocessor(vendor.id, id),
    onSuccess: (items) => {
      onApply({ ...vendor, subprocessors: items });
      toast({ title: "Subprocessor removed. It stays on the record.", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "subprocessor"), tone: "danger" }),
  });

  return (
    <>
      <Panel
        title="Subprocessors"
        count={rows.length || undefined}
        description={
          [
            shared.length > 0 ? `${shared.length} shared with other vendors` : null,
            removedCount > 0 ? `${removedCount} no longer used` : null,
          ]
            .filter(Boolean)
            .join(" · ") || undefined
        }
        action={
          canManage ? (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Icon name="plus" className="size-4" />
              Add subprocessor
            </Button>
          ) : null
        }
      >
        {rows.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            None recorded. Ask the vendor for their subprocessor list.
          </p>
        ) : (
          <Table density="compact">
            <THead>
              <TR>
                <TH>Subprocessor</TH>
                <TH>Service</TH>
                <TH>Where</TH>
                <TH>Source</TH>
                <TH numeric>Also used by</TH>
                {canManage ? <TH aria-label="Actions" /> : null}
              </TR>
            </THead>
            <TBody>
              {rows.map((s) => {
                const provenance = PROVENANCE_META[s.provenance] ?? {
                  label: s.provenance,
                  variant: "neutral" as const,
                };
                return (
                  <TR key={s.id}>
                    <TD>
                      <span className="text-body-md text-text-primary">{s.name}</span>
                      {s.linked_vendor_id ? (
                        <Link
                          to={`/vendors/${s.linked_vendor_id}`}
                          className="ml-1.5 text-caption text-text-link underline-offset-2 hover:underline"
                        >
                          in the register
                        </Link>
                      ) : null}
                      {s.notification_obligation ? (
                        <p className="mt-0.5 text-caption text-text-subtle">
                          {s.notification_obligation}
                        </p>
                      ) : null}
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">{s.service || "Not set"}</span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">
                        {s.data_location || "Unknown"}
                      </span>
                    </TD>
                    <TD>
                      <Tooltip
                        content={
                          s.provenance === "vendor_declared"
                            ? "The vendor told us. Unverified."
                            : "Observed rather than declared."
                        }
                      >
                        <span>
                          <Badge variant={provenance.variant}>{provenance.label}</Badge>
                        </span>
                      </Tooltip>
                    </TD>
                    <TD numeric>
                      <span className="tabular text-body-sm text-text-secondary">
                        {s.also_used_by_vendors > 0 ? `${s.also_used_by_vendors} others` : "None"}
                      </span>
                    </TD>
                    {canManage ? (
                      <TD>
                        <Tooltip content="No longer used by this vendor">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Remove ${s.name}`}
                            loading={remove.isPending && remove.variables === s.id}
                            onClick={() => remove.mutate(s.id)}
                          >
                            <Icon name="x" className="size-4" />
                          </Button>
                        </Tooltip>
                      </TD>
                    ) : null}
                  </TR>
                );
              })}
            </TBody>
          </Table>
        )}
      </Panel>

      <AddDialog open={adding} onOpenChange={setAdding} vendor={vendor} onAdded={onApply} />
    </>
  );
}

function AddDialog({
  open,
  onOpenChange,
  vendor,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor: VendorDetail;
  onAdded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    service: "",
    data_location: "",
    provenance: "vendor_declared",
    notification_obligation: "",
  });

  const set = <K extends keyof typeof form>(key: K, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const add = useMutation({
    mutationFn: () =>
      addSubprocessor(vendor.id, {
        name: form.name.trim(),
        service: form.service.trim(),
        data_location: form.data_location.trim() || null,
        provenance: form.provenance,
        notification_obligation: form.notification_obligation.trim() || null,
      }),
    onSuccess: (items) => {
      // This route answers with the whole list, not the one row that was added.
      onAdded({ ...vendor, subprocessors: items });
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
      onOpenChange(false);
      setForm({
        name: "",
        service: "",
        data_location: "",
        provenance: "vendor_declared",
        notification_obligation: "",
      });
      toast({ title: "Subprocessor added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "subprocessor"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Add subprocessor</DialogTitle>
          <DialogDescription>
            A fourth party this vendor passes work or data to.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (form.name.trim()) add.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="Name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Amazon Web Services"
              autoFocus
            />
            <TextField
              label="Service"
              optional
              value={form.service}
              onChange={(e) => set("service", e.target.value)}
              placeholder="Hosting and object storage"
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Data location"
                optional
                value={form.data_location}
                onChange={(e) => set("data_location", e.target.value)}
                placeholder="eu-central-1"
              />
              <SelectField label="Source">
                <Select value={form.provenance} onValueChange={(v) => set("provenance", v)}>
                  <SelectTrigger aria-label="Provenance" />
                  <SelectContent>
                    <SelectItem value="vendor_declared">Vendor declared</SelectItem>
                    <SelectItem value="auto_detected">Auto detected</SelectItem>
                    <SelectItem value="intelligence">External intelligence</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
            <TextField
              label="Notification obligation"
              optional
              value={form.notification_obligation}
              onChange={(e) => set("notification_obligation", e.target.value)}
              placeholder="30 days written notice before adding a subprocessor"
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={add.isPending} disabled={!form.name.trim()}>
              Add subprocessor
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
