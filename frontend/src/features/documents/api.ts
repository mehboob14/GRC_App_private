import { ApiError, apiFetch } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import type {
  ApprovalTier,
  Campaign,
  CampaignCreateInput,
  CampaignSummary,
  Classification,
  Document,
  DocumentDetail,
  DocumentKpis,
  DocumentVersion,
  DocType,
  Lifecycle,
  PendingCampaign,
} from "./types";

/**
 * Data layer for the documents module, wired to the real backend (Stage 8).
 * Backend responses are mapped to the frontend `Document` shape here, so the
 * components stay unchanged from the mock era.
 */

type RawDocument = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  doc_type: DocType;
  classification: Classification;
  lifecycle: Lifecycle;
  content_format: "html" | "pdf" | "docx";
  filename: string | null;
  version: string | null;
  owner_membership_id: string | null;
  owner_name: string | null;
  assigned_to: string | null;
  renewal_date: string | null;
  created_at: string;
  approved_at: string | null;
  published_at: string | null;
  archived_at: string | null;
  updated_at: string;
  frameworks: string[];
  controls: string[];
  attestation_pct: number | null;
};

type RawVersion = {
  version_no: string;
  change_type: "major" | "minor" | "patch";
  created_at: string;
  created_by_name: string | null;
  summary: string | null;
  is_current: boolean;
};

type RawApproval = {
  tier: number;
  status: ApprovalTier["status"];
  approver_name: string | null;
  decided_at: string | null;
};

type RawDetail = RawDocument & {
  content_html: string | null;
  versions: RawVersion[];
  approvals: RawApproval[];
  acknowledged: number;
  assigned_count: number;
  acknowledged_by_me: boolean;
};

const day = (iso: string | null): string | null => (iso ? iso.slice(0, 10) : null);

function toDocument(r: RawDocument): Document {
  return {
    id: r.id,
    code: r.code,
    title: r.title,
    description: r.description ?? "",
    doc_type: r.doc_type,
    classification: r.classification,
    lifecycle: r.lifecycle,
    version: r.version ?? "—",
    content_format: r.content_format,
    filename: r.filename,
    owner: r.owner_membership_id
      ? { membership_id: r.owner_membership_id, name: r.owner_name ?? "Unknown" }
      : null,
    frameworks: r.frameworks,
    controls: r.controls,
    attestation_pct: r.attestation_pct,
    assigned_to: r.assigned_to,
    created_on: day(r.created_at),
    approved_on: day(r.approved_at),
    published_on: day(r.published_at),
    renewal_date: r.renewal_date,
    updated_at: day(r.updated_at),
  };
}

function toVersion(v: RawVersion): DocumentVersion {
  return {
    version: v.version_no,
    change_type: v.change_type,
    created_on: day(v.created_at) ?? "",
    created_by: v.created_by_name ?? "System",
    summary: v.summary ?? "",
    status: v.is_current ? "current" : "superseded",
  };
}

function toApproval(a: RawApproval): ApprovalTier {
  return {
    tier: a.tier,
    name: `Tier ${a.tier}`,
    status: a.status,
    approver: a.approver_name,
    decided_on: day(a.decided_at),
  };
}

function toDetail(r: RawDetail): DocumentDetail {
  return {
    ...toDocument(r),
    content_html: r.content_html,
    versions: r.versions.map(toVersion),
    approvals: r.approvals.map(toApproval),
    acknowledged: r.acknowledged,
    assigned_count: r.assigned_count,
    acknowledged_by_me: r.acknowledged_by_me,
  };
}

export async function listDocuments(): Promise<Document[]> {
  const raw = await apiFetch<RawDocument[]>("/documents");
  return raw.map(toDocument);
}

export async function documentKpis(): Promise<DocumentKpis> {
  return apiFetch<DocumentKpis>("/documents/kpis");
}

export async function getDocumentDetail(id: string): Promise<DocumentDetail | null> {
  try {
    return toDetail(await apiFetch<RawDetail>(`/documents/${id}`));
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export type AuthoredInput = {
  title: string;
  description?: string | null;
  doc_type: DocType;
  classification: Classification;
  content_html?: string | null;
  assigned_to?: string | null;
  owner_membership_id?: string | null;
  framework_ids: string[];
  control_ids: string[];
};

export async function createDocument(input: AuthoredInput): Promise<Document> {
  return toDocument(
    await apiFetch<RawDocument>("/documents", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  );
}

export type UploadFields = {
  title: string;
  doc_type: DocType;
  classification: Classification;
  description?: string | null;
};

export async function uploadDocument(file: File, fields: UploadFields): Promise<Document> {
  const form = new FormData();
  form.set("file", file);
  form.set("title", fields.title);
  form.set("doc_type", fields.doc_type);
  form.set("classification", fields.classification);
  if (fields.description) form.set("description", fields.description);
  return toDocument(
    await apiFetch<RawDocument>("/documents/upload", { method: "POST", body: form }),
  );
}

export type DocumentPatch = {
  title?: string;
  description?: string | null;
  doc_type?: DocType;
  classification?: Classification;
  assigned_to?: string | null;
  owner_membership_id?: string | null;
  clear_owner?: boolean;
  framework_ids?: string[];
  control_ids?: string[];
};

export async function updateDocument(id: string, patch: DocumentPatch): Promise<Document> {
  return toDocument(
    await apiFetch<RawDocument>(`/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  );
}

export async function archiveDocument(id: string, reason: string): Promise<void> {
  await apiFetch<RawDocument>(`/documents/${id}/archive`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function saveDocumentContent(
  id: string,
  content_html: string,
  change_type: "major" | "minor" | "patch" = "minor",
  summary?: string,
): Promise<DocumentDetail> {
  return toDetail(
    await apiFetch<RawDetail>(`/documents/${id}/content`, {
      method: "PUT",
      body: JSON.stringify({ content_html, change_type, summary }),
    }),
  );
}

export async function submitDocument(
  id: string,
  approverIds: string[] = [],
): Promise<Document> {
  return toDocument(
    await apiFetch<RawDocument>(`/documents/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ approver_ids: approverIds }),
    }),
  );
}

export async function decideApproval(
  id: string,
  tier: number,
  decision: "approved" | "rejected",
  note?: string,
): Promise<Document> {
  return toDocument(
    await apiFetch<RawDocument>(`/documents/${id}/approvals/${tier}/decide`, {
      method: "POST",
      body: JSON.stringify({ decision, note }),
    }),
  );
}

export async function publishDocument(id: string): Promise<Document> {
  return toDocument(await apiFetch<RawDocument>(`/documents/${id}/publish`, { method: "POST" }));
}

export async function acknowledgeDocument(id: string): Promise<void> {
  await apiFetch<void>(`/documents/${id}/acknowledge`, { method: "POST" });
}

/** Authenticated file fetch for the viewer/download (blob; a plain link 401s). */
export async function downloadDocumentBlob(id: string): Promise<Blob> {
  const response = await fetch(`/api/v1/documents/${id}/download`, {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  return response.blob();
}

// -- acknowledgement campaigns ----------------------------------------------

export async function createCampaign(
  documentId: string,
  input: CampaignCreateInput,
): Promise<Campaign> {
  return apiFetch<Campaign>(`/documents/${documentId}/campaigns`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function listDocumentCampaigns(documentId: string): Promise<CampaignSummary[]> {
  return apiFetch<CampaignSummary[]>(`/documents/${documentId}/campaigns`);
}

export async function getCampaign(campaignId: string): Promise<Campaign | null> {
  try {
    return await apiFetch<Campaign>(`/documents/campaigns/${campaignId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function myPendingCampaigns(): Promise<PendingCampaign[]> {
  return apiFetch<PendingCampaign[]>("/documents/campaigns/pending");
}

export async function myPendingCampaignCount(): Promise<number> {
  const { count } = await apiFetch<{ count: number }>("/documents/campaigns/pending/count");
  return count;
}

export async function acknowledgeCampaign(
  campaignId: string,
  comment?: string,
): Promise<Campaign> {
  return apiFetch<Campaign>(`/documents/campaigns/${campaignId}/acknowledge`, {
    method: "POST",
    body: JSON.stringify({ comment: comment ?? null }),
  });
}

export async function commentOnCampaign(
  campaignId: string,
  body: string,
  mentionedIds: string[] = [],
): Promise<Campaign> {
  return apiFetch<Campaign>(`/documents/campaigns/${campaignId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body, mentioned_ids: mentionedIds }),
  });
}

export async function closeCampaign(campaignId: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/documents/campaigns/${campaignId}/close`, { method: "POST" });
}
