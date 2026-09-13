import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  Avatar,
  Badge,
  Button,
  DetailHeader,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorState,
  Icon,
  StatusPill,
  TabStrip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  acknowledgeDocument,
  getDocumentDetail,
  updateDocument,
  mergeIntoDocumentDetail,
} from "@/features/documents/api";
import { VersionHistory } from "./version-history";
import type { ApprovalTier, Document } from "@/features/documents/types";
import { DocumentContentViewer } from "./document-content-viewer";
import { DocumentCampaignsPanel } from "./document-campaigns-panel";
import { DocumentFormDialog } from "./document-form-dialog";
import { TierApprovalCard } from "./tier-approval-card";
import { OwnerSelect } from "@/features/iam/components/owner-select";
import { CLASS_LABEL, LIFECYCLE_META, TYPE_LABEL } from "../labels";

const APPROVAL_LABEL: Record<ApprovalTier["status"], string> = {
  approved: "Approved", pending: "Pending", rejected: "Rejected", not_started: "Not started",
};

function fmtDate(value: string | null): string {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric", month: "long", day: "numeric",
  });
}

// The backend only creates a tier's row once it is first assigned, so a fresh
// draft has zero rows to render. Fill in placeholders up to the fixed 2-tier
// maximum so the owner always has an "Assign" affordance to start with.
const APPROVAL_TIER_COUNT = 2;
function tierCards(approvals: ApprovalTier[]): ApprovalTier[] {
  const byTier = new Map(approvals.map((a) => [a.tier, a]));
  return Array.from({ length: APPROVAL_TIER_COUNT }, (_, i) => i + 1).map(
    (tier) =>
      byTier.get(tier) ?? {
        tier,
        name: `Tier ${tier}`,
        status: "not_started",
        decided_on: null,
        targets: [],
        assignees: [],
        my_decision: null,
      },
  );
}

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "content", label: "Content" },
  { id: "controls", label: "Mappings" },
  { id: "history", label: "Version history" },
  { id: "workflows", label: "Workflows" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const [tab, setTab] = useState<TabId>("overview");
  const [editing, setEditing] = useState(false);
  const [assigningOwner, setAssigningOwner] = useState(false);

  const canManage = Boolean(principal?.permissions.includes("documents:manage"));

  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  const query = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => getDocumentDetail(documentId!),
    enabled: Boolean(documentId),
  });
  const doc = query.data;

  if (query.isLoading) {
    return <p className="w-full text-body-md text-text-subtle">Loading…</p>;
  }
  if (query.isError) {
    const e = describeError(query.error, "document");
    return (
      <div className="w-full">
        <DetailHeader backTo="/documents" backLabel="Back to documents" title="Document" />
        <ErrorState
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void query.refetch() : undefined}
        />
      </div>
    );
  }
  if (!doc) {
    return (
      <div className="w-full">
        <DetailHeader
          backTo="/documents"
          backLabel="Back to documents"
          title="Document not found"
        />
      </div>
    );
  }

  const life = LIFECYCLE_META[doc.lifecycle];
  const openEditor = () =>
    window.open(`/documents/${doc.id}/edit`, "_blank");

  return (
    <div className="w-full">
      <DetailHeader
        icon="book"
        backTo="/documents"
        backLabel="Back to documents"
        title={doc.title}
        chips={
          <>
            <Badge variant="neutral">{TYPE_LABEL[doc.doc_type]}</Badge>
          </>
        }
        actions={
          doc.lifecycle === "published" && !doc.acknowledged_by_me ? (
            <Button
              variant="secondary"
              loading={action.isPending}
              onClick={() => action.mutate(() => acknowledgeDocument(doc.id))}
            >
              <Icon name="check" className="size-4" />
              Acknowledge
            </Button>
          ) : undefined
        }
      />

      {doc.placeholders.length > 0 ? (
        <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-status-warning-border bg-status-warning-bg px-3 py-2 text-body-sm text-status-warning-text">
          <Icon name="alert" className="size-4 shrink-0" aria-hidden />
          <span>
            <strong>
              {doc.placeholders.reduce((n, p) => n + p.count, 0)} placeholder
              {doc.placeholders.reduce((n, p) => n + p.count, 0) === 1 ? "" : "s"}
            </strong>{" "}
            still to fill in before this is ready to approve:{" "}
            {doc.placeholders.map((p) => p.label).join(", ")}.
          </span>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
        <Field label="Status"><StatusPill status={life.family} label={life.label} /></Field>
        <Field label="Version"><Plain>{doc.version}</Plain></Field>
        <Field label="Created on"><Plain>{fmtDate(doc.created_on)}</Plain></Field>
        <Field label="Approved on"><Plain>{fmtDate(doc.approved_on)}</Plain></Field>
        <Field label="Published on"><Plain>{fmtDate(doc.published_on)}</Plain></Field>
        <Field label="Owner">
          {doc.owner ? (
            <span className="flex items-center gap-2">
              <Avatar name={doc.owner.name} size="sm" />
              <span className="text-body-md text-text-primary">{doc.owner.name}</span>
            </span>
          ) : (
            <Plain>Unassigned</Plain>
          )}
        </Field>
      </div>

      <TabStrip
        label="Document sections"
        items={TABS}
        value={tab}
        onSelect={(id) => setTab(id as TabId)}
        className="mt-6"
        inline
      />

      <div>
        {tab === "overview" ? (
          <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
            <Panel
              title="Details"
              action={
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                  Edit
                </Button>
              }
            >
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
                <Meta label="Document name" value={doc.title} />
                <Meta label="Type" value={TYPE_LABEL[doc.doc_type]} />
                <Meta label="Classification" value={CLASS_LABEL[doc.classification]} />
                <Meta label="Renewal date" value={fmtDate(doc.renewal_date)} />
                <Meta label="Assigned to" value={doc.assigned_to ?? "Unassigned"} />
                <Meta
                  label="Frameworks"
                  value={doc.frameworks.length ? doc.frameworks.join(", ") : "None"}
                />
                <div className="col-span-2">
                  <dt className="text-caption text-text-subtle">Description</dt>
                  <dd className="mt-0.5 text-body-md text-text-secondary">
                    {doc.description || "No description"}
                  </dd>
                </div>
              </dl>
            </Panel>

            <div className="space-y-4">
              <Panel
                title="Owner"
                action={
                  canManage ? (
                    <Button variant="secondary" size="sm" onClick={() => setAssigningOwner(true)}>
                      Assign
                    </Button>
                  ) : undefined
                }
              >
                {doc.owner ? (
                  <span className="flex items-center gap-2">
                    <Avatar name={doc.owner.name} size="sm" />
                    <span className="text-body-md text-text-primary">{doc.owner.name}</span>
                  </span>
                ) : (
                  <Plain>Unassigned</Plain>
                )}
              </Panel>
              {tierCards(doc.approvals).map((tier, i, all) => (
                <TierApprovalCard
                  key={tier.tier}
                  documentId={doc.id}
                  tier={tier}
                  canManage={canManage}
                  blockedReason={
                    i > 0 && all[i - 1].targets.length === 0
                      ? `Assign tier ${all[i - 1].tier} first.`
                      : undefined
                  }
                  onAssigned={(next) => mergeIntoDocumentDetail(queryClient, documentId, next)}
                />
              ))}
            </div>
          </div>
        ) : null}

        {tab === "content" ? (
          <DocumentContentViewer doc={doc} onEdit={openEditor} />
        ) : null}

        {tab === "history" ? (
          <Panel title="Version history">
            <VersionHistory
              documentId={documentId}
              versions={doc.versions}
              canManage={canManage}
              lifecycle={doc.lifecycle}
            />
          </Panel>
        ) : null}

        {tab === "workflows" ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Approval history">
              <ol className="space-y-3">
                {tierCards(doc.approvals).map((tier) => (
                  <li key={tier.tier} className="flex items-start gap-3">
                    <span
                      className={cn(
                        "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-caption font-bold",
                        tier.status === "approved"
                          ? "bg-status-success-tint text-status-success-text"
                          : "bg-surface-sunken text-text-subtle",
                      )}
                    >
                      {tier.status === "approved" ? (
                        <Icon name="check" className="size-3.5" />
                      ) : (
                        tier.tier
                      )}
                    </span>
                    <div>
                      <p className="text-body-md text-text-primary">{tier.name}</p>
                      <p className="text-caption text-text-subtle">
                        {APPROVAL_LABEL[tier.status]}
                        {tier.assignees.length
                          ? ` · ${tier.assignees.filter((a) => a.decision === "approved").length}/${tier.assignees.length} signed off`
                          : ""}
                        {tier.decided_on ? ` · ${fmtDate(tier.decided_on)}` : ""}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </Panel>
            <DocumentCampaignsPanel
              documentId={doc.id}
              documentTitle={doc.title}
              canManage={canManage}
            />
          </div>
        ) : null}

        {tab === "controls" ? (
          <Panel
            title="Mappings"
            action={
              canManage ? (
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                  <Icon name="plus" className="size-4" />
                  {doc.controls.length ? "Edit mappings" : "Link controls"}
                </Button>
              ) : undefined
            }
          >
            {doc.controls.length ? (
              <div className="flex flex-wrap gap-2">
                {doc.controls.map((code) => (
                  <button
                    key={code}
                    type="button"
                    onClick={() => navigate(`/controls?search=${encodeURIComponent(code)}`)}
                    className="rounded-sm border border-border bg-surface-primary px-2.5 py-1 font-mono text-caption text-text-secondary hover:border-border-strong"
                  >
                    {code}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-body-sm text-text-subtle">
                No controls linked. Link controls so this document counts toward their coverage.
              </p>
            )}
          </Panel>
        ) : null}
      </div>

      <DocumentFormDialog
        mode="edit"
        document={doc}
        open={editing}
        onOpenChange={setEditing}
      />

      {assigningOwner ? (
        <AssignOwnerDialog
          documentId={doc.id}
          currentOwnerId={doc.owner?.membership_id ?? null}
          currentOwnerName={doc.owner?.name ?? null}
          onOpenChange={setAssigningOwner}
          onAssigned={(next) => {
            mergeIntoDocumentDetail(queryClient, documentId, next);
            queryClient.invalidateQueries({ queryKey: ["documents"] });
          }}
        />
      ) : null}
    </div>
  );
}

function AssignOwnerDialog({
  documentId,
  currentOwnerId,
  currentOwnerName,
  onOpenChange,
  onAssigned,
}: {
  documentId: string;
  currentOwnerId: string | null;
  currentOwnerName: string | null;
  onOpenChange: (open: boolean) => void;
  onAssigned: (doc: Document) => void;
}) {
  const { toast } = useToast();
  const [ownerId, setOwnerId] = useState(currentOwnerId);

  const assign = useMutation({
    mutationFn: () => updateDocument(documentId, { owner_membership_id: ownerId }),
    onSuccess: (doc) => {
      toast({ title: "Owner assigned", tone: "success" });
      onAssigned(doc);
      onOpenChange(false);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Assign owner</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <OwnerSelect value={ownerId} valueLabel={currentOwnerName} onChange={setOwnerId} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={assign.isPending}
            disabled={ownerId === currentOwnerId}
            onClick={() => assign.mutate()}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
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
    <div>
      <dt className="text-caption text-text-subtle">{label}</dt>
      <dd className="mt-0.5 text-body-md text-text-primary">{value}</dd>
    </div>
  );
}

function Plain({ children }: { children: React.ReactNode }) {
  return <span className="text-body-md text-text-primary">{children}</span>;
}
