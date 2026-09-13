import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
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
  EmptyState,
  ErrorState,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TabStrip,
  TextArea,
  TextField,
  Tooltip,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { addContact, addEngagement, getVendor, offboard } from "../api";
import type { Tiering, VendorDetail } from "../types";
import { CONTACT_TYPES } from "../types";
import {
  CLASSIFICATION_META,
  CONTACT_TYPE_LABEL,
  duplicateReason,
  fmtCountdown,
  fmtDate,
  fmtMoney,
  daysUntil,
  GRADE_META,
  LIFECYCLE_META,
  TIER_META,
  VENDOR_TYPE_LABEL,
} from "../tokens";
import { Field, Panel } from "./panel";
import { LifecycleWorkspace } from "./lifecycle-workspace";
import { TierBadge } from "./tier-badge";
import { TieringDialog } from "./tiering-panel";
import { AssessmentsPanel } from "./assessments-panel";
import { FindingsPanel } from "./findings-panel";
import { DocumentsPanel } from "./documents-panel";
import { SocReviewPanel } from "./soc-review-panel";
import { ContractsPanel } from "./contracts-panel";
import { SubprocessorsPanel } from "./subprocessors-panel";
import { MonitoringPanel } from "./monitoring-panel";
import { VendorFormDrawer } from "./vendor-form-drawer";

type TabId = "overview" | "lifecycle" | "assessments" | "findings" | "paperwork" | "monitoring";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "lifecycle", label: "Lifecycle" },
  { id: "assessments", label: "Assessments" },
  { id: "findings", label: "Findings" },
  { id: "paperwork", label: "Paperwork" },
  { id: "monitoring", label: "Monitoring" },
] as const;

/** Where a blocker's "clear this" action lands. */
const TARGET_TAB: Record<string, TabId> = {
  vendor: "overview",
  tiering: "lifecycle",
  assessments: "assessments",
  findings: "findings",
  paperwork: "paperwork",
  approval: "lifecycle",
  lifecycle: "lifecycle",
};

export function VendorDetailPage() {
  const { vendorId = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { principal } = useAuth();
  const queryClient = useQueryClient();

  const canManage = hasPermission(principal, "vendors:manage");
  const canAssess = hasPermission(principal, "vendors:assess");
  const canApprove = hasPermission(principal, "vendors:approve");

  const key = ["vendor", vendorId];
  const query = useQuery({ queryKey: key, queryFn: () => getVendor(vendorId) });
  const vendor = query.data ?? null;

  // Derived, not seeded. A useState initialiser reads the query string once, so
  // Back walked the URL through four tabs while the page stayed frozen and then
  // ejected the reader off the vendor entirely. An unknown value falls to
  // Overview rather than through the render chain onto Monitoring.
  const rawTab = params.get("tab");
  const tab: TabId = TABS.some((t) => t.id === rawTab) ? (rawTab as TabId) : "overview";
  const [engagementId, setEngagementId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [addingEngagement, setAddingEngagement] = useState(false);
  const [addingContact, setAddingContact] = useState(false);
  const [offboarding, setOffboarding] = useState(false);
  // The tiering popup lives on the page, not inside one tab, so the header,
  // the Overview tab, the Lifecycle tab and a link from the register can all
  // open it. It stays mounted once opened, so closing it keeps the draft.
  const [tieringFor, setTieringFor] = useState<string | null>(null);
  const [tieringOpen, setTieringOpen] = useState(false);
  const openTiering = (id: string) => {
    setTieringFor(id);
    setTieringOpen(true);
  };

  // Default to the vendor's only engagement, or the first, once it arrives.
  useEffect(() => {
    if (!vendor) return;
    setEngagementId((prev) =>
      prev && vendor.engagements.some((e) => e.id === prev)
        ? prev
        : (vendor.engagements[0]?.id ?? null),
    );
  }, [vendor]);

  // `?tier=1` (from the register) opens the popup on the first engagement that
  // still needs a tier, then drops the parameter so a refresh does not reopen it.
  const tierParam = params.get("tier");
  useEffect(() => {
    if (!vendor || !tierParam) return;
    const target =
      vendor.engagements.find((e) => e.id === tierParam) ??
      vendor.engagements.find((e) => !e.tier) ??
      vendor.engagements[0];
    if (target && canAssess) {
      setEngagementId(target.id);
      setTieringFor(target.id);
      setTieringOpen(true);
    }
    setParams(
      (p) => {
        const copy = new URLSearchParams(p);
        copy.delete("tier");
        return copy;
      },
      { replace: true },
    );
    // Runs once per arrival of the parameter; the setters are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendor, tierParam]);

  const goToTab = (next: TabId) => {
    // replace, not push: switching tabs inside one record is not a navigation
    // the reader wants to unwind one Back press at a time.
    setParams(
      (p) => {
        const copy = new URLSearchParams(p);
        copy.set("tab", next);
        return copy;
      },
      { replace: true },
    );
  };

  /** Every write returns the refreshed vendor; seed the cache rather than refetch. */
  const apply = (next: VendorDetail) => {
    queryClient.setQueryData(key, next);
    void queryClient.invalidateQueries({ queryKey: ["vendors"] });
  };

  if (query.isError) {
    const error = describeError(query.error, "vendor");
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        referenceId={error.referenceId}
        onRetry={error.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!vendor) {
    return (
      <EmptyState
        icon="vendor"
        title="This vendor is not here"
        description="It may have been archived, or the link may be wrong."
        action={
          <Button asChild>
            <Link to="/vendors">Back to the register</Link>
          </Button>
        }
      />
    );
  }

  const status = LIFECYCLE_META[vendor.lifecycle_status] ?? {
    label: vendor.lifecycle_status,
    family: "neutral" as const,
  };
  const engagement = vendor.engagements.find((e) => e.id === engagementId) ?? null;
  const untiered = engagement !== null && !engagement.tier;

  return (
    <div>
      <DetailHeader
        backTo="/vendors"
        backLabel="Back to vendors"
        icon="vendor"
        title={vendor.name}
        chips={
          <>
            <TierBadge
              tier={vendor.tier}
              label={vendor.tier ? `${TIER_META[vendor.tier]?.label ?? vendor.tier} tier` : "Not tiered"}
            />
            <StatusPill status={status.family} label={status.label} kind="inline" />
            {vendor.current_grade ? (
              <Tooltip content={`Residual score ${vendor.current_residual_score ?? "not set"}`}>
                <span>
                  <StatusPill
                    status={GRADE_META[vendor.current_grade]?.family ?? "neutral"}
                    label={`Grade ${vendor.current_grade}`}
                    kind="inline"
                  />
                </span>
              </Tooltip>
            ) : null}
            {vendor.stores_pii ? <Badge variant="countWarn">Holds personal data</Badge> : null}
            {vendor.data_classification ? (
              <Badge variant="neutral">
                {CLASSIFICATION_META[vendor.data_classification]?.label ??
                  vendor.data_classification}
              </Badge>
            ) : null}
          </>
        }
        meta={
          <span>
            {[
              VENDOR_TYPE_LABEL[vendor.vendor_type] ?? vendor.vendor_type,
              vendor.industry,
              vendor.business_unit,
            ]
              .filter(Boolean)
              .join(" · ")}
            {vendor.website ? (
              <>
                {" · "}
                <a
                  href={vendor.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-link underline-offset-2 hover:underline"
                >
                  {vendor.website.replace(/^https?:\/\//, "")}
                </a>
              </>
            ) : null}
          </span>
        }
        actions={
          canManage || canAssess ? (
            <>
              {canAssess && untiered && engagement ? (
                <Button onClick={() => openTiering(engagement.id)}>
                  <Icon name="gauge" className="size-4" />
                  Tier engagement
                </Button>
              ) : null}
              {canManage ? (
                <Button variant="secondary" onClick={() => setEditing(true)}>
                  <Icon name="edit" className="size-4" />
                  Edit
                </Button>
              ) : null}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" aria-label={`Actions for ${vendor.name}`}>
                    Actions
                    <Icon name="chev" className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {canAssess && engagement ? (
                    <DropdownMenuItem onSelect={() => openTiering(engagement.id)}>
                      <Icon name="gauge" className="size-4 text-text-subtle" />
                      {untiered ? "Tier engagement" : "Re-tier engagement"}
                    </DropdownMenuItem>
                  ) : null}
                  {canManage ? (
                    <>
                      <DropdownMenuItem onSelect={() => setAddingEngagement(true)}>
                        <Icon name="briefcase" className="size-4 text-text-subtle" />
                        Add engagement
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => setAddingContact(true)}>
                        <Icon name="user" className="size-4 text-text-subtle" />
                        Add contact
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem variant="danger" onSelect={() => setOffboarding(true)}>
                        <Icon name="signout" className="size-4" />
                        Start offboarding
                      </DropdownMenuItem>
                    </>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : null
        }
      />

      <TabStrip
        label="Vendor sections"
        items={TABS.map((t) => ({ ...t }))}
        value={tab}
        onSelect={(id) => goToTab(id as TabId)}
        className="mt-1"
        variant="bar"
        inline
      />

      {vendor.engagements.length > 1 && tab !== "overview" && tab !== "monitoring" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2.5">
          <span className="text-label-sm text-text-secondary">Engagement</span>
          <div className="w-64">
            <Select value={engagementId ?? ""} onValueChange={setEngagementId}>
              <SelectTrigger aria-label="Engagement" />
              <SelectContent>
                {vendor.engagements.map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      ) : null}

      {tab === "lifecycle" ? (
        // The lifecycle is a workspace with its own sub-navigation, so it takes
        // the full width rather than sharing it with the record's side rail.
        <div className="mt-4">
          <LifecycleWorkspace
            vendor={vendor}
            engagementId={engagementId}
            canManage={canManage}
            canAssess={canAssess}
            canApprove={canApprove}
            onApply={apply}
            onTier={() => {
              if (engagementId) openTiering(engagementId);
            }}
            onGo={(target) => {
              // The roster is a module-root page, not a tab on this record.
              if (target === "roster") {
                navigate("/vendors/roster");
                return;
              }
              if (target === "engagement") {
                setAddingEngagement(true);
                return;
              }
              if (target === "vendor") setEditing(true);
              goToTab(TARGET_TAB[target] ?? "lifecycle");
            }}
          />
        </div>
      ) : (
        <div className="mt-4 grid items-start gap-4 lg:grid-cols-[1fr_20rem]">
          {/* min-w-0: a `1fr` track is minmax(auto, 1fr), so without it the column
              cannot shrink below its content's min-content width and the rail gets
              pushed off screen. */}
          <div className="min-w-0 space-y-4">
            {tab === "overview" ? (
              <OverviewTab
                vendor={vendor}
                canAssess={canAssess}
                onTier={(id) => {
                  setEngagementId(id);
                  openTiering(id);
                }}
              />
            ) : tab === "assessments" ? (
              <AssessmentsPanel
                vendor={vendor}
                engagementId={engagementId}
                canAssess={canAssess}
                onApply={apply}
              />
            ) : tab === "findings" ? (
              <FindingsPanel
                vendorId={vendor.id}
                canManage={canManage}
                canApprove={canApprove}
              />
            ) : tab === "paperwork" ? (
              <>
                <DocumentsPanel vendor={vendor} canManage={canManage} onApply={apply} />
                <SocReviewPanel vendor={vendor} canAssess={canAssess} onApply={apply} />
                <ContractsPanel vendor={vendor} canManage={canManage} onApply={apply} />
                <SubprocessorsPanel vendor={vendor} canManage={canManage} onApply={apply} />
              </>
            ) : tab === "monitoring" ? (
              <MonitoringPanel vendor={vendor} />
            ) : null}
          </div>

          <div className="space-y-4">
            <OwnershipPanel vendor={vendor} />
            <KeyDatesPanel vendor={vendor} />
            <ContactsPanel
              vendor={vendor}
              canManage={canManage}
              onAdd={() => setAddingContact(true)}
            />
            {vendor.duplicates.length > 0 ? <DuplicatesPanel vendor={vendor} /> : null}
            {engagement ? <EngagementPanel vendor={vendor} engagementId={engagement.id} /> : null}
          </div>
        </div>
      )}

      {tieringFor ? (
        <TieringDialog
          open={tieringOpen}
          onOpenChange={setTieringOpen}
          vendor={vendor}
          engagementId={tieringFor}
          latest={latestTiering(vendor, tieringFor)}
          onApply={apply}
        />
      ) : null}
      <VendorFormDrawer open={editing} onOpenChange={setEditing} vendor={vendor} />
      <AddEngagementDialog
        open={addingEngagement}
        onOpenChange={setAddingEngagement}
        vendorId={vendor.id}
        onAdded={apply}
      />
      <AddContactDialog
        open={addingContact}
        onOpenChange={setAddingContact}
        vendorId={vendor.id}
        onAdded={apply}
      />
      <OffboardDialog
        open={offboarding}
        onOpenChange={setOffboarding}
        vendor={vendor}
        onOffboarded={apply}
      />
    </div>
  );
}

/** The engagement's current tiering: the one from its latest cycle. */
function latestTiering(vendor: VendorDetail, engagementId: string): Tiering | null {
  const rows = vendor.tierings.filter((t) => t.engagement_id === engagementId);
  return rows.length > 0 ? rows.reduce((a, b) => (b.cycle >= a.cycle ? b : a)) : null;
}

function OverviewTab({
  vendor,
  canAssess,
  onTier,
}: {
  vendor: VendorDetail;
  canAssess: boolean;
  onTier: (engagementId: string) => void;
}) {
  return (
    <>
      <Panel title="What they do for us">
        {vendor.services_provided ? (
          <p className="whitespace-pre-line text-body-md text-text-secondary">
            {vendor.services_provided}
          </p>
        ) : (
          <p className="text-body-sm text-text-subtle">Not described yet.</p>
        )}

        <dl className="mt-4 grid gap-3 border-t border-border pt-3 sm:grid-cols-2">
          <Field
            label="Data we share"
            value={
              vendor.data_types_in_scope.length > 0 ? (
                <span className="flex flex-wrap gap-1.5">
                  {vendor.data_types_in_scope.map((d) => (
                    <Badge key={d} variant="neutral">
                      {d}
                    </Badge>
                  ))}
                </span>
              ) : vendor.stores_pii ? (
                "Personal data, types not itemised"
              ) : (
                "None recorded"
              )
            }
          />
          <Field label="Where it lives" value={vendor.data_location || "Not recorded"} />
          <Field label="Annual value" value={fmtMoney(vendor.annual_contract_value)} />
          <Field
            label="Tags"
            value={
              vendor.tags.length > 0 ? (
                <span className="flex flex-wrap gap-1.5">
                  {vendor.tags.map((t) => (
                    <Badge key={t} variant="neutral">
                      {t}
                    </Badge>
                  ))}
                </span>
              ) : (
                "None"
              )
            }
          />
        </dl>
      </Panel>

      <Panel title="Engagements" count={vendor.engagements.length || undefined}>
        {vendor.engagements.length === 0 ? (
          <p className="text-body-sm text-text-subtle">No engagements yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {vendor.engagements.map((e) => {
              const status = LIFECYCLE_META[e.status] ?? {
                label: e.status,
                family: "neutral" as const,
              };
              return (
                <li key={e.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="text-body-md font-semibold text-text-primary">{e.name}</p>
                    {e.service_description ? (
                      <p className="mt-0.5 text-body-sm text-text-secondary">
                        {e.service_description}
                      </p>
                    ) : null}
                    <p className="mt-0.5 text-caption text-text-subtle">
                      {[e.business_unit, e.internal_owner_name].filter(Boolean).join(" · ") ||
                        "No owner named"}
                      {e.start_date ? ` · from ${fmtDate(e.start_date)}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <TierBadge tier={e.tier} variant="dot" />
                    <StatusPill status={status.family} label={status.label} kind="inline" />
                    {canAssess ? (
                      e.tier ? (
                        <Button variant="secondary" size="sm" onClick={() => onTier(e.id)}>
                          Re-tier
                        </Button>
                      ) : (
                        <Button size="sm" onClick={() => onTier(e.id)}>
                          <Icon name="gauge" className="size-4" />
                          Tier engagement
                        </Button>
                      )
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </>
  );
}

function OwnershipPanel({ vendor }: { vendor: VendorDetail }) {
  const roles = [
    {
      label: "Business owner",
      name: vendor.ownership.business_owner_name,
      id: vendor.ownership.business_owner_membership_id,
    },
    {
      label: "Security owner",
      name: vendor.ownership.security_owner_name,
      id: vendor.ownership.security_owner_membership_id,
    },
    {
      label: "Relationship owner",
      name: vendor.ownership.relationship_owner_name,
      id: vendor.ownership.relationship_owner_membership_id,
    },
  ];

  return (
    <Panel title="Ownership">
      <ul className="space-y-3">
        {roles.map((r) => (
          <li key={r.label}>
            <p className="text-caption text-text-subtle">{r.label}</p>
            {r.name ? (
              <p className="mt-1 flex items-center gap-2">
                <Avatar name={r.name} seed={r.id ?? r.name} size="sm" />
                <span className="text-body-sm text-text-primary">{r.name}</span>
              </p>
            ) : (
              <p className="mt-0.5 text-body-sm text-status-warning-text">Unassigned</p>
            )}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function KeyDatesPanel({ vendor }: { vendor: VendorDetail }) {
  const due = daysUntil(vendor.next_reassessment_on);
  return (
    <Panel title="Dates">
      <dl className="space-y-2.5">
        <Field
          label="Next reassessment"
          value={
            vendor.next_reassessment_on ? (
              <span className={due !== null && due < 0 ? "text-status-danger-text" : undefined}>
                {fmtDate(vendor.next_reassessment_on)} ({fmtCountdown(due)})
              </span>
            ) : (
              "After tiering"
            )
          }
        />
        <Field label="Added" value={fmtDate(vendor.created_at)} />
        <Field label="Last changed" value={fmtDate(vendor.updated_at)} />
        <Field
          label="Source"
          value={vendor.source === "manual" ? "Entered by hand" : vendor.source}
        />
      </dl>
    </Panel>
  );
}

function ContactsPanel({
  vendor,
  canManage,
  onAdd,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onAdd: () => void;
}) {
  return (
    <Panel
      title="Contacts"
      count={vendor.contacts.length || undefined}
      action={
        canManage ? (
          <Button variant="ghost" size="icon-sm" aria-label="Add a contact" onClick={onAdd}>
            <Icon name="plus" className="size-4" />
          </Button>
        ) : null
      }
    >
      {vendor.contacts.length === 0 ? (
        <p className="text-body-sm text-text-subtle">No contacts yet.</p>
      ) : (
        <ul className="space-y-2.5">
          {vendor.contacts.map((c) => (
            <li key={c.id}>
              <p className="text-body-sm text-text-primary">{c.name}</p>
              <p className="text-caption text-text-subtle">
                {CONTACT_TYPE_LABEL[c.contact_type] ?? c.contact_type}
                {c.email ? ` · ${c.email}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function DuplicatesPanel({ vendor }: { vendor: VendorDetail }) {
  return (
    <Panel title="Possible duplicates" count={vendor.duplicates.length}>
      <ul className="space-y-2">
        {vendor.duplicates.map((d) => (
          <li key={d.id} className="text-body-sm">
            <Link to={`/vendors/${d.id}`} className="text-text-link underline-offset-2 hover:underline">
              {d.name}
            </Link>
            <span className="block text-caption text-text-subtle">{duplicateReason(d.reason)}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function EngagementPanel({
  vendor,
  engagementId,
}: {
  vendor: VendorDetail;
  engagementId: string;
}) {
  const e = vendor.engagements.find((x) => x.id === engagementId);
  if (!e) return null;
  const stages = vendor.stages.filter((s) => s.engagement_id === engagementId);
  const done = stages.filter((s) => s.status === "complete" || s.status === "skipped").length;

  return (
    <Panel title="This engagement">
      <dl className="space-y-2.5">
        <Field label="Name" value={e.name} />
        <Field label="Internal owner" value={e.internal_owner_name ?? "Unassigned"} />
        <Field
          label="Progress"
          value={
            stages.length > 0 ? (
              <>
                <span className="tabular">
                  {done} of {stages.length} stages settled
                </span>
                <span className="mt-1 block h-1.5 rounded-full bg-surface-sunken">
                  <span
                    className="block h-1.5 rounded-full bg-action-accent"
                    style={{ width: `${(done / stages.length) * 100}%` }}
                  />
                </span>
              </>
            ) : (
              "Not tiered yet"
            )
          }
        />
      </dl>
    </Panel>
  );
}

function AddEngagementDialog({
  open,
  onOpenChange,
  vendorId,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  onAdded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const add = useMutation({
    mutationFn: () =>
      addEngagement(vendorId, { name: name.trim(), service_description: description.trim() }),
    onSuccess: (next) => {
      onAdded(next);
      onOpenChange(false);
      setName("");
      setDescription("");
      toast({ title: "Engagement added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "engagement"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Add engagement</DialogTitle>
          <DialogDescription>Each engagement is tiered and assessed on its own.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) add.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Payroll processing"
              autoFocus
            />
            <TextArea
              label="What this engagement covers"
              optional
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={8000}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={add.isPending} disabled={!name.trim()}>
              Add engagement
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function AddContactDialog({
  open,
  onOpenChange,
  vendorId,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  onAdded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState({ name: "", email: "", phone: "", contact_type: "portal" });

  const add = useMutation({
    mutationFn: () =>
      addContact(vendorId, {
        name: form.name.trim(),
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        contact_type: form.contact_type,
      }),
    onSuccess: (next) => {
      onAdded(next);
      onOpenChange(false);
      setForm({ name: "", email: "", phone: "", contact_type: "portal" });
      toast({ title: "Contact added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "contact"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Add contact</DialogTitle>
          <DialogDescription>Questionnaires go to the portal contact.</DialogDescription>
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
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              autoFocus
            />
            <TextField
              label="Email"
              optional
              type="email"
              hint="Needed to send a questionnaire."
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Phone"
                optional
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              />
              <SelectField label="Kind">
                <Select
                  value={form.contact_type}
                  onValueChange={(v) => setForm((f) => ({ ...f, contact_type: v }))}
                >
                  <SelectTrigger aria-label="Contact type" />
                  <SelectContent>
                    {CONTACT_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {CONTACT_TYPE_LABEL[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={add.isPending} disabled={!form.name.trim()}>
              Add contact
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function OffboardDialog({
  open,
  onOpenChange,
  vendor,
  onOffboarded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor: VendorDetail;
  onOffboarded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const [reason, setReason] = useState("");
  const [scope, setScope] = useState("__all__");

  const start = useMutation({
    mutationFn: () =>
      offboard(vendor.id, reason.trim(), scope === "__all__" ? null : scope),
    onSuccess: (next) => {
      onOffboarded(next);
      onOpenChange(false);
      setReason("");
      toast({ title: "Offboarding started", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "offboarding"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Start offboarding</DialogTitle>
          <DialogDescription>
            Nothing is deleted. A checklist opens and the vendor keeps its history.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (reason.trim()) start.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            {vendor.engagements.length > 1 ? (
              <SelectField label="What is ending">
                <Select value={scope} onValueChange={setScope}>
                  <SelectTrigger aria-label="Offboarding scope" />
                  <SelectContent>
                    <SelectItem value="__all__">The whole relationship</SelectItem>
                    {vendor.engagements.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        Just {e.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
            ) : null}
            <TextArea
              label="Why"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              maxLength={4000}
              placeholder="Replaced by the Contoso agreement from 1 April."
              autoFocus
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive-2" loading={start.isPending} disabled={!reason.trim()}>
              Start offboarding
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
