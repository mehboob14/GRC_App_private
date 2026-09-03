import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  ErrorBanner,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  Switch,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import {
  createAsset,
  getAsset,
  listMembers,
  previewCriticality,
  updateAsset,
  type AssetInput,
} from "../api";
import {
  ASSET_TYPES,
  DATA_CLASSIFICATIONS,
  ENVIRONMENTS,
  type AssetDetail,
  type AssetType,
  type CiaRating,
  type DataClassification,
  type Environment,
} from "../types";
import { ASSET_TYPE_META, CLASSIFICATION_META, ENVIRONMENT_LABEL, NEEDS_ASSESSMENT, TIER_META } from "../tokens";

/** High-impact functions carry the criticality boost; the rest are neutral. */
const BUSINESS_FUNCTIONS = [
  "Payment processing",
  "Authentication / IAM",
  "Regulated data (PHI)",
  "Customer data",
  "Financial reporting",
  "Marketing",
  "Internal tooling",
  "Analytics",
  "Other",
];

const VENDOR_SUGGESTIONS = [
  "Microsoft",
  "Amazon Web Services",
  "Google Cloud",
  "Salesforce",
  "Okta",
  "Cloudflare",
  "Datadog",
  "Snowflake",
  "Atlassian",
  "GitHub",
  "Slack",
];

const LOCATION_SUGGESTIONS = ["HQ data center", "Colo — East", "Colo — West", "Remote / cloud-only"];
const NETWORK_SEGMENT_SUGGESTIONS = ["DMZ", "Internal — corp", "Internal — prod", "Guest / isolated"];

/** Which kind of asset carries which fields — the same shape shows only what
 *  it can actually have, so the form fits in fewer rows instead of a long
 *  list of fields that never apply. Presentation only; every field the
 *  backend accepts still submits if it happens to hold a value. */
function fieldsFor(type: AssetType) {
  return {
    hostname: type === "infrastructure" || type === "data" || type === "cloud",
    ip: type === "infrastructure" || type === "data" || type === "cloud" || type === "application",
    vendor: type === "application" || type === "data" || type === "cloud" || type === "third_party",
    location: type === "infrastructure" || type === "data",
    network: type === "infrastructure" || type === "data",
    internetFacing: type !== "third_party",
  };
}

const EMPTY: AssetInput = {
  name: "",
  asset_type: "application",
  description: "",
  hostname: null,
  ip_address: null,
  environment: null,
  location: null,
  vendor_ref: null,
  data_classification: null,
  regulated_data_type: null,
  compliance_scope: [],
  internet_facing: false,
  customer_facing: false,
  network_segment: null,
  business_function: null,
  confidentiality: null,
  integrity: null,
  availability: null,
  tier_override: null,
  tier_override_reason: null,
  primary_owner_id: null,
  secondary_owner_id: null,
  business_owner_id: null,
  custodian_id: null,
  escalation_contact_id: null,
  owning_team: null,
  valuation: null,
  business_impact_notes: null,
  operational_dependency_rating: null,
};

const NONE = "__none__";

function fromDetail(a: AssetDetail): AssetInput {
  return {
    name: a.name,
    asset_type: a.asset_type,
    description: a.description,
    hostname: a.hostname,
    ip_address: a.ip_address,
    environment: a.environment,
    location: a.location,
    vendor_ref: a.vendor_ref,
    data_classification: a.data_classification,
    regulated_data_type: a.regulated_data_type,
    compliance_scope: a.compliance_scope,
    internet_facing: a.internet_facing,
    customer_facing: a.customer_facing,
    network_segment: a.network_segment,
    business_function: a.business_function,
    confidentiality: a.criticality.confidentiality,
    integrity: a.criticality.integrity,
    availability: a.criticality.availability,
    tier_override: a.criticality.tier_override,
    tier_override_reason: a.criticality.tier_override_reason,
    primary_owner_id: a.ownership.primary_owner?.membership_id ?? null,
    secondary_owner_id: a.ownership.secondary_owner?.membership_id ?? null,
    business_owner_id: a.ownership.business_owner?.membership_id ?? null,
    custodian_id: a.ownership.custodian?.membership_id ?? null,
    escalation_contact_id: a.ownership.escalation_contact?.membership_id ?? null,
    owning_team: a.ownership.owning_team,
    valuation: a.valuation,
    business_impact_notes: a.business_impact_notes,
    operational_dependency_rating: a.operational_dependency_rating,
  };
}

/**
 * Add/edit an asset in a dense right-side drawer instead of a full page — a
 * register action should not cost a navigation. Two-across fields and a
 * type-aware field set keep the whole form to roughly one scroll, matching
 * the reference layout in C:\...\GRC-Tenant\grc-frontend's asset modal.
 *
 * Every field here already exists on `AssetInput` (rule: no schema change for
 * a presentation pass) — the reference's OS/hardware/CIS-benchmark and
 * procurement fields have no equivalent in Verity's asset model and are not
 * reproduced; PCI/HIPAA "scope" is Verity's existing free-text
 * `compliance_scope` array, toggled here rather than typed.
 */
export function AssetFormDrawer({
  open,
  onOpenChange,
  assetId,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present = edit that asset; absent = create. */
  assetId?: string;
  onSaved: (asset: AssetDetail) => void;
}) {
  const { toast } = useToast();
  const editing = Boolean(assetId);
  const [form, setForm] = useState<AssetInput>(EMPTY);
  const set = <K extends keyof AssetInput>(key: K, value: AssetInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const membersQuery = useQuery({ queryKey: ["asset-members"], queryFn: listMembers, enabled: open });
  const existingQuery = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId!),
    enabled: open && editing,
  });

  // Fresh form each time the drawer opens for a NEW asset; the existing
  // asset's data once it loads for an edit.
  useEffect(() => {
    if (!open) return;
    if (!editing) {
      setForm(EMPTY);
      return;
    }
    if (existingQuery.data) setForm(fromDetail(existingQuery.data));
  }, [open, editing, existingQuery.data]);

  const preview = useMemo(
    () =>
      previewCriticality({
        confidentiality: form.confidentiality,
        integrity: form.integrity,
        availability: form.availability,
        internet_facing: form.internet_facing,
        data_classification: form.data_classification,
        business_function: form.business_function,
      }),
    [form.confidentiality, form.integrity, form.availability, form.internet_facing, form.data_classification, form.business_function],
  );
  const effectiveTier = form.tier_override ?? preview?.tier ?? null;
  const tierMeta = effectiveTier ? TIER_META[effectiveTier] : NEEDS_ASSESSMENT;

  const save = useMutation({
    mutationFn: () => (editing ? updateAsset(assetId!, form) : createAsset(form)),
    onSuccess: (a) => {
      toast({ title: editing ? "Asset updated" : "Asset added", tone: "success" });
      onSaved(a);
      onOpenChange(false);
    },
    onError: (error) => toast({ title: errorToast(error, "asset"), tone: "danger" }),
  });

  const members = membersQuery.data ?? [];
  const show = fieldsFor(form.asset_type);
  const hasPci = form.compliance_scope.includes("PCI-DSS");
  const hasHipaa = form.compliance_scope.includes("HIPAA");
  const toggleScope = (tag: string, on: boolean) =>
    set("compliance_scope", on ? [...form.compliance_scope, tag] : form.compliance_scope.filter((s) => s !== tag));

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent size="xl" className="text-body-sm">
        <DrawerHeader className="py-3.5">
          <DrawerTitle className="text-title-md">{editing ? "Edit asset" : "Add asset"}</DrawerTitle>
        </DrawerHeader>

        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            if (form.name.trim()) save.mutate();
          }}
        >
          <DrawerBody className="space-y-3.5">
            {editing && existingQuery.isError ? (
              <ErrorBanner title="Couldn't load this asset" />
            ) : null}

            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <TextField label="Name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Customer billing platform" />
              <TextField label="Description" optional value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="Brief description…" />
            </div>

            <div>
              <span className="mb-1 block text-label-sm text-text-secondary">Asset type</span>
              <div className="grid grid-cols-3 gap-1.5">
                {ASSET_TYPES.map((t) => {
                  const meta = ASSET_TYPE_META[t];
                  const selected = form.asset_type === t;
                  return (
                    <button
                      key={t}
                      type="button"
                      onClick={() => set("asset_type", t)}
                      className={
                        "flex items-center gap-2 rounded-sm border px-2.5 py-2 text-left transition-colors duration-80 ease-state " +
                        (selected
                          ? "border-action-accent-border bg-action-accent-tint"
                          : "border-border bg-surface-primary hover:border-border-strong hover:bg-surface-hover")
                      }
                    >
                      <Icon name={meta.icon} className={"size-4 shrink-0 " + (selected ? "text-action-accent" : "text-text-subtle")} />
                      <span className={"truncate text-caption font-semibold " + (selected ? "text-action-accent" : "text-text-secondary")}>
                        {meta.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              {show.hostname ? (
                <TextField label="Hostname" optional value={form.hostname ?? ""} onChange={(e) => set("hostname", e.target.value || null)} />
              ) : null}
              {show.ip ? (
                <TextField label="IP address" optional value={form.ip_address ?? ""} onChange={(e) => set("ip_address", e.target.value || null)} placeholder="e.g. 10.0.10.15" />
              ) : null}
              <SelectField label="Environment" optional>
                <Select value={form.environment ?? NONE} onValueChange={(v) => set("environment", v === NONE ? null : (v as Environment))}>
                  <SelectTrigger aria-label="Environment" />
                  <SelectContent>
                    <SelectItem value={NONE}>—</SelectItem>
                    {ENVIRONMENTS.map((e) => (
                      <SelectItem key={e} value={e}>
                        {ENVIRONMENT_LABEL[e]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            </div>

            <div className="border-t border-border pt-3.5">
              <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                {show.vendor ? (
                  <ComboField label="Vendor" listId="vendor-suggestions" options={VENDOR_SUGGESTIONS} value={form.vendor_ref ?? ""} onChange={(v) => set("vendor_ref", v || null)} placeholder="Search or type a vendor…" />
                ) : null}
                {show.location ? (
                  <ComboField label="Location" listId="location-suggestions" options={LOCATION_SUGGESTIONS} value={form.location ?? ""} onChange={(v) => set("location", v || null)} placeholder="Search or type a location…" />
                ) : null}
              </div>

              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
                <div>
                  <label htmlFor="asset-value" className="mb-1.5 block text-label-sm text-text-secondary">
                    Asset value (USD)
                  </label>
                  <div className="relative">
                    <Icon name="dollar" className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-text-subtle" />
                    <input
                      id="asset-value"
                      type="number"
                      min={0}
                      className="h-9 w-full rounded-sm border border-border bg-surface-primary pl-8 pr-3 font-sans text-body-md text-text-primary transition-colors duration-150 ease-state placeholder:text-text-faint focus:outline-none focus-visible:outline-none focus-visible:border-action-accent"
                      value={form.valuation != null ? String(form.valuation) : ""}
                      onChange={(e) => set("valuation", e.target.value ? Number(e.target.value) : null)}
                      placeholder="0"
                    />
                  </div>
                </div>
                {show.network ? (
                  <ComboField label="Network segment" listId="network-suggestions" options={NETWORK_SEGMENT_SUGGESTIONS} value={form.network_segment ?? ""} onChange={(v) => set("network_segment", v || null)} placeholder="Search or type a segment…" />
                ) : null}
              </div>

              <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3">
                <ScopeToggle label="PCI DSS scope" sublabel="Cardholder data environment" checked={hasPci} onChange={(v) => toggleScope("PCI-DSS", v)} />
                <ScopeToggle label="HIPAA scope" sublabel="ePHI environment" checked={hasHipaa} onChange={(v) => toggleScope("HIPAA", v)} />
              </div>
              {hasPci || hasHipaa ? (
                <div className="mt-3">
                  <TextField
                    label="Regulated data type"
                    optional
                    value={form.regulated_data_type ?? ""}
                    onChange={(e) => set("regulated_data_type", e.target.value || null)}
                    placeholder="e.g. cardholder_data, ePHI"
                  />
                </div>
              ) : null}

              <div className="mt-3.5">
                <span className="mb-1 block text-label-sm text-text-secondary">
                  CIA ratings <span className="font-normal text-text-faint">(highest drives criticality)</span>
                </span>
                <div className="grid grid-cols-3 gap-3">
                  <CiaPills label="Confidentiality" value={form.confidentiality} onChange={(v) => set("confidentiality", v)} tone="accent" />
                  <CiaPills label="Integrity" value={form.integrity} onChange={(v) => set("integrity", v)} tone="success" />
                  <CiaPills label="Availability" value={form.availability} onChange={(v) => set("availability", v)} tone="warning" />
                </div>
                <div className="mt-2 flex h-7 items-center gap-2">
                  {effectiveTier ? (
                    <>
                      <StatusPill status={tierMeta.family} label={tierMeta.label} />
                      {preview ? <span className="tabular text-caption text-text-subtle">{preview.score.toFixed(1)}</span> : null}
                    </>
                  ) : (
                    <span className="text-caption text-text-subtle">Not rated — leave CIA blank to keep this asset unassessed</span>
                  )}
                </div>
              </div>

              <div className="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-3">
                <SelectField label="Data classification" optional>
                  <Select value={form.data_classification ?? NONE} onValueChange={(v) => set("data_classification", v === NONE ? null : (v as DataClassification))}>
                    <SelectTrigger aria-label="Data classification" />
                    <SelectContent>
                      <SelectItem value={NONE}>None — search to pick…</SelectItem>
                      {DATA_CLASSIFICATIONS.map((c) => (
                        <SelectItem key={c} value={c}>
                          {CLASSIFICATION_META[c].label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                {show.internetFacing ? (
                  <ScopeToggle
                    label="Internet-facing"
                    sublabel={form.internet_facing ? "Exposed to the public internet" : "Internal only"}
                    checked={form.internet_facing}
                    onChange={(v) => set("internet_facing", v)}
                  />
                ) : null}
              </div>
              <div className="mt-3">
                <label className="flex cursor-pointer items-center gap-2.5">
                  <Checkbox checked={form.customer_facing} onCheckedChange={(v) => set("customer_facing", Boolean(v))} aria-label="Customer-facing" />
                  <span className="text-body-sm text-text-primary">Customer-facing</span>
                </label>
              </div>

              <div className="mt-3.5">
                <ComboField label="Business function" listId="business-function-suggestions" options={BUSINESS_FUNCTIONS} value={form.business_function ?? ""} onChange={(v) => set("business_function", v || null)} placeholder="Search or type a function…" />
              </div>

              <div className="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-3">
                <MemberSelect label="Owner" value={form.primary_owner_id} onChange={(v) => set("primary_owner_id", v)} members={members} />
                <MemberSelect label="Secondary owner" value={form.secondary_owner_id} onChange={(v) => set("secondary_owner_id", v)} members={members} />
                <MemberSelect label="Business owner" value={form.business_owner_id} onChange={(v) => set("business_owner_id", v)} members={members} />
                <MemberSelect label="Custodian" value={form.custodian_id} onChange={(v) => set("custodian_id", v)} members={members} />
                <MemberSelect label="Escalation contact" value={form.escalation_contact_id} onChange={(v) => set("escalation_contact_id", v)} members={members} />
                {/* Owning team is intentionally absent: the API stores it as a
                    group reference, so a free-text name here would silently not
                    save. It returns as a group picker. */}
              </div>
              {membersQuery.isError ? (
                <p className="mt-2 text-caption text-status-danger-text">Couldn't load the team list.</p>
              ) : null}
            </div>
          </DrawerBody>

          <DrawerFooter>
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending} disabled={form.name.trim() === ""}>
              {editing ? "Save changes" : "Add asset"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

function ComboField({
  label,
  listId,
  options,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  listId: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <TextField label={label} optional list={listId} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      <datalist id={listId}>
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </div>
  );
}

function ScopeToggle({
  label,
  sublabel,
  checked,
  onChange,
}: {
  label: string;
  sublabel?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div>
      <span className="mb-1 block text-label-sm text-text-secondary">{label}</span>
      <label className="flex cursor-pointer items-center gap-2">
        <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
        <span className="text-caption text-text-subtle">{sublabel}</span>
      </label>
    </div>
  );
}

const CIA_TONE: Record<"accent" | "success" | "warning", string> = {
  accent: "bg-action-accent",
  success: "bg-status-success-base",
  warning: "bg-status-warning-base",
};

function CiaPills({
  label,
  value,
  onChange,
  tone,
}: {
  label: string;
  value: CiaRating | null;
  onChange: (v: CiaRating | null) => void;
  tone: "accent" | "success" | "warning";
}) {
  return (
    <div>
      <span className="mb-1 block text-caption text-text-subtle">{label}</span>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => {
          const selected = value === n;
          return (
            <button
              key={n}
              type="button"
              // Tapping the active rating again clears it — "not rated" is a
              // real state (rule: no phantom defaults), not just the absence
              // of a click, so it needs a way back without a separate control.
              onClick={() => onChange(selected ? null : (n as CiaRating))}
              aria-pressed={selected}
              className={
                "flex h-6 w-6 items-center justify-center rounded-sm border text-caption font-semibold transition-colors duration-80 ease-state " +
                (selected ? `${CIA_TONE[tone]} border-transparent text-white` : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover")
              }
            >
              {n}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MemberSelect({
  label,
  value,
  onChange,
  members,
}: {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  members: { membership_id: string; name: string }[];
}) {
  return (
    <SelectField label={label} optional>
      <Select value={value ?? NONE} onValueChange={(v) => onChange(v === NONE ? null : v)}>
        <SelectTrigger aria-label={label} />
        <SelectContent>
          <SelectItem value={NONE}>Unassigned</SelectItem>
          {members.map((m) => (
            <SelectItem key={m.membership_id} value={m.membership_id}>
              {m.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </SelectField>
  );
}
