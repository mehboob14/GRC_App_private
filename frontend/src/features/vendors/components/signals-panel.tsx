import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
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
  SeverityChip,
  StatusPill,
  TextArea,
  TextField,
  useToast,
  type Severity,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { recordSignal, setSignalStatus } from "../api";
import {
  FINDING_SEVERITIES,
  SIGNAL_SOURCE_CLASSES,
  SIGNAL_TYPES,
  type VendorDetail,
} from "../types";
import { fmtDate } from "../tokens";
import { Panel } from "./panel";

const TYPE_LABEL: Record<string, string> = {
  breach: "Breach",
  adverse_media: "Adverse news",
  rating_change: "Rating change",
  financial: "Financial",
  sla_breach: "Service level",
  cert_expiry: "Certificate lapsed",
};

const SOURCE_LABEL: Record<string, string> = {
  internal: "We saw it",
  media: "News",
  breach_intel: "Breach intelligence",
  rating_platform: "Rating platform",
  financial_provider: "Financial provider",
};

const STATUS_META: Record<string, { label: string; family: "warning" | "neutral" | "success" }> = {
  new: { label: "New", family: "warning" },
  acknowledged: { label: "Acknowledged", family: "success" },
  dismissed: { label: "Dismissed", family: "neutral" },
};

/**
 * Adverse events about a vendor, recorded by hand.
 *
 * Automated feeds are Phase 2, and a breach heard about on a call is worth the
 * same as one a feed reports: both are things somebody has to decide about. The
 * decision is the point, so acknowledging and dismissing are both recorded with
 * a name against them.
 */
export function SignalsPanel({
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
  const fresh = vendor.signals.filter((s) => s.status === "new");

  const decide = useMutation({
    mutationFn: (input: { id: string; status: "acknowledged" | "dismissed" }) =>
      setSignalStatus(vendor.id, input.id, input.status),
    onSuccess: (next, input) => {
      onApply(next);
      toast({
        title: input.status === "acknowledged" ? "Signal acknowledged" : "Signal dismissed",
        tone: "success",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "signal"), tone: "danger" }),
  });

  return (
    <>
      <Panel
        title="Signals"
        count={vendor.signals.length || undefined}
        description={fresh.length > 0 ? `${fresh.length} waiting on a decision` : undefined}
        action={
          canManage ? (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Icon name="plus" className="size-4" />
              Record signal
            </Button>
          ) : null
        }
      >
        {vendor.signals.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            Nothing recorded. Add a breach, a news story or a rating change as you hear about it.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {vendor.signals.map((s) => {
              const status = STATUS_META[s.status] ?? { label: s.status, family: "neutral" as const };
              return (
                <li key={s.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2">
                      <SeverityChip
                        severity={s.severity as Severity}
                        label={s.severity.charAt(0).toUpperCase() + s.severity.slice(1)}
                      />
                      <span className="text-body-md font-semibold text-text-primary">{s.title}</span>
                      <Badge variant="neutral">{TYPE_LABEL[s.signal_type] ?? s.signal_type}</Badge>
                    </p>
                    {s.detail ? (
                      <p className="mt-1 whitespace-pre-line text-body-sm text-text-secondary">
                        {s.detail}
                      </p>
                    ) : null}
                    <p className="mt-1 text-caption text-text-subtle">
                      {SOURCE_LABEL[s.source_class] ?? s.source_class} · seen{" "}
                      {fmtDate(s.observed_at)}
                      {s.acknowledged_by_name ? ` · ${s.acknowledged_by_name}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <StatusPill status={status.family} label={status.label} kind="inline" />
                    {s.status === "new" && canManage ? (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={decide.isPending && decide.variables?.id === s.id}
                          onClick={() => decide.mutate({ id: s.id, status: "acknowledged" })}
                        >
                          Acknowledge
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => decide.mutate({ id: s.id, status: "dismissed" })}
                        >
                          Dismiss
                        </Button>
                      </>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      <RecordSignalDialog
        open={adding}
        onOpenChange={setAdding}
        vendorId={vendor.id}
        onRecorded={onApply}
      />
    </>
  );
}

function RecordSignalDialog({
  open,
  onOpenChange,
  vendorId,
  onRecorded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  onRecorded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const blank = {
    signal_type: "breach",
    title: "",
    severity: "high",
    detail: "",
    source_class: "internal",
    observed_on: "",
    raise_finding: true,
  };
  const [form, setForm] = useState(blank);
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const record = useMutation({
    mutationFn: () =>
      recordSignal(vendorId, {
        signal_type: form.signal_type,
        title: form.title.trim(),
        severity: form.severity,
        detail: form.detail.trim(),
        source_class: form.source_class,
        observed_on: form.observed_on || null,
        raise_finding: form.raise_finding,
      }),
    onSuccess: (next) => {
      onRecorded(next);
      onOpenChange(false);
      setForm(blank);
      toast({ title: "Signal recorded", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "signal"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Record signal</DialogTitle>
          <DialogDescription>Something adverse you heard about this vendor.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (form.title.trim()) record.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="What happened"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="Customer data exposed in their support tool"
              autoFocus
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <SelectField label="Kind">
                <Select value={form.signal_type} onValueChange={(v) => set("signal_type", v)}>
                  <SelectTrigger aria-label="Signal kind" />
                  <SelectContent>
                    {SIGNAL_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {TYPE_LABEL[t] ?? t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <SelectField label="Severity">
                <Select value={form.severity} onValueChange={(v) => set("severity", v)}>
                  <SelectTrigger aria-label="Severity" />
                  <SelectContent>
                    {FINDING_SEVERITIES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <SelectField label="How we know">
                <Select value={form.source_class} onValueChange={(v) => set("source_class", v)}>
                  <SelectTrigger aria-label="Source" />
                  <SelectContent>
                    {SIGNAL_SOURCE_CLASSES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {SOURCE_LABEL[s] ?? s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <TextField
                label="When"
                optional
                type="date"
                hint="Today if left blank."
                value={form.observed_on}
                onChange={(e) => set("observed_on", e.target.value)}
              />
            </div>
            <TextArea
              label="Detail"
              optional
              value={form.detail}
              onChange={(e) => set("detail", e.target.value)}
              rows={3}
              maxLength={8000}
            />
            <label className="flex items-start gap-2.5 rounded-md border border-border bg-surface-sunken px-3 py-2.5">
              <input
                type="checkbox"
                className="mt-1 size-4 accent-action-accent"
                checked={form.raise_finding}
                onChange={(e) => set("raise_finding", e.target.checked)}
              />
              <span>
                <span className="block font-sans text-label-sm text-text-primary">
                  Raise a finding with it
                </span>
                <span className="block text-caption text-text-subtle">
                  Gives it an owner and a due date. Leave off for a note.
                </span>
              </span>
            </label>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={record.isPending} disabled={!form.title.trim()}>
              Record signal
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
