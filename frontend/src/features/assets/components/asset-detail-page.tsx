import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  Checkbox,
  Dialog,
  DialogContent,
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
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextField,
  useToast,
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
import { RELATIONSHIP_TYPES } from "../types";
import type { AssetDetail, AssetStatus, HygieneFlag, LinkTarget, RelationshipType } from "../types";
import { AssetFormDrawer } from "./asset-form-drawer";
import { listVulnerabilities } from "@/features/vulnerabilities/api";
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

const HYGIENE_LABEL: Record<HygieneFlag, string> = {
  no_owner: "No primary owner",
  no_type: "No type set",
  no_criticality: "No criticality",
  no_classification: "No data classification",
  no_cia: "CIA not rated",
};

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "criticality", label: "Criticality" },
  { id: "ownership", label: "Ownership" },
  { id: "lifecycle", label: "Lifecycle" },
  { id: "vulnerabilities", label: "Vulnerabilities" },
  { id: "relationships", label: "Relationships" },
  { id: "linked", label: "Related" },
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
  const linkedCounts = Object.entries(a.linked_summary).filter(([, n]) => n > 0);
  // The single obvious next lifecycle move stays a button; the rest fold into ⋯.
  const primaryTo = a.allowed_transitions.find((t) => t === PRIMARY_NEXT[a.status]) ?? null;
  const otherTransitions = a.allowed_transitions.filter((t) => t !== primaryTo);

  return (
    <div className="w-full">
      <DetailHeader
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
                <button
                  type="button"
                  aria-label="More actions"
                  className="inline-flex size-9 items-center justify-center rounded-sm border border-border text-text-secondary transition-colors hover:bg-surface-hover"
                >
                  <Icon name="more" className="size-4" />
                </button>
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
      <nav className="mt-6 flex items-center gap-1 overflow-x-auto border-b border-border">
        {TABS.map((t) => {
          const count =
            t.id === "linked"
              ? linkedCounts.reduce((s, [, n]) => s + n, 0)
              : t.id === "relationships"
                ? a.relationship_count
                : undefined;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "relative flex shrink-0 items-center gap-1.5 px-3 py-2 text-label-sm",
                tab === t.id ? "text-text-primary" : "text-text-subtle hover:text-text-secondary",
              )}
            >
              {t.label}
              {count ? <span className="tabular text-caption text-text-subtle">{count}</span> : null}
              {tab === t.id ? <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" /> : null}
            </button>
          );
        })}
      </nav>

      <div className="mt-5">
        {tab === "overview" ? <OverviewTab a={a} onChange={invalidate} /> : null}
        {tab === "criticality" ? <CriticalityTab a={a} /> : null}
        {tab === "ownership" ? <OwnershipTab a={a} /> : null}
        {tab === "lifecycle" ? <LifecycleTab a={a} /> : null}
        {tab === "vulnerabilities" ? <VulnerabilitiesTab assetId={a.id} onOpen={(id) => navigate(`/vulnerabilities/${id}`)} /> : null}
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
  return (
    <Panel
      title="Inventory hygiene"
      action={
        <Button variant="ghost" size="sm" loading={review.isPending} onClick={() => review.mutate()}>
          Mark reviewed
        </Button>
      }
    >
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "font-display text-heading-md tabular",
            a.hygiene.score >= 80 ? "text-status-success-text" : a.hygiene.score >= 40 ? "text-status-warning-text" : "text-status-danger-text",
          )}
        >
          {a.hygiene.score}%
        </span>
        <span className="text-body-sm text-text-subtle">complete</span>
      </div>
      {clean ? (
        <p className="mt-2 text-body-sm text-status-success-text">Fully assessed and current.</p>
      ) : (
        <ul className="mt-3 space-y-1.5">
          {a.hygiene.missing.map((m) => (
            <li key={m} className="flex items-center gap-2 text-body-sm text-text-secondary">
              <Icon name="alert" className="size-3.5 text-status-warning-text" />
              {HYGIENE_LABEL[m]}
            </li>
          ))}
          {a.hygiene.is_stale ? (
            <li className="flex items-center gap-2 text-body-sm text-text-secondary">
              <Icon name="clock" className="size-3.5 text-status-danger-text" />
              Not reviewed in over 90 days
            </li>
          ) : null}
        </ul>
      )}
    </Panel>
  );
}

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
              <Badge variant="neutral">{r.direction === "outbound" ? humanize(r.type) : `is ${humanize(r.type)} by`}</Badge>
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

const LINKED_MODULES: { type: LinkTarget; label: string }[] = [
  { type: "control", label: "Controls" },
  { type: "risk", label: "Risks" },
  { type: "vulnerability", label: "Vulnerabilities" },
  { type: "evidence", label: "Evidence" },
  { type: "document", label: "Documents" },
];

function VulnerabilitiesTab({ assetId, onOpen }: { assetId: string; onOpen: (id: string) => void }) {
  const query = useQuery({
    queryKey: ["asset-vulns", assetId],
    queryFn: () => listVulnerabilities({ asset_id: assetId, state: "all" }),
  });
  const rows = query.data ?? [];
  const open = rows.filter((r) => !["fixed", "accepted", "false_positive"].includes(r.state));

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          Vulnerabilities
          <span className="ml-2 tabular text-body-sm text-text-subtle">{open.length} open</span>
        </h2>
        <Link
          to={`/vulnerabilities?asset_id=${assetId}`}
          className="text-caption font-semibold text-text-link"
        >
          Open in register →
        </Link>
      </div>
      {query.isLoading ? (
        <p className="text-body-sm text-text-subtle">Loading…</p>
      ) : query.isError ? (
        <p className="text-body-sm text-status-danger-text">{describeError(query.error, "vulnerability list").message}</p>
      ) : rows.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No vulnerabilities on this asset. Findings imported for it appear here, prioritised by risk.
        </p>
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
    </div>
  );
}

function LinkedTab({ a }: { a: AssetDetail }) {
  const groups = new Map<LinkTarget, typeof a.links>();
  for (const l of a.links) groups.set(l.to_type, [...(groups.get(l.to_type) ?? []), l]);
  return (
    <Panel title="Linked records">
      {a.links.length > 0 ? (
        <div className="mb-5 space-y-4">
          {[...groups.entries()].map(([type, links]) => (
            <div key={type}>
              <p className="type-overline mb-1.5 text-text-subtle">{cap(type)}</p>
              <ul className="space-y-1.5">
                {links.map((l) => (
                  <li key={l.id} className="flex items-center gap-2.5 rounded-sm border border-border px-3 py-2">
                    <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">{l.to_label}</span>
                    <Badge variant="neutral">{humanize(l.relation)}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
      <p className="mb-3 text-body-sm text-text-subtle">
        As the compliance modules connect, the controls, risks and vulnerabilities this asset ties into
        appear here for end-to-end traceability.
      </p>
      <ul className="space-y-2">
        {LINKED_MODULES.map((m) => {
          const n = a.linked_summary[m.type] ?? 0;
          return (
            <li key={m.type} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span className="text-body-sm text-text-primary">{m.label}</span>
              {n > 0 ? <Badge variant="neutral">{n} linked</Badge> : <span className="text-caption text-text-subtle">Soon</span>}
            </li>
          );
        })}
      </ul>
    </Panel>
  );
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
