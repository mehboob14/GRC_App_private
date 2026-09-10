import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
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
  TextField,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { addContract } from "../api";
import { CONTRACT_TYPES, type Contract, type VendorDetail } from "../types";
import {
  CONTRACT_STATUS_META,
  CONTRACT_TYPE_LABEL,
  daysUntil,
  fmtCountdown,
  fmtDate,
  fmtMoney,
} from "../tokens";
import { Panel } from "./panel";

/**
 * Contracts, and the four clauses that decide what you can actually do when
 * something goes wrong.
 *
 * The service levels that matter for third-party risk are contractual, not
 * operational: how long they have to tell you about a breach, and how much
 * notice you have to give before the thing auto-renews. Both are on the row.
 */
export function ContractsPanel({
  vendor,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const [adding, setAdding] = useState(false);
  const contracts = vendor.contracts;

  return (
    <>
      <Panel
        title="Contracts and service levels"
        count={contracts.length || undefined}
        action={
          canManage ? (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Icon name="plus" className="size-4" />
              Record a contract
            </Button>
          ) : null
        }
      >
        {contracts.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            Nothing recorded. A critical vendor with no recorded right to audit and no breach
            notification window is a vendor you cannot hold to anything.
          </p>
        ) : (
          <ul className="space-y-3">
            {contracts.map((c) => (
              <li key={c.id}>
                <ContractCard contract={c} />
              </li>
            ))}
          </ul>
        )}

        <p className="mt-3 text-caption text-text-subtle">
          Per-metric service levels — uptime targets, response times and their breaches — are
          modelled in the database but have no endpoint yet, so only the contractual windows above
          are shown.
        </p>
      </Panel>

      <AddContractDialog
        open={adding}
        onOpenChange={setAdding}
        vendor={vendor}
        onAdded={onApply}
      />
    </>
  );
}

const CLAUSES = [
  {
    key: "right_to_audit" as const,
    label: "Right to audit",
    why: "Without it you cannot ask to see anything you were not already given.",
  },
  {
    key: "subprocessor_terms" as const,
    label: "Subprocessor terms",
    why: "Without it they can add a fourth party without telling you.",
  },
  {
    key: "exit_data_return_clause" as const,
    label: "Exit data return",
    why: "Without it you have no contractual claim on your data when you leave.",
  },
];

function ContractCard({ contract: c }: { contract: Contract }) {
  const status = CONTRACT_STATUS_META[c.status] ?? { label: c.status, family: "neutral" as const };
  const noticeDays = daysUntil(c.notice_deadline);
  const noticeSoon = noticeDays !== null && noticeDays <= 60;

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-body-md font-semibold text-text-primary">{c.title}</p>
          <p className="mt-0.5 text-caption text-text-subtle">
            {CONTRACT_TYPE_LABEL[c.contract_type] ?? c.contract_type}
            {c.start_date || c.end_date
              ? ` · ${fmtDate(c.start_date)} to ${fmtDate(c.end_date)}`
              : ""}
            {c.value !== null ? ` · ${fmtMoney(c.value)}` : ""}
          </p>
        </div>
        <StatusPill status={status.family} label={status.label} kind="inline" />
      </div>

      {c.auto_renew ? (
        <div
          className={cn(
            "mt-3 rounded-md border p-3",
            noticeSoon
              ? "border-status-warning-border bg-status-warning-bg"
              : "border-border bg-surface-primary",
          )}
        >
          <p
            className={cn(
              "flex items-center gap-1.5 text-label-sm",
              noticeSoon ? "text-status-warning-text" : "text-text-secondary",
            )}
          >
            <Icon name="clock" className="size-4 shrink-0" />
            Renews automatically
          </p>
          <p className="mt-1 text-body-sm text-text-secondary">
            {c.notice_deadline ? (
              <>
                To stop it you have to give notice by{" "}
                <span className="font-semibold text-text-primary">
                  {fmtDate(c.notice_deadline)}
                </span>{" "}
                ({fmtCountdown(noticeDays)})
                {c.notice_period_days !== null ? `, ${c.notice_period_days} days ahead` : ""}.
              </>
            ) : (
              "No notice period is recorded, so nobody knows when the window to stop it closes."
            )}
          </p>
        </div>
      ) : c.renewal_date ? (
        <p className="mt-2 text-body-sm text-text-secondary">
          Up for renewal {fmtDate(c.renewal_date)} ({fmtCountdown(c.renews_in_days)}).
        </p>
      ) : null}

      <div className="mt-3">
        <p className="type-overline">Clauses</p>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {CLAUSES.map((clause) => (
            <Tooltip key={clause.key} content={c[clause.key] ? "Present" : clause.why}>
              <span>
                <Badge variant={c[clause.key] ? "statusPass" : "count"}>
                  {clause.label}
                  {c[clause.key] ? "" : " — missing"}
                </Badge>
              </span>
            </Tooltip>
          ))}
          <Badge variant={c.breach_notification_hours !== null ? "statusPass" : "count"}>
            {c.breach_notification_hours !== null
              ? `Breach notice within ${c.breach_notification_hours}h`
              : "No breach notification window"}
          </Badge>
        </div>
      </div>
    </div>
  );
}

function AddContractDialog({
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
    title: "",
    contract_type: "master",
    engagement_id: "",
    start_date: "",
    end_date: "",
    renewal_date: "",
    auto_renew: false,
    notice_period_days: "",
    breach_notification_hours: "",
    right_to_audit: false,
    subprocessor_terms: false,
    exit_data_return_clause: false,
    value: "",
    status: "active",
  });

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const add = useMutation({
    mutationFn: () =>
      addContract(vendor.id, {
        title: form.title.trim(),
        contract_type: form.contract_type,
        engagement_id: form.engagement_id || null,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        renewal_date: form.renewal_date || null,
        auto_renew: form.auto_renew,
        notice_period_days: form.notice_period_days ? Number(form.notice_period_days) : null,
        breach_notification_hours: form.breach_notification_hours
          ? Number(form.breach_notification_hours)
          : null,
        right_to_audit: form.right_to_audit,
        subprocessor_terms: form.subprocessor_terms,
        exit_data_return_clause: form.exit_data_return_clause,
        value: form.value ? Number(form.value) : null,
        status: form.status,
      }),
    onSuccess: (created) => {
      onAdded({ ...vendor, contracts: [...vendor.contracts, created] });
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
      onOpenChange(false);
      toast({ title: "Contract recorded", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "contract"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody>
        <DialogHeader>
          <DialogTitle>Record a contract</DialogTitle>
          <DialogDescription>
            The clauses matter more than the dates. Tick only what the signed document actually
            says.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (form.title.trim()) add.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="Title"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="Master services agreement 2026"
              autoFocus
            />
            <div className="grid gap-3.5 sm:grid-cols-3">
              <SelectField label="Type">
                <Select value={form.contract_type} onValueChange={(v) => set("contract_type", v)}>
                  <SelectTrigger aria-label="Contract type" />
                  <SelectContent>
                    {CONTRACT_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {CONTRACT_TYPE_LABEL[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <SelectField label="Status">
                <Select value={form.status} onValueChange={(v) => set("status", v)}>
                  <SelectTrigger aria-label="Contract status" />
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="terminated">Terminated</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
              <TextField
                label="Annual value"
                optional
                type="number"
                min={0}
                value={form.value}
                onChange={(e) => set("value", e.target.value)}
              />
            </div>

            <div className="grid gap-3.5 sm:grid-cols-3">
              <TextField
                label="Start"
                optional
                type="date"
                value={form.start_date}
                onChange={(e) => set("start_date", e.target.value)}
              />
              <TextField
                label="End"
                optional
                type="date"
                value={form.end_date}
                onChange={(e) => set("end_date", e.target.value)}
              />
              <TextField
                label="Renewal"
                optional
                type="date"
                value={form.renewal_date}
                onChange={(e) => set("renewal_date", e.target.value)}
              />
            </div>

            <div className="rounded-md border border-border bg-surface-sunken p-3.5">
              <label className="flex items-start gap-2.5">
                <Checkbox
                  checked={form.auto_renew}
                  onCheckedChange={(v) => set("auto_renew", v)}
                />
                <span>
                  <span className="text-body-md text-text-primary">This renews automatically</span>
                  <span className="mt-0.5 block text-caption text-text-subtle">
                    Verity works back from the renewal date to tell you when the window to stop it
                    closes.
                  </span>
                </span>
              </label>
              {form.auto_renew ? (
                <TextField
                  className="mt-3"
                  label="Notice period (days)"
                  type="number"
                  min={0}
                  max={1095}
                  value={form.notice_period_days}
                  onChange={(e) => set("notice_period_days", e.target.value)}
                  placeholder="90"
                />
              ) : null}
            </div>

            <TextField
              label="Breach notification window (hours)"
              optional
              type="number"
              min={0}
              max={8760}
              hint="How long they have to tell you. 72 is the usual number for personal data."
              value={form.breach_notification_hours}
              onChange={(e) => set("breach_notification_hours", e.target.value)}
              placeholder="72"
            />

            <div className="space-y-2.5 rounded-md border border-border bg-surface-sunken p-3.5">
              <p className="type-overline">Clauses present</p>
              {CLAUSES.map((clause) => (
                <label key={clause.key} className="flex items-start gap-2.5">
                  <Checkbox
                    checked={form[clause.key]}
                    onCheckedChange={(v) => set(clause.key, v)}
                  />
                  <span>
                    <span className="text-body-md text-text-primary">{clause.label}</span>
                    <span className="mt-0.5 block text-caption text-text-subtle">{clause.why}</span>
                  </span>
                </label>
              ))}
            </div>

            {vendor.engagements.length > 0 ? (
              <SelectField label="Engagement this covers" optional>
                <Select
                  value={form.engagement_id || "__none__"}
                  onValueChange={(v) => set("engagement_id", v === "__none__" ? "" : v)}
                >
                  <SelectTrigger aria-label="Engagement" />
                  <SelectContent>
                    <SelectItem value="__none__">The whole relationship</SelectItem>
                    {vendor.engagements.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        {e.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={add.isPending} disabled={!form.title.trim()}>
              Record contract
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
