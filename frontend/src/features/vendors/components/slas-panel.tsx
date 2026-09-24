import { useState } from "react";
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
  StatusPill,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TextField,
  TR,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { saveSla } from "../api";
import { SLA_STATUSES, type Sla, type VendorDetail } from "../types";
import { fmtDate } from "../tokens";
import { Panel } from "./panel";

const STATUS_META: Record<string, { label: string; family: "success" | "warning" | "danger" }> = {
  on_track: { label: "On track", family: "success" },
  at_risk: { label: "At risk", family: "warning" },
  breached: { label: "Breached", family: "danger" },
};

/**
 * The service levels a contract commits to, and what was actually measured.
 *
 * Marking one breached is what puts it on somebody's list: the nightly sweep
 * raises one finding per breached level, once, however often it runs.
 */
export function SlasPanel({
  vendor,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Sla | null>(null);
  const breached = vendor.slas.filter((s) => s.status === "breached");
  const contracts = vendor.contracts;

  return (
    <>
      <Panel
        title="Service levels"
        count={vendor.slas.length || undefined}
        description={breached.length > 0 ? `${breached.length} breached` : undefined}
        action={
          canManage && contracts.length > 0 ? (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Icon name="plus" className="size-4" />
              Add service level
            </Button>
          ) : null
        }
      >
        {contracts.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            Record a contract first. A service level belongs to the contract that commits to it.
          </p>
        ) : vendor.slas.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            None recorded. Add uptime, response times and anything else the contract promises.
          </p>
        ) : (
          <Table density="compact">
            <THead>
              <TR>
                <TH>Service level</TH>
                <TH>Committed</TH>
                <TH>Measured</TH>
                <TH>Status</TH>
                {canManage ? <TH aria-label="Actions" /> : null}
              </TR>
            </THead>
            <TBody>
              {vendor.slas.map((s) => {
                const status = STATUS_META[s.status] ?? {
                  label: s.status,
                  family: "warning" as const,
                };
                return (
                  <TR key={s.id}>
                    <TD>
                      <span className="text-body-md text-text-primary">{s.name}</span>
                      {s.contract_title ? (
                        <p className="text-caption text-text-subtle">{s.contract_title}</p>
                      ) : null}
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">{s.target}</span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">
                        {s.measurement ?? "Not measured"}
                      </span>
                      {s.measured_on ? (
                        <p className="text-caption text-text-subtle">{fmtDate(s.measured_on)}</p>
                      ) : null}
                    </TD>
                    <TD>
                      <StatusPill status={status.family} label={status.label} kind="inline" />
                    </TD>
                    {canManage ? (
                      <TD>
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Edit ${s.name}`}
                          onClick={() => setEditing(s)}
                        >
                          Record measurement
                        </Button>
                      </TD>
                    ) : null}
                  </TR>
                );
              })}
            </TBody>
          </Table>
        )}
      </Panel>

      <SlaDialog
        key={editing?.id ?? "new"}
        open={adding || editing !== null}
        onOpenChange={(open) => {
          if (!open) {
            setAdding(false);
            setEditing(null);
          }
        }}
        vendor={vendor}
        sla={editing}
        onSaved={onApply}
      />
    </>
  );
}

function SlaDialog({
  open,
  onOpenChange,
  vendor,
  sla,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor: VendorDetail;
  /** Null adds one; an existing level records this period's measurement. */
  sla: Sla | null;
  onSaved: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    contract_id: sla?.contract_id ?? (vendor.contracts[0]?.id ?? ""),
    name: sla?.name ?? "",
    target: sla?.target ?? "",
    measurement: sla?.measurement ?? "",
    measured_on: sla?.measured_on ?? "",
    cure_period_days: sla?.cure_period_days?.toString() ?? "",
    status: sla?.status ?? "on_track",
  });
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const save = useMutation({
    mutationFn: () =>
      saveSla(
        vendor.id,
        {
          contract_id: form.contract_id,
          name: form.name.trim(),
          target: form.target.trim(),
          measurement: form.measurement.trim() || null,
          measured_on: form.measured_on || null,
          cure_period_days: form.cure_period_days ? Number(form.cure_period_days) : null,
          status: form.status,
        },
        sla?.id,
      ),
    onSuccess: (items) => {
      onSaved({ ...vendor, slas: items });
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
      onOpenChange(false);
      toast({ title: sla ? "Service level saved" : "Service level added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "service level"), tone: "danger" }),
  });

  const usable = form.contract_id && form.name.trim() && form.target.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{sla ? "Record measurement" : "Add service level"}</DialogTitle>
          <DialogDescription>
            A breached level raises a finding overnight, once per level.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (usable) save.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <SelectField label="Contract">
              <Select value={form.contract_id} onValueChange={(v) => set("contract_id", v)}>
                <SelectTrigger aria-label="Contract" />
                <SelectContent>
                  {vendor.contracts.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Name"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Uptime"
                autoFocus
              />
              <TextField
                label="Committed to"
                value={form.target}
                onChange={(e) => set("target", e.target.value)}
                placeholder="99.9% monthly"
              />
            </div>
            <div className="grid gap-3.5 sm:grid-cols-3">
              <TextField
                label="Measured"
                optional
                value={form.measurement}
                onChange={(e) => set("measurement", e.target.value)}
                placeholder="99.2%"
              />
              <TextField
                label="Measured on"
                optional
                type="date"
                value={form.measured_on}
                onChange={(e) => set("measured_on", e.target.value)}
              />
              <SelectField label="Status">
                <Select value={form.status} onValueChange={(v) => set("status", v)}>
                  <SelectTrigger aria-label="Service level status" />
                  <SelectContent>
                    {SLA_STATUSES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {STATUS_META[s]?.label ?? s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
            <TextField
              label="Cure period (days)"
              optional
              type="number"
              min={0}
              max={365}
              hint="How long they have to put it right before it counts as a breach."
              value={form.cure_period_days}
              onChange={(e) => set("cure_period_days", e.target.value)}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending} disabled={!usable}>
              {sla ? "Save" : "Add service level"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
