import type { IconName } from "@/components/ui";
import type { LinkedRecord, LinkType } from "./api";

export const LINK_META: Record<
  LinkType,
  {
    label: string;
    plural: string;
    icon: IconName;
    href: (id: string) => string;
  }
> = {
  risk: {
    label: "Risk",
    plural: "Risks",
    icon: "risk",
    href: (id) => `/risks/${id}`,
  },
  control: {
    label: "Control",
    plural: "Controls",
    icon: "controls",
    href: (id) => `/controls/${id}`,
  },
  evidence: {
    label: "Evidence",
    plural: "Evidence",
    icon: "doc",
    href: (id) => `/evidence/${id}`,
  },
  document: {
    label: "Document",
    plural: "Documents",
    icon: "book",
    href: (id) => `/documents/${id}`,
  },
  vendor: {
    label: "Vendor",
    plural: "Vendors",
    icon: "vendor",
    href: (id) => `/vendors/${id}`,
  },
  task: {
    label: "Task",
    plural: "Tasks",
    icon: "checklist",
    href: (id) => `/tasks/${id}`,
  },
  asset: {
    label: "Asset",
    plural: "Assets",
    icon: "box",
    href: (id) => `/assets/${id}`,
  },
  vulnerability: {
    label: "Vulnerability",
    plural: "Vulnerabilities",
    icon: "bug",
    href: (id) => `/vulnerabilities/${id}`,
  },
};

/** What the edge means, read from the record the page is about. Plain "relates to" says nothing. */
export function relationLabel(record: LinkedRecord): string | null {
  const incoming = record.direction === "incoming";
  switch (record.relation) {
    case "caused_by":
      return incoming ? "Raised from this" : "Caused by";
    case "remediates":
      return incoming ? "Fixes this" : "Remediates";
    case "depends_on":
      return incoming ? "Depends on this" : "Depends on";
    case "duplicates":
      return "Duplicate";
    default:
      return null;
  }
}

export const humanize = (value: string) => {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};
