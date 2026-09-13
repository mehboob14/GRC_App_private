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
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { reviewSocReport } from "../api";
import type { SocReview, VendorDetail } from "../types";
import { fmtDate, OPINION_META, REPORT_KIND_LABEL, REPORT_TYPE_LABEL } from "../tokens";
import { Panel } from "./panel";

/** The five Trust Services Criteria, in the order a SOC 2 report lists them. */
const TSC = [
  { key: "security", label: "Security" },
  { key: "availability", label: "Availability" },
  { key: "processing_integrity", label: "Processing integrity" },
  { key: "confidentiality", label: "Confidentiality" },
  { key: "privacy", label: "Privacy" },
];

/**
 * A SOC report read back as a summary an auditor could accept, not a form dump.
 *
 * The two facts that decide whether the report is worth anything lead: the
 * opinion, and whether the findings were material. Everything else — period,
 * criteria, subservice organisations, complementary user entity controls — is
 * supporting detail and reads as such.
 */
export function SocReviewPanel({
  vendor,
  canAssess,
  onApply,
}: {
  vendor: VendorDetail;
  canAssess: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const [recording, setRecording] = useState(false);
  const reviews = vendor.soc_reviews;

  return (
    <>
      <Panel
        title="Assurance reports"
        count={reviews.length || undefined}
        action={
          canAssess ? (
            <Button variant="secondary" size="sm" onClick={() => setRecording(true)}>
              <Icon name="plus" className="size-4" />
              Record review
            </Button>
          ) : null
        }
      >
        {reviews.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            No assurance reports reviewed yet.
          </p>
        ) : (
          <ul className="space-y-4">
            {reviews.map((r) => (
              <li key={r.id}>
                <SocReviewCard review={r} />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <RecordDialog
        open={recording}
        onOpenChange={setRecording}
        vendor={vendor}
        onRecorded={onApply}
      />
    </>
  );
}

function SocReviewCard({ review: r }: { review: SocReview }) {
  const opinion = OPINION_META[r.opinion] ?? {
    label: r.opinion,
    family: "neutral" as const,
    blurb: "",
  };

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-4">
      {/* The verdict first. A reader who stops after one line should still have
          the answer to "can we rely on this". */}
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={opinion.family} label={`${opinion.label} opinion`} />
        {r.findings_material ? (
          <StatusPill status="danger" label="Material findings" />
        ) : (
          <StatusPill status="success" label="No material findings" kind="inline" />
        )}
        <span className="text-caption text-text-subtle">
          {REPORT_KIND_LABEL[r.report_kind] ?? r.report_kind}{" "}
          {REPORT_TYPE_LABEL[r.report_type] ?? r.report_type}
          {r.cpa_firm ? ` · ${r.cpa_firm}` : ""}
        </span>
      </div>
      <p className="mt-1.5 text-body-md text-text-secondary">{opinion.blurb}</p>

      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-caption text-text-subtle">Period covered</dt>
          <dd className="mt-0.5 text-body-sm text-text-primary">
            {r.audit_period_start || r.audit_period_end
              ? `${fmtDate(r.audit_period_start)} to ${fmtDate(r.audit_period_end)}`
              : "Not recorded"}
            {r.period_is_stale ? (
              <>
                , <span className="text-status-warning-text">too old to rely on alone</span>
              </>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-caption text-text-subtle">Bridge letter</dt>
          <dd className="mt-0.5 text-body-sm text-text-primary">
            {r.bridge_letter_received
              ? "Received"
              : r.needs_bridge_letter
                ? "Needed and not received"
                : "Not needed"}
          </dd>
        </div>
      </dl>

      {r.tsc_included.length > 0 ? (
        <div className="mt-3">
          <p className="type-overline">Criteria in scope</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {TSC.map((c) => (
              <Badge
                key={c.key}
                variant={r.tsc_included.includes(c.key) ? "statusPass" : "neutral"}
              >
                {c.label}
                {r.tsc_included.includes(c.key) ? "" : ": not covered"}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {r.subservice_orgs ? (
        <div className="mt-3">
          <p className="type-overline">Subservice organisations</p>
          <p className="mt-1 text-body-sm text-text-secondary">{r.subservice_orgs}</p>
        </div>
      ) : null}

      <div className="mt-3">
        <p className="type-overline">Complementary user entity controls</p>
        <p className="mt-1 flex items-start gap-1.5 text-body-sm text-text-secondary">
          <Icon
            name={r.cuec_reviewed ? "check" : "alert"}
            className={`mt-0.5 size-4 shrink-0 ${r.cuec_reviewed ? "text-status-success-base" : "text-status-warning-base"}`}
          />
          <span>
            {r.cuec_reviewed
              ? (r.cuec_notes ?? "Reviewed. No notes recorded.")
              : "Not reviewed. The opinion only covers us if we operate these."}
          </span>
        </p>
      </div>

      {r.reviewed_at ? (
        <p className="mt-3 text-caption text-text-subtle">Reviewed {fmtDate(r.reviewed_at)}</p>
      ) : null}
    </div>
  );
}

function RecordDialog({
  open,
  onOpenChange,
  vendor,
  onRecorded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor: VendorDetail;
  onRecorded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    report_kind: "soc2",
    report_type: "type_ii",
    document_id: "",
    audit_period_start: "",
    audit_period_end: "",
    opinion: "unqualified",
    bridge_letter_received: false,
    findings_material: false,
    cuec_reviewed: false,
    cuec_notes: "",
    subservice_orgs: "",
    cpa_firm: "",
  });
  const [tsc, setTsc] = useState<string[]>(["security"]);

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const record = useMutation({
    mutationFn: () =>
      reviewSocReport(vendor.id, {
        report_kind: form.report_kind,
        report_type: form.report_type,
        document_id: form.document_id || null,
        audit_period_start: form.audit_period_start || null,
        audit_period_end: form.audit_period_end || null,
        tsc_included: tsc,
        opinion: form.opinion,
        bridge_letter_received: form.bridge_letter_received,
        findings_material: form.findings_material,
        cuec_reviewed: form.cuec_reviewed,
        cuec_notes: form.cuec_notes.trim() || null,
        subservice_orgs: form.subservice_orgs.trim() || null,
        cpa_firm: form.cpa_firm.trim() || null,
      }),
    onSuccess: (created) => {
      onRecorded({ ...vendor, soc_reviews: [created, ...vendor.soc_reviews] });
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
      onOpenChange(false);
      toast({ title: "Report review recorded", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "report review"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody>
        <DialogHeader>
          <DialogTitle>Record report review</DialogTitle>
          <DialogDescription>Opinion and material findings drive lifecycle checks.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            record.mutate();
          }}
        >
          <DialogBody className="space-y-4">
            <div className="grid gap-3.5 sm:grid-cols-3">
              <SelectField label="Report">
                <Select value={form.report_kind} onValueChange={(v) => set("report_kind", v)}>
                  <SelectTrigger aria-label="Report kind" />
                  <SelectContent>
                    <SelectItem value="soc1">SOC 1</SelectItem>
                    <SelectItem value="soc2">SOC 2</SelectItem>
                    <SelectItem value="soc3">SOC 3</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
              <SelectField label="Type">
                <Select value={form.report_type} onValueChange={(v) => set("report_type", v)}>
                  <SelectTrigger aria-label="Report type" />
                  <SelectContent>
                    <SelectItem value="type_i">Type I: design only</SelectItem>
                    <SelectItem value="type_ii">Type II: design and operation</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
              <TextField
                label="Audit firm"
                optional
                value={form.cpa_firm}
                onChange={(e) => set("cpa_firm", e.target.value)}
              />
            </div>

            <SelectField label="Opinion">
              <Select value={form.opinion} onValueChange={(v) => set("opinion", v)}>
                <SelectTrigger aria-label="Opinion" />
                <SelectContent>
                  {Object.entries(OPINION_META).map(([value, meta]) => (
                    <SelectItem key={value} value={value}>
                      {meta.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>

            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Period from"
                optional
                type="date"
                value={form.audit_period_start}
                onChange={(e) => set("audit_period_start", e.target.value)}
              />
              <TextField
                label="Period to"
                optional
                type="date"
                hint="Old periods need a bridge letter."
                value={form.audit_period_end}
                onChange={(e) => set("audit_period_end", e.target.value)}
              />
            </div>

            {vendor.documents.length > 0 ? (
              <SelectField label="Report document" optional>
                <Select
                  value={form.document_id || "__none__"}
                  onValueChange={(v) => set("document_id", v === "__none__" ? "" : v)}
                >
                  <SelectTrigger aria-label="Document" />
                  <SelectContent>
                    <SelectItem value="__none__">Not linked</SelectItem>
                    {vendor.documents.map((d) => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            ) : null}

            <div>
              <p className="mb-1.5 font-sans text-label-sm text-text-secondary">
                Criteria covered
              </p>
              <div className="flex flex-wrap gap-x-4 gap-y-2">
                {TSC.map((c) => (
                  <label key={c.key} className="flex items-center gap-2">
                    <Checkbox
                      checked={tsc.includes(c.key)}
                      onCheckedChange={(on) =>
                        setTsc((all) => (on ? [...all, c.key] : all.filter((k) => k !== c.key)))
                      }
                    />
                    <span className="text-body-md text-text-primary">{c.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2.5 rounded-md border border-border bg-surface-sunken p-3.5">
              <label className="flex items-start gap-2.5">
                <Checkbox
                  checked={form.findings_material}
                  onCheckedChange={(v) => set("findings_material", v)}
                />
                <span>
                  <span className="text-body-md text-text-primary">
                    Exceptions were material
                  </span>
                  <span className="mt-0.5 block text-caption text-text-subtle">
                    Blocks the lifecycle assurance check.
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-2.5">
                <Checkbox
                  checked={form.bridge_letter_received}
                  onCheckedChange={(v) => set("bridge_letter_received", v)}
                />
                <span className="text-body-md text-text-primary">
                  Bridge letter received
                </span>
              </label>
              <label className="flex items-start gap-2.5">
                <Checkbox
                  checked={form.cuec_reviewed}
                  onCheckedChange={(v) => set("cuec_reviewed", v)}
                />
                <span className="text-body-md text-text-primary">
                  Complementary user entity controls reviewed
                </span>
              </label>
            </div>

            {form.cuec_reviewed ? (
              <TextArea
                label="What we must do on our side"
                optional
                value={form.cuec_notes}
                onChange={(e) => set("cuec_notes", e.target.value)}
                rows={3}
                maxLength={8000}
                placeholder="Enforce MFA on admin accounts, rotate the API key yearly"
              />
            ) : null}

            <TextArea
              label="Subservice organisations"
              optional
              hint="Note whether each is carved out or included."
              value={form.subservice_orgs}
              onChange={(e) => set("subservice_orgs", e.target.value)}
              rows={2}
              maxLength={4000}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={record.isPending}>
              Record review
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
