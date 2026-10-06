export type AuditExportFormat = "xlsx" | "csv";

/** What the Export dialog asks for. `from` and `to` are UTC days (YYYY-MM-DD), both
 *  inclusive, and empty means that end is open. */
export type AuditExportOptions = {
  format: AuditExportFormat;
  from: string;
  to: string;
  includeSystem: boolean;
};
