import { useDeferredValue, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
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
  DetailHeader,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  ErrorState,
  Icon,
  SearchInput,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextField,
  useToast,
  TabStrip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  addRelationship,
  decommissionAsset,
  deleteRelationship,
  getAsset,
  listAssets,
  recordReview,
  transitionAsset,
} from "../api";
import {
  type AssetRelationship, HYGIENE_FLAGS, RELATIONSHIP_TYPES } from "../types";
import type { AssetDetail, AssetStatus, HygieneFlag, RelationshipType } from "../types";
import { customFieldText } from "@/features/custom-fields/format";
import { useCustomFields } from "@/features/custom-fields/hooks";
import { AssetFormDrawer } from "./asset-form-drawer";
import { linkVulnerabilityAsset, listVulnerabilities } from "@/features/vulnerabilities/api";
import { AddFindingDrawer } from "@/features/vulnerabilities/components/add-finding-drawer";
import { LinkedRecordsPanel } from "@/features/linkage/components/linked-records-panel";
import { useLinkedRecords } from "@/features/linkage/hooks";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { SeverityBadge } from "@/features/vulnerabilities/components/severity-badge";
import {
  ASSET_TYPE_META,
  CLASSIFICATION_META,
  ENVIRONMENT_LABEL,
  NEEDS_ASSESSMENT,
  STATUS_META,
  TIER_META,
  displayTier,
  fmtDate,
  fmtMoney,
  relativeTime,
} from "../tokens";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const humanize = (s: string) => s.replace(/_/g, " ");

const PRIMARY_NEXT: Record<AssetStatus, AssetStatus | null> = {
  planned: "active",
  active: "in_maintenance",
  in_maintenance: "active",
  decommissioned: "retired",
  retired: null,
};

function lifecycleLabel(from: AssetStatus, to: AssetStatus): string {
  if (to === "active") return from === "planned" ? "Activate" : "Return to service";
  if (to === "in_maintenance") return "Start maintenance";
  if (to === "decommissioned") return "Decommission";
  if (to === "retired") return "Retire";
  return cap(humanize(to));
}

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "criticality", label: "Criticality" },
  { id: "ownership", label: "Ownership" },
  { id: "lifecycle", label: "Lifecycle" },
  { id: "vulnerabilities", label: "Vulnerabilities" },
  { id: "relationships", label: "Relationships" },
  { id: "linked", label: "Linked records" },
  { id: "activity", label: "Activity" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function AssetDetailPage() {
  const { assetId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabId>("overview");
  const [transition, setTransition] = useState<AssetStatus | null>(null);
  const [editing, setEditing] = useState(false);

  const query = useQuery({ queryKey: ["asset", assetId], queryFn: () => getAsset(assetId), enabled: assetId.length > 0 });
  const a = query.data;
  const linksQuery = useLinkedRecords("asset", assetId);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
    void queryClient.invalidateQueries({ queryKey: ["assets"] });
    void queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
    void queryClient.invalidateQueries({ queryKey: ["asset-facets"] });
  };

  if (query.isLoading) {
    return <p className="w-full text-body-md text-text-subtle">Loading…</p>;
  }
  if (query.isError) {
    const e = describeError(query.error, "asset");
    return (
      <div className="w-full">
        <Link to="/assets" className="text-body-sm text-text-link">
          Assets
        </Link>
        <ErrorState
          className="mt-4"
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void query.refetch() : undefined}
        />
      </div>
    );
  }
  if (!a) {
    return (
      <div className="w-full">
        <Link to="/assets" className="text-body-sm text-text-link">
          Assets
        </Link>
        <p className="mt-4 text-body-md text-text-secondary">Asset not found.</p>
      </div>
    );
  }

  const tier = displayTier(a.criticality);
  const tierMeta = tier ? TIER_META[tier] : NEEDS_ASSESSMENT;
  // The single obvious next lifecycle move stays a button; the rest fold into ⋯.
  const primaryTo = a.allowed_transitions.find((t) => t === PRIMARY_NEXT[a.status]) ?? null;
  const otherTransitions = a.allowed_transitions.filter((t) => t !== primaryTo);

  return (
    <div className="w-full">
      <DetailHeader
        icon="box"
        backTo="/assets"
        backLabel="Back to assets"
        title={a.name}
        chips={
          <>
            <Badge variant="neutral">{ASSET_TYPE_META[a.asset_type].label}</Badge>
            {a.environment ? <Badge variant="neutral">{ENVIRONMENT_LABEL[a.environment]}</Badge> : null}
            {a.internet_facing ? (
              <span className="inline-flex items-center gap-1 text-caption text-status-warning-text">
                <Icon name="globe" className="size-3.5" />
                Internet-facing
              </span>
            ) : null}
          </>
        }
        meta={
          a.hostname || a.fqdn || a.ip_address ? (
            <span className="font-mono">{[a.hostname, a.fqdn, a.ip_address].filter(Boolean).join(" · ")}</span>
          ) : null
        }
        actions={
          <>
            {primaryTo ? (
              <Button onClick={() => setTransition(primaryTo)}>{lifecycleLabel(a.status, primaryTo)}</Button>
            ) : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary">
                  Actions
                  <Icon name="chev" className="size-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => setEditing(true)}>Edit</DropdownMenuItem>
                {otherTransitions.length > 0 ? <DropdownMenuSeparator /> : null}
                {otherTransitions.map((to) => (
                  <DropdownMenuItem
                    key={to}
                    variant={to === "decommissioned" || to === "retired" ? "danger" : "default"}
                    onSelect={() => setTransition(to)}
                  >
                    {lifecycleLabel(a.status, to)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        }
      />

      {/* Facts */}
      <div className="mt-4 flex flex-wrap items-center gap-x-8 gap-y-2">
        <Field label="Criticality">
          {tier ? (
            <span className="inline-flex items-center gap-2">
              <StatusPill status={tierMeta.family} label={tierMeta.label} />
              {a.criticality.score != null ? (
                <span className="tabular text-caption text-text-subtle">{a.criticality.score.toFixed(1)}</span>
              ) : null}
              {a.criticality.tier_override ? <Badge variant="neutral">Override</Badge> : null}
            </span>
          ) : (
            <Plain>Not rated</Plain>
          )}
        </Field>
        <Field label="Lifecycle">
          <StatusPill status={STATUS_META[a.status].family} label={STATUS_META[a.status].label} />
        </Field>
        <Field label="Owner">
          {a.ownership.primary_owner ? (
            <span className="flex items-center gap-2">
              <Avatar name={a.ownership.primary_owner.name} size="sm" />
              <span className="text-body-md text-text-primary">{a.ownership.primary_owner.name}</span>
            </span>
          ) : (
            <span className="text-body-md text-status-warning-text">Unassigned</span>
          )}
        </Field>
        <Field label="Classification">
          {a.data_classification ? (
            <StatusPill kind="inline" status={CLASSIFICATION_META[a.data_classification].family} label={CLASSIFICATION_META[a.data_classification].label} />
          ) : (
            <Plain>Not set</Plain>
          )}
        </Field>
        <Field label="Value">
          <Plain>{fmtMoney(a.valuation)}</Plain>
        </Field>
        <Field label="Last seen">
          <span className={cn("text-body-md", a.hygiene.is_stale ? "text-status-danger-text" : "text-text-primary")}>
            {relativeTime(a.last_seen_at)}
          </span>
        </Field>
      </div>

      {/* Tabs */}
      <TabStrip
        label="Asset sections"
        items={TABS.map((t) => ({
          id: t.id,
          label: t.label,
          count:
            (t.id === "linked"
              ? linksQuery.data?.records.length
              : t.id === "relationships"
                ? a.relationship_count
                : undefined) || undefined,
        }))}
        value={tab}
        onSelect={(id) => setTab(id as TabId)}
        className="mb-0 mt-6"
        inline
      />

      <div className="mt-5">
        {tab === "overview" ? <OverviewTab a={a} onChange={invalidate} /> : null}
        {tab === "criticality" ? <CriticalityTab a={a} /> : null}
        {tab === "ownership" ? <OwnershipTab a={a} /> : null}
        {tab === "lifecycle" ? <LifecycleTab a={a} /> : null}
        {tab === "vulnerabilities" ? <VulnerabilitiesTab assetId={a.id} assetName={a.name} onOpen={(id) => navigate(`/vulnerabilities/${id}`)} /> : null}
        {tab === "relationships" ? <RelationshipsTab a={a} onChange={invalidate} onOpen={(id) => navigate(`/assets/${id}`)} /> : null}
        {tab === "linked" ? <LinkedTab a={a} /> : null}
        {tab === "activity" ? <ActivityTab a={a} /> : null}
      </div>

      {transition === "decommissioned" ? (
        <DecommissionDialog
          a={a}
          onOpenChange={(o) => !o && setTransition(null)}
          onDone={() => {
            setTransition(null);
            invalidate();
          }}
        />
      ) : transition ? (
        <TransitionDialog
          a={a}
          to={transition}
          onOpenChange={(o) => !o && setTransition(null)}
          onDone={() => {
            setTransition(null);
            invalidate();
          }}
        />
      ) : null}

      <AssetFormDrawer
        open={editing}
        onOpenChange={setEditing}
        assetId={a.id}
        onSaved={() => invalidate()}
      />
    </div>
  );
}

// -- tabs --------------------------------------------------------------------

function OverviewTab({ a, onChange }: { a: AssetDetail; onChange: () => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <div className="space-y-4">
        <Panel title="Description">
          {a.description ? (
            <p className="whitespace-pre-line text-body-md leading-relaxed text-text-secondary">{a.description}</p>
          ) : (
            <p className="text-body-sm text-text-subtle">No description.</p>
          )}
        </Panel>
        <Panel title="Identity">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-body-sm">
            <Meta label="Hostname" value={a.hostname ?? "Not set"} />
            <Meta label="IP address" value={a.ip_address ?? "Not set"} />
            <Meta label="FQDN" value={a.fqdn ?? "Not set"} />
            <Meta label="OS" value={a.os_normalized ?? "Not set"} />
            <Meta label="Location" value={a.location ?? "Not set"} />
            <Meta label="Network segment" value={a.network_segment ?? "Not set"} />
            <Meta label="Vendor" value={a.vendor_ref ?? "Not set"} />
            <Meta label="Environment" value={a.environment ? ENVIRONMENT_LABEL[a.environment] : "Not set"} />
          </dl>
        </Panel>
        <Panel title="Classification & exposure">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-body-sm">
            <Meta label="Data classification" value={a.data_classification ? CLASSIFICATION_META[a.data_classification].label : "Not set"} />
            <Meta label="Regulated data" value={a.regulated_data_type ? humanize(a.regulated_data_type) : "Not set"} />
            <Meta label="Compliance scope" value={a.compliance_scope.length ? a.compliance_scope.join(", ") : "None"} />
            <Meta label="Business function" value={a.business_function ?? "Not set"} />
            <Meta label="Internet-facing" value={a.internet_facing ? "Yes" : "No"} />
            <Meta label="Customer-facing" value={a.customer_facing ? "Yes" : "No"} />
          </dl>
        </Panel>
        {a.business_impact_notes || a.valuation != null || a.operational_dependency_rating ? (
          <Panel title="Business context">
            <dl className="space-y-2.5 text-body-sm">
              <Meta label="Valuation" value={fmtMoney(a.valuation)} />
              <Meta label="Operational dependency" value={a.operational_dependency_rating ? humanize(a.operational_dependency_rating) : "Not rated"} />
              {a.business_impact_notes ? (
                <div>
                  <dt className="text-text-subtle">Business impact</dt>
                  <dd className="mt-1 text-text-secondary">{a.business_impact_notes}</dd>
                </div>
              ) : null}
            </dl>
          </Panel>
        ) : null}
      </div>

      <div className="space-y-4">
        <HygienePanel a={a} onChange={onChange} />
        <CustomFieldsPanel a={a} />
        <Panel title="Record">
          <dl className="space-y-2.5 text-body-sm">
            <Meta label="Source" value={cap(a.source)} />
            <Meta label="Created" value={fmtDate(a.created_at)} />
            <Meta label="First seen" value={fmtDate(a.first_seen_at)} />
            <Meta label="Last reviewed" value={fmtDate(a.last_reviewed_at)} />
            {a.vuln_count > 0 ? <Meta label="Open vulnerabilities" value={String(a.vuln_count)} /> : null}
          </dl>
        </Panel>
      </div>
    </div>
  );
}

/** The tenant's own fields, if this workspace defined any. Values are edited in
 *  the asset form beside everything else, so this is a read. */
function CustomFieldsPanel({ a }: { a: AssetDetail }) {
  const fields = useCustomFields("assets").data ?? [];
  const shown = fields.filter((f) => a.custom_fields[f.key] !== undefined || f.required);
  if (shown.length === 0) return null;
  return (
    <Panel title="Also recorded">
      <dl className="space-y-2.5 text-body-sm">
        {shown.map((f) => (
          <Meta key={f.id} label={f.label} value={customFieldText(f, a.custom_fields[f.key])} />
        ))}
      </dl>
    </Panel>
  );
}

function HygienePanel({ a, onChange }: { a: AssetDetail; onChange: () => void }) {
  const clean = a.hygiene.missing.length === 0 && !a.hygiene.is_stale;
  const { toast } = useToast();
  const review = useMutation({
    mutationFn: () => recordReview(a.id),
    onSuccess: () => {
      onChange();
      toast({ title: "Inventory reviewed", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "asset"), tone: "danger" }),
  });
  const since = a.last_reviewed_at
    ? Math.floor((Date.now() - new Date(a.last_reviewed_at).getTime()) / 86_400_000)
    : null;
  return (
    <Panel
      title="Inventory hygiene"
      action={
        <Button variant="ghost" size="sm" loading={review.isPending} onClick={() => review.mutate()}>
          Mark reviewed
        </Button>
      }
    >
      <div className="flex items-baseline gap-2">
        <span
          className={cn(
            "font-display text-heading-md tabular",
            a.hygiene.score >= 80 ? "text-status-success-text" : a.hygiene.score >= 40 ? "text-status-warning-text" : "text-status-danger-text",
          )}
        >
          {a.hygiene.score}%
        </span>
        <span className="text-body-sm text-text-subtle">
          {5 - a.hygiene.missing.length} of 5 assessed
        </span>
      </div>

      {/* Every check, answered. A bare "100%" tells a reader the number but not
          what was counted, which is the one thing they need to trust it. */}
      <ul className="mt-3 space-y-1.5">
        {HYGIENE_FLAGS.map((flag) => {
          const met = !a.hygiene.missing.includes(flag);
          return (
            <li key={flag} className="flex items-center gap-2 text-body-sm">
              <Icon
                name={met ? "check" : "alert"}
                className={cn("size-3.5 shrink-0", met ? "text-status-success-text" : "text-status-warning-text")}
              />
              <span className={met ? "text-text-secondary" : "text-text-primary"}>
                {HYGIENE_CHECK_LABEL[flag]}
              </span>
              <span className="ml-auto text-caption text-text-subtle">
                {met ? HYGIENE_MET_VALUE[flag](a) : "Not set"}
              </span>
            </li>
          );
        })}
      </ul>

      <p
        className={cn(
          "mt-3 border-t border-border pt-2.5 text-body-sm",
          a.hygiene.is_stale ? "text-status-danger-text" : "text-text-subtle",
        )}
      >
        {a.hygiene.is_stale
          ? `Not reviewed in over ${a.hygiene.review_days} days.`
          : since === null
            ? `Never reviewed. Reviewed every ${a.hygiene.review_days} days.`
            : `Reviewed ${since === 0 ? "today" : since === 1 ? "yesterday" : `${since} days ago`}, due again in ${Math.max(0, a.hygiene.review_days - since)} days.`}
      </p>
      {clean ? null : (
        <p className="mt-1 text-caption text-text-subtle">
          Edit the asset to fill in what is missing.
        </p>
      )}
    </Panel>
  );
}

/** What each check asks for, and what it found. The register's "needs
 *  attention" filter keys off exactly these five plus the review window. */
const HYGIENE_CHECK_LABEL: Record<HygieneFlag, string> = {
  no_owner: "Primary owner",
  no_type: "Type",
  no_criticality: "Criticality",
  no_classification: "Data classification",
  no_cia: "CIA rating",
};

const HYGIENE_MET_VALUE: Record<HygieneFlag, (a: AssetDetail) => string> = {
  no_owner: (a) => a.ownership.primary_owner?.name ?? "Set",
  no_type: (a) => ASSET_TYPE_META[a.asset_type]?.label ?? a.asset_type,
  no_criticality: (a) => {
    const tier = displayTier(a.criticality);
    return tier ? TIER_META[tier].label : "Set";
  },
  no_classification: (a) =>
    a.data_classification ? CLASSIFICATION_META[a.data_classification].label : "Set",
  no_cia: (a) =>
    `C${a.criticality.confidentiality} I${a.criticality.integrity} A${a.criticality.availability}`,
};


function CriticalityTab({ a }: { a: AssetDetail }) {
  const c = a.criticality;
  const rated = c.confidentiality != null || c.integrity != null || c.availability != null;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="CIA rating">
        {rated ? (
          <div className="space-y-3">
            <CiaRow label="Confidentiality" value={c.confidentiality} />
            <CiaRow label="Integrity" value={c.integrity} />
            <CiaRow label="Availability" value={c.availability} />
          </div>
        ) : (
          <p className="text-body-sm text-text-subtle">
            Not rated. Rate confidentiality, integrity and availability to derive a criticality tier.
          </p>
        )}
      </Panel>
      <Panel title="Derived criticality">
        <dl className="space-y-2.5 text-body-sm">
          <Meta label="Computed score" value={c.score != null ? `${c.score.toFixed(1)} / 10` : "Not scored"} />
          <Meta label="Computed tier" value={c.tier ? TIER_META[c.tier].label : "Not rated"} />
          <Meta label="Published tier" value={displayTier(c) ? TIER_META[displayTier(c)!].label : "Not rated"} />
        </dl>
        {c.tier_override ? (
          <div className="mt-3 rounded-sm border border-border bg-surface-sunken px-3 py-2">
            <p className="text-caption text-text-subtle">
              Overridden to <span className="font-semibold text-text-primary">{TIER_META[c.tier_override].label}</span>
              {c.tier ? <> from computed {TIER_META[c.tier].label}</> : null}
            </p>
            {c.tier_override_reason ? <p className="mt-1 text-body-sm text-text-secondary">{c.tier_override_reason}</p> : null}
          </div>
        ) : (
          <p className="mt-3 text-caption text-text-subtle">
            Score is the highest CIA rating, adjusted for internet exposure and data sensitivity.
          </p>
        )}
      </Panel>
    </div>
  );
}

function CiaRow({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-body-sm text-text-secondary">{label}</span>
        <span className="tabular text-body-sm text-text-primary">{value != null ? `${value} / 5` : "Not rated"}</span>
      </div>
      <div className="mt-1 flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            className={cn("h-1.5 flex-1 rounded-full", value != null && n <= value ? "bg-action-accent" : "bg-surface-sunken")}
          />
        ))}
      </div>
    </div>
  );
}

function OwnershipTab({ a }: { a: AssetDetail }) {
  const o = a.ownership;
  const roles: { label: string; member: { name: string } | null }[] = [
    { label: "Primary owner", member: o.primary_owner },
    { label: "Secondary owner", member: o.secondary_owner },
    { label: "Business owner", member: o.business_owner },
    { label: "Custodian", member: o.custodian },
    { label: "Escalation contact", member: o.escalation_contact },
  ];
  return (
    <Panel title="Ownership chain">
      <p className="mb-4 text-body-sm text-text-subtle">
        Everything inherits its owner from here. Vulnerabilities, policy violations and alerts resolve to the primary owner.
      </p>
      <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {roles.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-3">
            <dt className="text-body-sm text-text-subtle">{r.label}</dt>
            <dd>
              {r.member ? (
                <span className="flex items-center gap-2">
                  <Avatar name={r.member.name} size="sm" />
                  <span className="text-body-sm text-text-primary">{r.member.name}</span>
                </span>
              ) : (
                <span className="text-body-sm text-text-subtle">Unassigned</span>
              )}
            </dd>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3">
          <dt className="text-body-sm text-text-subtle">Owning team</dt>
          <dd className="text-body-sm text-text-primary">{o.owning_team ?? "Not set"}</dd>
        </div>
      </dl>
    </Panel>
  );
}

function LifecycleTab({ a }: { a: AssetDetail }) {
  return (
    <div className="space-y-4">
      <Panel title="Lifecycle state">
        <div className="flex items-center gap-2">
          <StatusPill status={STATUS_META[a.status].family} label={STATUS_META[a.status].label} />
          {a.replaced_by_asset_id ? (
            <Link to={`/assets/${a.replaced_by_asset_id}`} className="text-body-sm text-text-link hover:underline">
              Replaced by →
            </Link>
          ) : null}
        </div>
        <p className="mt-3 text-body-sm text-text-subtle">
          Allowed next: {a.allowed_transitions.length ? a.allowed_transitions.map((t) => STATUS_META[t].label).join(", ") : "none (terminal)"}
        </p>
      </Panel>
      {a.decommission ? (
        <Panel title="Decommission record">
          <dl className="space-y-2.5 text-body-sm">
            <Meta label="Disposal method" value={humanize(a.decommission.disposal_method)} />
            <Meta label="Media sanitised" value={a.decommission.media_sanitised ? "Yes" : "No"} />
            <Meta label="Disposal evidence" value={a.decommission.evidence_ref ?? "None"} />
            <Meta label="Decommissioned by" value={a.decommission.decommissioned_by} />
            <Meta label="Date" value={fmtDate(a.decommission.decommissioned_at)} />
            <div>
              <dt className="text-text-subtle">Reason</dt>
              <dd className="mt-1 text-text-secondary">{a.decommission.reason}</dd>
            </div>
          </dl>
        </Panel>
      ) : null}
    </div>
  );
}

function RelationshipsTab({ a, onChange, onOpen }: { a: AssetDetail; onChange: () => void; onOpen: (id: string) => void }) {
  const [adding, setAdding] = useState(false);
  const { toast } = useToast();
  const remove = useMutation({
    mutationFn: (relId: string) => deleteRelationship(a.id, relId),
    onSuccess: onChange,
    onError: (error) => toast({ title: errorToast(error, "relationship"), tone: "danger" }),
  });
  return (
    <Panel
      title="Dependencies"
      action={
        <Button variant="ghost" size="sm" onClick={() => setAdding(true)}>
          <Icon name="plus" className="size-3.5" />
          Add
        </Button>
      }
    >
      {a.relationships.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No relationships declared. Map what this asset depends on and what depends on it to trace blast radius and inherit criticality.
        </p>
      ) : (
        <ul className="space-y-2">
          {a.relationships.map((r) => (
            <li key={r.id} className="flex items-center gap-2.5 rounded-sm border border-border px-3 py-2">
              <Badge variant="neutral">{relationshipLabel(r)}</Badge>
              <button type="button" onClick={() => onOpen(r.other_asset_id)} className="min-w-0 flex-1 truncate text-left text-body-sm text-text-primary hover:underline">
                {r.other_asset_name}
              </button>
              {r.provenance === "discovered" ? <span className="text-caption text-text-subtle">discovered</span> : null}
              <button type="button" aria-label="Remove relationship" onClick={() => remove.mutate(r.id)} className="text-text-subtle transition-colors hover:text-status-danger-text">
                <Icon name="x" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {adding ? <RelationshipDialog a={a} onOpenChange={setAdding} onDone={() => { setAdding(false); onChange(); }} /> : null}
    </Panel>
  );
}

/**
 * How an edge reads from the asset you are looking at.
 *
 * One stored row, two sentences: the inverse of "runs on" is "hosts", not
 * "is runs on by". Mechanically inverting the verb is how a dependency map ends
 * up unreadable in exactly the direction people scan it.
 */
const INVERSE_LABEL: Record<RelationshipType, string> = {
  depends_on: "is depended on by",
  runs_on: "hosts",
  contains: "is part of",
  connects_to: "is connected to by",
  processes_data_for: "has data processed by",
};

function relationshipLabel(r: AssetRelationship): string {
  return r.direction === "outbound"
    ? humanize(r.type)
    : (INVERSE_LABEL[r.type] ?? `is ${humanize(r.type)} by`);
}

function RelationshipDialog({ a, onOpenChange, onDone }: { a: AssetDetail; onOpenChange: (o: boolean) => void; onDone: () => void }) {
  const [direction, setDirection] = useState<"outbound" | "inbound">("outbound");
  const [type, setType] = useState<RelationshipType>("depends_on");
  const [other, setOther] = useState<string | null>(null);
  const { toast } = useToast();
  const candidatesQuery = useQuery({ queryKey: ["assets", "all-for-rel"], queryFn: () => listAssets({}, 1, 100) });
  const candidates = (candidatesQuery.data?.items ?? []).filter((x) => x.id !== a.id);
  const run = useMutation({
    mutationFn: () => addRelationship(a.id, { type, direction, other_asset_id: other! }),
    onSuccess: () => {
      onDone();
      toast({ title: "Relationship added", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "relationship"), tone: "danger" }),
  });
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Add dependency</DialogTitle>
          <p className="text-body-md text-text-secondary">Declare how this asset relates to another. The inverse is recorded on the other asset automatically.</p>
        </DialogHeader>
        <div className="space-y-4">
          <SelectField label="Direction">
            <Select value={direction} onValueChange={(v) => setDirection(v as "outbound" | "inbound")}>
              <SelectTrigger aria-label="Direction" />
              <SelectContent>
                <SelectItem value="outbound">This asset → other</SelectItem>
                <SelectItem value="inbound">Other → this asset</SelectItem>
              </SelectContent>
            </Select>
          </SelectField>
          <SelectField label="Relationship">
            <Select value={type} onValueChange={(v) => setType(v as RelationshipType)}>
              <SelectTrigger aria-label="Relationship" />
              <SelectContent>
                {RELATIONSHIP_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {humanize(t)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <SelectField label="Other asset">
            <Select value={other ?? ""} onValueChange={setOther}>
              <SelectTrigger aria-label="Other asset" />
              <SelectContent>
                {candidates.map((x) => (
                  <SelectItem key={x.id} value={x.id}>
                    {x.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          {candidatesQuery.isError ? (
            <p className="text-body-sm text-status-danger-text">{describeError(candidatesQuery.error, "asset list").message}</p>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={run.isPending} disabled={!other} onClick={() => run.mutate()}>
            Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function VulnerabilitiesTab({
  assetId,
  assetName,
  onOpen,
}: {
  assetId: string;
  assetName: string;
  onOpen: (id: string) => void;
}) {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vulnerabilities:manage");
  const [adding, setAdding] = useState(false);
  const [linking, setLinking] = useState(false);
  const query = useQuery({
    queryKey: ["asset-vulns", assetId],
    queryFn: () => listVulnerabilities({ asset_id: assetId, state: "all" }),
  });
  const rows = query.data ?? [];
  const open = rows.filter((r) => !["fixed", "accepted", "false_positive"].includes(r.state));

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-display text-title-md text-text-primary">
          Vulnerabilities
          <span className="ml-2 tabular text-body-sm text-text-subtle">{open.length} open</span>
        </h2>
        <span className="ml-auto flex flex-wrap items-center gap-2">
          <Button size="sm" variant="ghost" asChild>
            <Link to={`/vulnerabilities?asset_id=${assetId}`}>
              View in register
              <Icon name="chevr" className="size-3.5" />
            </Link>
          </Button>
          {canManage ? (
            <>
              <Button size="sm" variant="secondary" onClick={() => setLinking(true)}>
                <Icon name="link" className="size-3.5" />
                Link finding
              </Button>
              <Button size="sm" onClick={() => setAdding(true)}>
                <Icon name="plus" className="size-3.5" />
                Add finding
              </Button>
            </>
          ) : null}
        </span>
      </div>
      {query.isLoading ? (
        <p className="text-body-sm text-text-subtle">Loading</p>
      ) : query.isError ? (
        <p className="text-body-sm text-status-danger-text">{describeError(query.error, "vulnerability list").message}</p>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-md bg-surface-sunken px-4 py-8 text-center">
          <span className="grid size-10 place-items-center rounded-xl bg-surface-primary text-text-subtle shadow-1">
            <Icon name="bug" className="size-5" />
          </span>
          <p className="text-body-sm text-text-secondary">No vulnerabilities on this asset.</p>
          <p className="text-caption text-text-subtle">Imported scans land here, prioritised by risk.</p>
        </div>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((v) => (
            <li key={v.id}>
              <button
                type="button"
                onClick={() => onOpen(v.id)}
                className="flex w-full items-center gap-2.5 rounded-sm border border-border px-3 py-2 text-left transition-colors hover:border-border-strong hover:bg-surface-hover"
              >
                <SeverityBadge severity={v.severity} />
                <span className="min-w-0 flex-1">
                  {v.cve_id ? (
                    <span className="mr-2 font-mono text-caption text-text-subtle">{v.cve_id}</span>
                  ) : null}
                  <span className="text-body-sm text-text-primary">{v.title}</span>
                </span>
                <span className="tabular text-caption font-semibold text-text-secondary">
                  {v.risk_score ?? "No score"} · {v.priority_band}
                </span>
                <Badge variant="neutral">{v.state.replace(/_/g, " ")}</Badge>
              </button>
            </li>
          ))}
        </ul>
      )}
      <AddFindingDrawer open={adding} onOpenChange={setAdding} assetId={assetId} />
      {linking ? (
        <LinkFindingDialog assetId={assetId} assetName={assetName} onOpenChange={setLinking} onAsset={rows} />
      ) : null}
    </div>
  );
}

/**
 * Record a finding that already exists elsewhere on this asset too. It becomes
 * its own instance here, with its own status, SLA and score, so fixing it on
 * one asset never closes it on another.
 */
function LinkFindingDialog({
  assetId,
  assetName,
  onOpenChange,
  onAsset,
}: {
  assetId: string;
  assetName: string;
  onOpenChange: (open: boolean) => void;
  onAsset: { cve_id: string | null; title: string }[];
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const query = useDeferredValue(search);
  const results = useQuery({
    queryKey: ["asset-link-finding", query],
    queryFn: () => listVulnerabilities({ search: query, state: "all" }),
  });
  const keyOf = (v: { cve_id: string | null; title: string }) => (v.cve_id || v.title).toLowerCase();
  const here = new Set(onAsset.map(keyOf));
  const findings = [...new Map((results.data ?? []).map((v) => [keyOf(v), v])).values()].slice(0, 30);

  const link = useMutation({
    mutationFn: (instanceId: string) => linkVulnerabilityAsset(instanceId, assetId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["asset-vulns", assetId] });
      void queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      void queryClient.invalidateQueries({ queryKey: ["vuln-kpis"] });
      toast({ title: `Finding added to ${assetName}`, tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "finding"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Link a finding</DialogTitle>
          <DialogDescription>
            Record an existing finding on {assetName} too. It gets its own status and SLA here.
          </DialogDescription>
        </DialogHeader>
        <SearchInput value={search} onChange={setSearch} placeholder="Search by title or CVE" aria-label="Search findings" />
        <DialogBody className="mt-3">
          {results.isLoading ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">Searching</p>
          ) : results.isError ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">
              {describeError(results.error, "findings").message}
            </p>
          ) : findings.length === 0 ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">No findings match.</p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {findings.map((v) => {
                const already = here.has(keyOf(v));
                return (
                  <li key={v.id} className="flex items-center gap-3 px-3 py-2.5">
                    <SeverityBadge severity={v.severity} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm font-medium text-text-primary">
                        {v.cve_id ? (
                          <span className="mr-1.5 font-mono text-caption font-semibold text-text-subtle">{v.cve_id}</span>
                        ) : null}
                        {v.title}
                      </span>
                      <span className="block truncate text-caption text-text-subtle">Seen on {v.asset_name}</span>
                    </span>
                    <Button
                      size="sm"
                      variant={already ? "ghost" : "secondary"}
                      disabled={already || link.isPending}
                      loading={link.isPending && link.variables === v.id}
                      onClick={() => link.mutate(v.id)}
                    >
                      {already ? (
                        <>
                          <Icon name="check" className="size-3.5" />
                          On this asset
                        </>
                      ) : (
                        "Add here"
                      )}
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LinkedTab({ a }: { a: AssetDetail }) {
  return <LinkedRecordsPanel anchorType="asset" anchorId={a.id} />;
}

function ActivityTab({ a }: { a: AssetDetail }) {
  return (
    <Panel title="Activity">
      <ol className="relative space-y-4 border-l border-border pl-5">
        {a.transitions.map((t) => (
          <li key={t.id} className="relative">
            <span className="absolute -left-[1.6rem] top-1.5 size-2 rounded-full bg-action-accent" />
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-body-sm font-semibold text-text-primary">{t.actor}</span>
              <span className="text-body-sm text-text-secondary">
                {t.field_changed === "created" ? (
                  "added this asset"
                ) : (
                  <>
                    changed <span className="text-text-primary">{humanize(t.field_changed)}</span>
                    {t.old_value ? (
                      <>
                        {" "}
                        <span className="line-through decoration-text-faint">{t.old_value}</span>
                        <Icon name="arrowr" className="mx-1 inline size-3 text-text-faint" aria-hidden />
                      </>
                    ) : null}
                    <span className="font-semibold text-text-primary">{t.new_value}</span>
                  </>
                )}
              </span>
              <span className="ml-auto tabular text-caption text-text-subtle">{new Date(t.occurred_at).toLocaleString()}</span>
            </div>
            {t.note ? <p className="mt-1 rounded-sm bg-surface-sunken px-2.5 py-1.5 text-body-sm text-text-secondary">{t.note}</p> : null}
          </li>
        ))}
      </ol>
    </Panel>
  );
}

// -- dialog ------------------------------------------------------------------

function TransitionDialog({
  a,
  to,
  onOpenChange,
  onDone,
}: {
  a: AssetDetail;
  to: AssetStatus;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const [note, setNote] = useState("");
  const { toast } = useToast();
  const noteRequired = to === "decommissioned" || to === "retired";
  const run = useMutation({
    mutationFn: () => transitionAsset(a.id, to, note.trim() || undefined),
    onSuccess: () => {
      onDone();
      toast({ title: "Asset updated", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "asset"), tone: "danger" }),
  });
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>
            {lifecycleLabel(a.status, to)} · {a.name}
          </DialogTitle>
          <p className="text-body-md text-text-secondary">
            {to === "decommissioned"
              ? "Record why this asset is being retired. Full disposal details are captured next."
              : to === "retired"
                ? "Retiring is terminal. The record stays with its reason."
                : "Add an optional note describing the change."}
          </p>
        </DialogHeader>
        <TextField
          label={noteRequired ? "Reason" : "Note"}
          optional={!noteRequired}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={run.isPending}
            disabled={noteRequired && note.trim() === ""}
            variant={noteRequired ? "secondary" : "primary"}
            onClick={() => run.mutate()}
          >
            {lifecycleLabel(a.status, to)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const DISPOSAL_METHODS = ["wiped_and_recycled", "physically_destroyed", "returned_to_vendor", "sold", "donated"];

function DecommissionDialog({ a, onOpenChange, onDone }: { a: AssetDetail; onOpenChange: (o: boolean) => void; onDone: () => void }) {
  const [method, setMethod] = useState(DISPOSAL_METHODS[0]);
  const [sanitised, setSanitised] = useState(true);
  const [replacement, setReplacement] = useState<string | null>(null);
  const [evidence, setEvidence] = useState("");
  const [reason, setReason] = useState("");
  const { toast } = useToast();

  const candidatesQuery = useQuery({ queryKey: ["assets", "all-for-replacement"], queryFn: () => listAssets({}, 1, 100) });
  const candidates = (candidatesQuery.data?.items ?? []).filter((x) => x.id !== a.id);

  const run = useMutation({
    mutationFn: () =>
      decommissionAsset(a.id, {
        disposal_method: method,
        media_sanitised: sanitised,
        replacement_asset_id: replacement,
        evidence_ref: evidence.trim() || null,
        reason: reason.trim(),
      }),
    onSuccess: () => {
      onDone();
      toast({ title: "Asset decommissioned", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "asset"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Decommission · {a.name}</DialogTitle>
          <p className="text-body-md text-text-secondary">
            Auditors test that retirement followed policy. Any open vulnerabilities on this asset are closed automatically.
          </p>
        </DialogHeader>
        <div className="space-y-4">
          <SelectField label="Disposal method">
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger aria-label="Disposal method" />
              <SelectContent>
                {DISPOSAL_METHODS.map((m) => (
                  <SelectItem key={m} value={m}>
                    {humanize(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <label className="flex cursor-pointer items-center gap-2.5">
            <Checkbox checked={sanitised} onCheckedChange={(v) => setSanitised(Boolean(v))} aria-label="Media sanitised" />
            <span className="text-body-sm text-text-primary">Media sanitised</span>
          </label>
          <SelectField label="Replacement asset" optional>
            <Select value={replacement ?? "__none__"} onValueChange={(v) => setReplacement(v === "__none__" ? null : v)}>
              <SelectTrigger aria-label="Replacement asset" />
              <SelectContent>
                <SelectItem value="__none__">None</SelectItem>
                {candidates.map((x) => (
                  <SelectItem key={x.id} value={x.id}>
                    {x.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          {candidatesQuery.isError ? (
            <p className="text-body-sm text-status-danger-text">{describeError(candidatesQuery.error, "asset list").message}</p>
          ) : null}
          <TextField label="Disposal evidence reference" optional value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="e.g. disposal-cert-2026-03" />
          <TextField label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="End of life; workloads migrated." />
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="secondary" className="text-status-danger-text" loading={run.isPending} disabled={reason.trim() === ""} onClick={() => run.mutate()}>
            Decommission
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -- primitives --------------------------------------------------------------

function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-caption text-text-subtle">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-text-subtle">{label}</dt>
      <dd className="text-right text-text-primary">{value}</dd>
    </div>
  );
}

function Plain({ children }: { children: React.ReactNode }) {
  return <span className="text-body-md text-text-primary">{children}</span>;
}
