import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import type { AttachInput } from "../api";

/** What the person has chosen to attach: items already in the library, and files to add. */
export type AttachSelection = AttachInput;
export const NO_ATTACHMENTS: AttachSelection = { evidenceIds: [], files: [] };

export const hasAttachments = (a: AttachSelection) => a.evidenceIds.length > 0 || a.files.length > 0;

/** Attaching touches the evidence library, so it follows that module's keys: read to pick an
 *  item that is already there, manage to add a new one. */
export function useAttachAccess() {
  const { principal } = useAuth();
  const canPick = hasPermission(principal, "evidence:read");
  const canUpload = hasPermission(principal, "evidence:manage");
  return { canPick, canUpload, canAttach: canPick || canUpload };
}
