/**
 * The `verity` block of a file a connector filed as evidence (connectors/service.py
 * `_evidence`): what was looked at, what was left out and why, and what each check
 * found. The rest of the file is the provider's own inventory, which stays raw.
 */

export type SnapshotOutcome = "pass" | "fail" | "error" | "not_applicable";

export type ConnectorSnapshot = {
  connection: { provider: string; account: string };
  /** The check this file is evidence of. Absent on files filed before each check had its own. */
  check?: { key: string; name: string; description?: string | null };
  collected_at: string;
  access?: string;
  scope: {
    listed: number;
    checked: number;
    excluded: { resource: string; reason: string | null; decided_by: string }[];
  };
  results: {
    check: string | null;
    /** Absent on files filed before checks carried a name. */
    name?: string | null;
    resource: string;
    outcome: SnapshotOutcome;
    summary: string | null;
    /** `plan` when the provider does not offer the feature on the account's plan. */
    reason?: string | null;
  }[];
};

/** The report of a file, or null when it is not one a connector filed. */
export function parseSnapshot(text: string): ConnectorSnapshot | null {
  try {
    const verity = (JSON.parse(text) as { verity?: Partial<ConnectorSnapshot> } | null)
      ?.verity;
    return verity &&
      Array.isArray(verity.results) &&
      verity.scope &&
      Array.isArray(verity.scope.excluded) &&
      verity.connection
      ? (verity as ConnectorSnapshot)
      : null;
  } catch {
    return null;
  }
}
