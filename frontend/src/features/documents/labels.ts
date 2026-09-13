import type { StatusFamily } from "@/components/ui/status-pill";
import type { Classification, DocType, Lifecycle } from "./types";

/**
 * Human labels for a document's type and classification.
 *
 * These were defined identically in three components and were about to be
 * copied into a fourth. One definition, so a rename lands everywhere.
 */
export const TYPE_LABEL: Record<DocType, string> = {
  policy: "Policy",
  standard: "Standard",
  procedure: "Procedure",
  guideline: "Guideline",
  charter: "Charter",
};

/** Lifecycle to pill family and label. */
export const LIFECYCLE_META: Record<Lifecycle, { label: string; family: StatusFamily }> = {
  draft: { label: "Draft", family: "neutral" },
  needs_approval: { label: "Needs approval", family: "pending" },
  approved: { label: "Approved", family: "progress" },
  published: { label: "Published", family: "success" },
  expired: { label: "Expired", family: "danger" },
  archived: { label: "Archived", family: "neutral" },
};

export const CLASS_LABEL: Record<Classification, string> = {
  public: "Public",
  internal: "Internal",
  confidential: "Confidential",
  restricted: "Restricted",
};
