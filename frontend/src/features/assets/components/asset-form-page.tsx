import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { createAsset, listMembers, getAsset, previewCriticality, updateAsset, type AssetInput } from "../api";
import {
  ASSET_TYPES,
  CRITICALITY_TIERS,
  DATA_CLASSIFICATIONS,
  ENVIRONMENTS,
  type AssetType,
  type CiaRating,
  type CriticalityTier,
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

export function AssetFormPage() {
  const { assetId } = useParams();
  const editing = Boolean(assetId);
  const navigate = useNavigate();
  const { toast } = useToast();

  const [form, setForm] = useState<AssetInput>(EMPTY);
  const set = <K extends keyof AssetInput>(key: K, value: AssetInput[K]) => setForm((f) => ({ ...f, [key]: value }));

  const membersQuery = useQuery({ queryKey: ["asset-members"], queryFn: listMembers });
  const existingQuery = useQuery({ queryKey: ["asset", assetId], queryFn: () => getAsset(assetId!), enabled: editing });

  useEffect(() => {
    const a = existingQuery.data;
    if (!a) return;
    setForm({
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
    });
  }, [existingQuery.data]);

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

  const save = useMutation({
    mutationFn: () => (editing ? updateAsset(assetId!, form) : createAsset(form)),
    onSuccess: (a) => {
      toast({ title: editing ? "Asset updated" : "Asset created", tone: "success" });
      navigate(`/assets/${a.id}`);
    },
    onError: () => toast({ title: "Couldn’t save the asset.", tone: "danger" }),
  });

  const members = membersQuery.data ?? [];
  const back = editing ? `/assets/${assetId}` : "/assets";
  const effectiveTier = form.tier_override ?? preview?.tier ?? null;
  const tierMeta = effectiveTier ? TIER_META[effectiveTier] : NEEDS_ASSESSMENT;

  return (
    <div className="mx-auto max-w-[900px] pb-16">
      <Link to={back} className="inline-flex items-center gap-1.5 text-body-sm text-text-link hover:underline">
        <Icon name="arrowl" className="size-4" />
        {editing ? "Back to asset" : "Back to inventory"}
      </Link>
      <h1 className="mt-3 font-display text-heading-lg text-text-primary">{editing ? "Edit asset" : "New asset"}</h1>

      <form
        className="mt-6 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (form.name.trim()) save.mutate();
        }}
      >
        <Section title="Identity">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Customer billing platform" />
            <SelectField label="Type">
              <Select value={form.asset_type} onValueChange={(v) => set("asset_type", v as AssetType)}>
                <SelectTrigger aria-label="Type" />
                <SelectContent>
                  {ASSET_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {ASSET_TYPE_META[t].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          </div>
          <TextField label="Description" optional value={form.description} onChange={(e) => set("description", e.target.value)} />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Hostname" optional value={form.hostname ?? ""} onChange={(e) => set("hostname", e.target.value || null)} />
            <TextField label="IP address" optional value={form.ip_address ?? ""} onChange={(e) => set("ip_address", e.target.value || null)} />
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
            <TextField label="Location" optional value={form.location ?? ""} onChange={(e) => set("location", e.target.value || null)} />
          </div>
        </Section>

        <Section title="Classification & exposure">
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField label="Data classification" optional>
              <Select value={form.data_classification ?? NONE} onValueChange={(v) => set("data_classification", v === NONE ? null : (v as DataClassification))}>
                <SelectTrigger aria-label="Data classification" />
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {DATA_CLASSIFICATIONS.map((c) => (
                    <SelectItem key={c} value={c}>
                      {CLASSIFICATION_META[c].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Business function" optional>
              <Select value={form.business_function ?? NONE} onValueChange={(v) => set("business_function", v === NONE ? null : v)}>
                <SelectTrigger aria-label="Business function" />
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {BUSINESS_FUNCTIONS.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextField label="Regulated data type" optional value={form.regulated_data_type ?? ""} onChange={(e) => set("regulated_data_type", e.target.value || null)} placeholder="e.g. cardholder_data" />
            <TextField
              label="Compliance scope"
              optional
              value={form.compliance_scope.join(", ")}
              onChange={(e) => set("compliance_scope", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
              placeholder="SOC2, PCI"
            />
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <label className="flex cursor-pointer items-center gap-2.5">
              <Checkbox checked={form.internet_facing} onCheckedChange={(v) => set("internet_facing", Boolean(v))} aria-label="Internet-facing" />
              <span className="text-body-sm text-text-primary">Internet-facing</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2.5">
              <Checkbox checked={form.customer_facing} onCheckedChange={(v) => set("customer_facing", Boolean(v))} aria-label="Customer-facing" />
              <span className="text-body-sm text-text-primary">Customer-facing</span>
            </label>
          </div>
        </Section>

        <Section title="Criticality">
          <div className="grid gap-4 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <CiaSelect label="Confidentiality" value={form.confidentiality} onChange={(v) => set("confidentiality", v)} />
            <CiaSelect label="Integrity" value={form.integrity} onChange={(v) => set("integrity", v)} />
            <CiaSelect label="Availability" value={form.availability} onChange={(v) => set("availability", v)} />
            <div className="flex flex-col gap-1.5">
              <span className="text-label-sm text-text-secondary">Computed</span>
              <div className="flex h-9 items-center gap-2">
                {effectiveTier ? (
                  <>
                    <StatusPill status={tierMeta.family} label={tierMeta.label} />
                    {preview ? <span className="tabular text-caption text-text-subtle">{preview.score.toFixed(1)}</span> : null}
                  </>
                ) : (
                  <span className="text-body-sm text-text-subtle">Not rated</span>
                )}
              </div>
            </div>
          </div>
          <p className="text-caption text-text-subtle">
            Score is the highest CIA rating, adjusted for internet exposure and data sensitivity. Leave CIA blank to keep the asset unassessed.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField label="Override tier" optional>
              <Select value={form.tier_override ?? NONE} onValueChange={(v) => set("tier_override", v === NONE ? null : (v as CriticalityTier))}>
                <SelectTrigger aria-label="Override tier" />
                <SelectContent>
                  <SelectItem value={NONE}>No override</SelectItem>
                  {CRITICALITY_TIERS.map((t) => (
                    <SelectItem key={t} value={t}>
                      {TIER_META[t].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            {form.tier_override ? (
              <TextField label="Override reason" value={form.tier_override_reason ?? ""} onChange={(e) => set("tier_override_reason", e.target.value || null)} />
            ) : null}
          </div>
        </Section>

        <Section title="Ownership">
          <div className="grid gap-4 sm:grid-cols-2">
            <MemberSelect label="Primary owner" value={form.primary_owner_id} onChange={(v) => set("primary_owner_id", v)} members={members} />
            <MemberSelect label="Secondary owner" value={form.secondary_owner_id} onChange={(v) => set("secondary_owner_id", v)} members={members} />
            <MemberSelect label="Business owner" value={form.business_owner_id} onChange={(v) => set("business_owner_id", v)} members={members} />
            <MemberSelect label="Custodian" value={form.custodian_id} onChange={(v) => set("custodian_id", v)} members={members} />
            <MemberSelect label="Escalation contact" value={form.escalation_contact_id} onChange={(v) => set("escalation_contact_id", v)} members={members} />
            <TextField label="Owning team" optional value={form.owning_team ?? ""} onChange={(e) => set("owning_team", e.target.value || null)} />
          </div>
        </Section>

        <Section title="Business context">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Valuation (USD)"
              optional
              value={form.valuation != null ? String(form.valuation) : ""}
              onChange={(e) => set("valuation", e.target.value ? Number(e.target.value.replace(/[^0-9.]/g, "")) || null : null)}
              placeholder="e.g. 180000"
            />
            <SelectField label="Operational dependency" optional>
              <Select
                value={form.operational_dependency_rating ?? NONE}
                onValueChange={(v) => set("operational_dependency_rating", v === NONE ? null : v)}
              >
                <SelectTrigger aria-label="Operational dependency" />
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {["very_high", "high", "medium", "low"].map((r) => (
                    <SelectItem key={r} value={r}>
                      {r.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          </div>
          <TextField label="Business impact notes" optional value={form.business_impact_notes ?? ""} onChange={(e) => set("business_impact_notes", e.target.value || null)} />
        </Section>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => navigate(back)}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={form.name.trim() === ""}>
            {editing ? "Save changes" : "Create asset"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function CiaSelect({ label, value, onChange }: { label: string; value: CiaRating | null; onChange: (v: CiaRating | null) => void }) {
  return (
    <SelectField label={label} optional>
      <Select value={value != null ? String(value) : NONE} onValueChange={(v) => onChange(v === NONE ? null : (Number(v) as CiaRating))}>
        <SelectTrigger aria-label={label} />
        <SelectContent>
          <SelectItem value={NONE}>Not rated</SelectItem>
          {[1, 2, 3, 4, 5].map((n) => (
            <SelectItem key={n} value={String(n)}>
              {n}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </SelectField>
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4 rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
      {children}
    </section>
  );
}
