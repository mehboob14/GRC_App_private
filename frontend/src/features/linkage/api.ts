import { apiFetch } from "@/lib/api/client";
import { controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { listAssets } from "@/features/assets/api";
import { listDocuments } from "@/features/documents/api";
import { listTasks } from "@/features/tasks/api";
import { listVendors } from "@/features/vendors/api";
import { listVulnerabilities } from "@/features/vulnerabilities/api";

/** The records whose pages show linked records through this feature. */
export type AnchorType = "asset" | "vulnerability" | "control" | "document";

export type LinkType =
  | "asset"
  | "vulnerability"
  | "risk"
  | "control"
  | "evidence"
  | "document"
  | "vendor"
  | "task";

export type LinkedRecord = {
  link_id: string;
  target_type: LinkType;
  target_id: string;
  relation: string;
  /** `outgoing` when the link was drawn from this record, else `incoming`. */
  direction: "outgoing" | "incoming";
  code: string;
  title: string;
  status: string;
  detail: string | null;
  can_unlink: boolean;
};

export type LinkedRecords = {
  records: LinkedRecord[];
  /** The groups this record's page shows, in order. */
  offered: LinkType[];
  /** Of those, the types the signed in person may link. */
  can_link: LinkType[];
};

const BASE: Record<AnchorType, string> = {
  asset: "/assets",
  vulnerability: "/vulnerabilities",
  control: "/controls",
  document: "/documents",
};

export const linksKey = (anchorType: AnchorType, anchorId: string) =>
  ["linked-records", anchorType, anchorId] as const;

export const getLinks = (anchorType: AnchorType, anchorId: string) =>
  apiFetch<LinkedRecords>(`${BASE[anchorType]}/${anchorId}/links`);

export const addLink = (
  anchorType: AnchorType,
  anchorId: string,
  targetType: LinkType,
  targetId: string,
) =>
  apiFetch<LinkedRecords>(`${BASE[anchorType]}/${anchorId}/links`, {
    method: "POST",
    body: JSON.stringify({ target_type: targetType, target_id: targetId }),
  });

export const removeLink = (
  anchorType: AnchorType,
  anchorId: string,
  linkId: string,
) =>
  apiFetch<LinkedRecords>(`${BASE[anchorType]}/${anchorId}/links/${linkId}`, {
    method: "DELETE",
  });

export type RaisedRisk = { id: string; code: string; title: string };

/** A risk scored from the finding and linked back to it and its asset. */
export const raiseRiskFromFinding = (instanceId: string, title: string) =>
  apiFetch<RaisedRisk>(`/vulnerabilities/${instanceId}/raise-risk`, {
    method: "POST",
    body: JSON.stringify({ title: title.trim() || null }),
  });

export type Candidate = {
  id: string;
  code: string;
  title: string;
  status: string;
};

const matches = (needle: string, ...values: (string | null | undefined)[]) =>
  !needle || values.some((v) => v?.toLowerCase().includes(needle));

/** One picker search per record type, each on the module's own list. */
export const SEARCH: Record<LinkType, (query: string) => Promise<Candidate[]>> =
  {
    asset: async (q) =>
      (await listAssets({ search: q }, 1, 25)).items.map((a) => ({
        id: a.id,
        code: a.hostname ?? "",
        title: a.name,
        status: a.status,
      })),
    vulnerability: async (q) =>
      (await listVulnerabilities({ search: q }))
        .slice(0, 25)
        .map((v) => ({
          id: v.id,
          code: v.cve_id ?? "",
          title: `${v.title} on ${v.asset_name}`,
          status: v.state,
        })),
    risk: async (q) =>
      (
        await apiFetch<
          { id: string; code: string; title: string; status: string }[]
        >(
          `/risks/refs${q.trim() ? `?search=${encodeURIComponent(q.trim())}` : ""}`,
        )
      ).map((r) => ({
        id: r.id,
        code: r.code,
        title: r.title,
        status: r.status,
      })),
    control: async (q) =>
      (await controlsApi.list({ search: q.trim() || undefined }))
        .slice(0, 25)
        .map((c) => ({
          id: c.id,
          code: c.code,
          title: c.name,
          status: c.status,
        })),
    evidence: async (q) => {
      const needle = q.trim().toLowerCase();
      return (await evidenceApi.list())
        .filter((e) => matches(needle, e.title))
        .slice(0, 25)
        .map((e) => ({
          id: e.id,
          code: "",
          title: e.title,
          status: e.freshness,
        }));
    },
    document: async (q) => {
      const needle = q.trim().toLowerCase();
      return (await listDocuments())
        .filter((d) => matches(needle, d.title, d.code))
        .slice(0, 25)
        .map((d) => ({
          id: d.id,
          code: d.code,
          title: d.title,
          status: d.lifecycle,
        }));
    },
    vendor: async (q) =>
      (await listVendors({ search: q }, 1, 25)).items.map((v) => ({
        id: v.id,
        code: "",
        title: v.name,
        status: v.lifecycle_status,
      })),
    task: async (q) =>
      (await listTasks({ search: q }, 1, 25)).items.map((t) => ({
        id: t.id,
        code: t.code,
        title: t.title,
        status: t.status,
      })),
  };
