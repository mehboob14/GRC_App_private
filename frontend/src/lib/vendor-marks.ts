/**
 * Third-party brand marks shown in the UI (SSO button, connector chips).
 * The hex values are the vendors' own brand colors and are deliberately
 * exempt from the Verity token system: they identify someone else's product
 * and must not re-theme with tenant branding.
 */
export type VendorMark = {
  label: string;
  /** Vendor brand color — third-party identity, exempt from design tokens. */
  color: string;
};

export const VENDOR_MARKS = {
  okta: { label: "OK", color: "#0a6dd8" },
  aws: { label: "AWS", color: "#ff9900" },
  github: { label: "GH", color: "#1b1f24" },
  datadog: { label: "DD", color: "#632ca6" },
} as const satisfies Record<string, VendorMark>;
