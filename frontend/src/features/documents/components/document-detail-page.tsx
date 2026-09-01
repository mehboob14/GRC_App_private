import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Avatar,
  Badge,
  Button,
  Dialog,
  DialogContent,
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
  Tooltip,
  TR,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { cn } from "@/lib/cn";
import { useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { iamApi } from "@/lib/api/endpoints";
import {
  acknowledgeDocument,
  decideApproval,
  getDocumentDetail,
  publishDocument,
  submitDocument,
} from "@/features/documents/api";
import type {
  ApprovalTier,
  Classification,
  DocType,
  Lifecycle,
} from "@/features/documents/types";
import { DocumentContentViewer } from "./document-content-viewer";
import { DocumentCampaignsPanel } from "./document-campaigns-panel";
import { DocumentFormDialog } from "./document-form-dialog";

const TYPE_LABEL: Record<DocType, string> = {
  policy: "Policy", standard: "Standard", procedure: "Procedure",
  guideline: "Guideline", charter: "Charter",
};
const CLASS_LABEL: Record<Classification, string> = {
  public: "Public", internal: "Internal", confidential: "Confidential", restricted: "Restricted",
};
const LIFECYCLE_META: Record<Lifecycle, { label: string; family: StatusFamily }> = {
  draft: { label: "Draft", family: "neutral" },
  needs_approval: { label: "Needs approval", family: "pending" },
  approved: { label: "Approved", family: "progress" },
  published: { label: "Published", family: "success" },
  expired: { label: "Expired", family: "danger" },
  archived: { label: "Archived", family: "neutral" },
};
const APPROVAL_FAMILY: Record<ApprovalTier["status"], StatusFamily> = {
  approved: "success", pending: "pending", rejected: "danger", not_started: "neutral",
};
const APPROVAL_LABEL: Record<ApprovalTier["status"], string> = {
  approved: "Approved", pending: "Pending", rejected: "Rejected", not_started: "Not started",
};

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric", month: "long", day: "numeric",
  });
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
  const { documentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const [tab, setTab] = useState<TabId>("overview");
  const [editing, setEditing] = useState(false);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [reviewerId, setReviewerId] = useState("");
  const [approverId, setApproverId] = useState("");

  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));
  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: canReadMembers,
  });
  const members = membersQuery.data ?? [];

  const canManage = Boolean(principal?.permissions.includes("documents:manage"));
  const canApprove = Boolean(principal?.permissions.includes("documents:approve"));
  const canPublish = Boolean(principal?.permissions.includes("documents:publish"));

  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: () => toast({ title: "Action failed", tone: "danger" }),
  });

  const query = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => getDocumentDetail(documentId!),
    enabled: Boolean(documentId),
  });
  const doc = query.data;

  if (query.isLoading) {
    return <p className="mx-auto max-w-[1000px] text-body-md text-text-subtle">Loading…</p>;
  }
  if (!doc) {
    return (
      <div className="mx-auto max-w-[1000px]">
        <Link to="/documents" className="text-body-sm text-text-link">
          Policies &amp; Documents
        </Link>
        <p className="mt-4 text-body-md text-text-secondary">Document not found.</p>
      </div>
    );
  }

  const life = LIFECYCLE_META[doc.lifecycle];
  const pendingTier = doc.approvals.find((a) => a.status === "pending")?.tier ?? null;
  const openEditor = () =>
    window.open(`/documents/${doc.id}/edit`, "_blank");

  return (
    <div className="mx-auto max-w-[1100px]">
      <Link
        to="/documents"
        className="inline-flex items-center gap-1.5 text-body-sm text-text-link hover:underline"
      >
        <Icon name="arrowl" className="size-4" />
        Back to library
      </Link>

      <div className="mt-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="rounded-sm bg-surface-sunken px-2 py-1 font-mono text-caption text-text-subtle">
            {doc.code}
          </span>
          <h1 className="font-display text-heading-lg text-text-primary">{doc.title}</h1>
          <Badge variant="neutral">{TYPE_LABEL[doc.doc_type]}</Badge>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {canManage && (doc.lifecycle === "draft" || doc.lifecycle === "expired") ? (
            doc.owner ? (
              <Button onClick={() => setSubmitOpen(true)}>Send for review</Button>
            ) : (
              <Tooltip content="Assign an owner before sending for review">
                <span tabIndex={0} className="rounded-sm">
                  <Button disabled>Send for review</Button>
                </span>
              </Tooltip>
            )
          ) : null}
          {canApprove && doc.lifecycle === "needs_approval" && pendingTier != null ? (
            <>
              <Button
                variant="secondary"
                loading={action.isPending}
                onClick={() =>
                  action.mutate(() => decideApproval(doc.id, pendingTier, "rejected"))
                }
              >
                Reject
              </Button>
              <Button
                loading={action.isPending}
                onClick={() =>
                  action.mutate(() => decideApproval(doc.id, pendingTier, "approved"))
                }
              >
                Approve tier {pendingTier}
              </Button>
            </>
          ) : null}
          {canPublish && doc.lifecycle === "approved" ? (
            <Button
              loading={action.isPending}
              onClick={() => action.mutate(() => publishDocument(doc.id))}
            >
              Publish
            </Button>
          ) : null}
          {doc.lifecycle === "published" && !doc.acknowledged_by_me ? (
            <Button
              variant="secondary"
              loading={action.isPending}
              onClick={() => action.mutate(() => acknowledgeDocument(doc.id))}
            >
              <Icon name="check" className="size-4" />
              Acknowledge
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-8 gap-y-2">
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

      {/* Tabs */}
      <nav className="mt-6 flex items-center gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "relative px-3 py-2 text-label-sm",
              tab === t.id ? "text-text-primary" : "text-text-subtle hover:text-text-secondary",
            )}
          >
            {t.label}
            {tab === t.id ? (
              <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" />
            ) : null}
          </button>
        ))}
      </nav>

      <div className="mt-5">
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
                <Meta label="Assigned to" value={doc.assigned_to ?? "—"} />
                <Meta
                  label="Frameworks"
                  value={doc.frameworks.length ? doc.frameworks.join(", ") : "—"}
                />
                <div className="col-span-2">
                  <dt className="text-caption text-text-subtle">Description</dt>
                  <dd className="mt-0.5 text-body-md text-text-secondary">
                    {doc.description || "—"}
                  </dd>
                </div>
              </dl>
            </Panel>

            <div className="space-y-4">
              <Panel title="Approval">
                <StatusPill status={life.family} label={life.label} />
                <div className="mt-3 space-y-2">
                  {doc.approvals.map((tier) => (
                    <div
                      key={tier.tier}
                      className="rounded-sm border border-border px-3 py-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-body-md text-text-primary">{tier.name}</span>
                        <StatusPill
                          status={APPROVAL_FAMILY[tier.status]}
                          label={APPROVAL_LABEL[tier.status]}
                        />
                      </div>
                      {tier.approver ? (
                        <p className="mt-0.5 text-caption text-text-subtle">{tier.approver}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Owner">
                {doc.owner ? (
                  <span className="flex items-center gap-2">
                    <Avatar name={doc.owner.name} size="sm" />
                    <span className="text-body-md text-text-primary">{doc.owner.name}</span>
                  </span>
                ) : (
                  <Plain>Unassigned</Plain>
                )}
              </Panel>
            </div>
          </div>
        ) : null}

        {tab === "content" ? (
          <DocumentContentViewer doc={doc} onEdit={openEditor} />
        ) : null}

        {tab === "history" ? (
          <Panel title="Version history">
            <Table>
              <THead>
                <TR>
                  <TH>Version</TH>
                  <TH>Change</TH>
                  <TH>Date</TH>
                  <TH>By</TH>
                  <TH>Summary</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {doc.versions.map((v) => (
                  <TR key={v.version}>
                    <TD><span className="tabular font-medium text-text-primary">{v.version}</span></TD>
                    <TD><Badge variant="neutral">{v.change_type}</Badge></TD>
                    <TD>{fmtDate(v.created_on)}</TD>
                    <TD>{v.created_by}</TD>
                    <TD><span className="text-body-sm text-text-secondary">{v.summary}</span></TD>
                    <TD>
                      <StatusPill
                        status={v.status === "current" ? "success" : "neutral"}
                        label={v.status === "current" ? "Current" : "Superseded"}
                      />
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </Panel>
        ) : null}

        {tab === "workflows" ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Approval workflow">
              <ol className="space-y-3">
                {doc.approvals.map((tier) => (
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
                        {tier.approver ? ` · ${tier.approver}` : ""}
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

      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Send for review</DialogTitle>
            <p className="text-body-md text-text-secondary">
              Choose who reviews and who gives final approval. They sign off in order.
            </p>
          </DialogHeader>
          <div className="space-y-3">
            <SelectField label="Reviewer (tier 1)" optional>
              <Select
                value={reviewerId || "none"}
                onValueChange={(v) => setReviewerId(v === "none" ? "" : v)}
              >
                <SelectTrigger aria-label="Reviewer" />
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {members.map((m) => (
                    <SelectItem key={m.membership_id} value={m.membership_id}>
                      {m.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Approver (tier 2)" optional>
              <Select
                value={approverId || "none"}
                onValueChange={(v) => setApproverId(v === "none" ? "" : v)}
              >
                <SelectTrigger aria-label="Approver" />
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {members.map((m) => (
                    <SelectItem key={m.membership_id} value={m.membership_id}>
                      {m.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setSubmitOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={action.isPending}
              onClick={() => {
                action.mutate(() =>
                  submitDocument(doc.id, [reviewerId, approverId].filter(Boolean)),
                );
                setSubmitOpen(false);
              }}
            >
              Send for review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
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
