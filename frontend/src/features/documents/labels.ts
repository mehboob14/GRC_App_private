import type { Classification, DocType } from "./types";

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

export const CLASS_LABEL: Record<Classification, string> = {
  public: "Public",
  internal: "Internal",
  confidential: "Confidential",
  restricted: "Restricted",
};
