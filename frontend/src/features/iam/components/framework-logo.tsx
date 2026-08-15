import { useState } from "react";

/**
 * Real brand logo for a framework (ISO, PCI-DSS, SOC 2, NIST, …), resolved by
 * the framework's owning-org domain to a bundled asset in /public/frameworks,
 * falling back to a clean initials badge. Same-origin only — no logo CDN.
 */
const DOMAIN_RULES: Array<[RegExp, string]> = [
  [/hitrust/i, "hitrustalliance.net"],
  [/cobit|isaca/i, "isaca.org"],
  [/pci|data security standard|dss/i, "pcisecuritystandards.org"],
  [/soc\s*-?\s*2|soc2|aicpa|trust\s*service/i, "aicpa.org"],
  [/sox|sarbanes/i, "sec.gov"],
  [/iso|iec|27001|27002|27017|27018|9001|22301|20000|42001/i, "iso.org"],
  [/sama\b|saudi arabian monetary/i, "sama.gov.sa"],
  [/nist|ai rmf|csf|800-?53|800-?171|cybersecurity framework/i, "nist.gov"],
  [/cis\b|critical security control|center for internet/i, "cisecurity.org"],
  [/hipaa|hitech/i, "hhs.gov"],
  [/gdpr|general data protection/i, "gdpr.eu"],
  [/dora|digital operational resilience/i, "esma.europa.eu"],
  [/nis2|nis\s*2|enisa/i, "enisa.europa.eu"],
  [/sbp|state bank of pakistan/i, "sbp.org.pk"],
];

function domainFor(name: string): string {
  for (const [re, domain] of DOMAIN_RULES) {
    if (re.test(name)) return domain;
  }
  return "";
}

function initials(name: string): string {
  const cleaned = (name || "").replace(/[^A-Za-z0-9 ]/g, " ").trim();
  const tokens = cleaned.split(/\s+/).filter(Boolean);
  if (tokens.length >= 2) return (tokens[0][0] + tokens[1][0]).toUpperCase();
  return (cleaned.replace(/\s/g, "").slice(0, 3) || "FW").toUpperCase();
}

export function FrameworkLogo({
  name,
  size = 24,
  className = "",
  eager = false,
}: {
  name: string;
  size?: number;
  className?: string;
  /** Load immediately — marquees animate their container, and lazy-loading
   *  makes icons pop in and out. */
  eager?: boolean;
}) {
  const [assetFailed, setAssetFailed] = useState(false);
  const domain = domainFor(name);

  if (!domain || assetFailed) {
    return (
      <span
        className={`flex shrink-0 items-center justify-center rounded bg-surface-sunken font-bold text-text-secondary ${className}`}
        style={{ width: size, height: size, fontSize: Math.max(8, size * 0.36) }}
        aria-label={name}
        title={name}
      >
        {initials(name)}
      </span>
    );
  }

  return (
    <img
      src={`/frameworks/${domain}.png`}
      alt={name}
      title={name}
      width={size}
      height={size}
      className={`shrink-0 rounded object-contain ${className}`}
      style={{ width: size, height: size }}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      onError={() => setAssetFailed(true)}
    />
  );
}
