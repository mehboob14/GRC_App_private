import type { IconName } from "@/components/ui";
import type { AnchorType, LinkedRecord, LinkType } from "./api";

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

export const isLinkType = (value: string): value is LinkType =>
  Object.prototype.hasOwnProperty.call(LINK_META, value);

/** What a group is called on a given page: the documents that document a control are its policies. */
export const groupLabel = (anchorType: AnchorType, type: LinkType) =>
  anchorType === "control" && type === "document"
    ? "Policies"
    : LINK_META[type].plural;

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
    // Pairs with a table of their own, shown read only on the control and document pages.
    case "mitigates":
      return "Mitigates";
    case "documented_by":
      return "Documented by";
    case "documents":
      return "Documents";
    default:
      return null;
  }
}

export const humanize = (value: string) => {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};
