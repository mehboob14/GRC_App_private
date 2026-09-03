import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Icon } from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { listDocumentCampaigns } from "../api";
import type { CampaignSummary } from "../types";
import { CreateCampaignDialog } from "./create-campaign-dialog";

function Progress({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-caption text-text-subtle">
          <span className="tabular text-text-secondary">{done}</span> of{" "}
          <span className="tabular text-text-secondary">{total}</span> acknowledged
        </span>
        <span className="tabular text-caption font-semibold text-text-secondary">{pct}%</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-sunken">
        <span
          className="block h-full rounded-full bg-action-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * The document's acknowledgement campaigns — the real read-and-sign flow that
 * replaces the old static "attestation" stand-in. Owners start a campaign and
 * track completion here; each row opens the campaign's own page.
 */
export function DocumentCampaignsPanel({
  documentId,
  documentTitle,
  canManage,
}: {
  documentId: string;
  documentTitle: string;
  canManage: boolean;
}) {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  const campaignsQuery = useQuery({
    queryKey: ["document-campaigns", documentId],
    queryFn: () => listDocumentCampaigns(documentId),
  });
  const campaigns = campaignsQuery.data ?? [];

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-sm text-text-primary">Acknowledgement campaigns</h2>
        {canManage ? (
          <Button variant="secondary" size="sm" onClick={() => setCreating(true)}>
            <Icon name="plus" className="size-4" />
            Start campaign
          </Button>
        ) : null}
      </div>

      {campaignsQuery.isError ? (
        <p className="text-body-sm text-status-danger-text">
          {describeError(campaignsQuery.error, "campaign list").message}
        </p>
      ) : campaigns.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No campaigns yet. Start one to ask reviewers and approvers to read and sign this document.
        </p>
      ) : (
        <ul className="space-y-2.5">
          {campaigns.map((c: CampaignSummary) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => navigate(`/documents/campaigns/${c.id}`)}
                className="w-full rounded-md border border-border p-3 text-left transition-colors hover:border-border-strong hover:bg-surface-hover"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate text-body-sm font-semibold text-text-primary">
                    {c.title}
                  </span>
                  <Badge variant={c.status === "active" ? "statusReview" : "neutral"}>
                    {c.status === "active" ? "Active" : "Closed"}
                  </Badge>
                </div>
                <Progress done={c.acknowledged} total={c.total} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {creating ? (
        <CreateCampaignDialog
          documentId={documentId}
          documentTitle={documentTitle}
          onOpenChange={setCreating}
          onCreated={(campaign) => navigate(`/documents/campaigns/${campaign.id}`)}
        />
      ) : null}
    </div>
  );
}
