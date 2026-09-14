/**
 * Small kindnesses for the email field: catch "gmial.com" before a
 * verification link goes nowhere, nudge toward a work address without blocking
 * a personal one, and offer a one click way into the inbox.
 */

const COMMON_DOMAINS = [
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "outlook.com",
  "hotmail.com",
  "live.com",
  "icloud.com",
  "aol.com",
  "proton.me",
  "protonmail.com",
];

const PERSONAL_DOMAINS = new Set([
  ...COMMON_DOMAINS,
  "me.com",
  "msn.com",
  "gmx.com",
  "mail.com",
  "yandex.com",
  "zoho.com",
]);

const TLD_TYPOS: Record<string, string> = {
  con: "com",
  cmo: "com",
  ocm: "com",
  comm: "com",
  vom: "com",
  xom: "com",
  cpm: "com",
  nte: "net",
  ogr: "org",
};

// Edit distance where swapping two neighbours ("gmial") costs one edit, not two:
// transpositions are the most common typing slip.
function distance(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) =>
    Array.from({ length: b.length + 1 }, (_, j) =>
      i === 0 ? j : j === 0 ? i : 0,
    ),
  );
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(
        d[i - 1][j] + 1,
        d[i][j - 1] + 1,
        d[i - 1][j - 1] + cost,
      );
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
    }
  }
  return d[a.length][b.length];
}

function split(email: string): [string, string] | null {
  const at = email.trim().lastIndexOf("@");
  if (at < 1) return null;
  return [
    email.trim().slice(0, at),
    email
      .trim()
      .slice(at + 1)
      .toLowerCase(),
  ];
}

/** The address the person probably meant, or null when it already looks right. */
export function suggestEmail(email: string): string | null {
  const parts = split(email);
  if (!parts) return null;
  const [local, domain] = parts;
  // A real provider is never "corrected" (mail.com is one edit from gmail.com).
  if (!domain.includes(".") || PERSONAL_DOMAINS.has(domain)) return null;
  const close = COMMON_DOMAINS.find((d) => {
    const gap = distance(domain, d);
    return gap > 0 && gap <= (d.length > 9 ? 2 : 1);
  });
  if (close) return `${local}@${close}`;
  const dot = domain.lastIndexOf(".");
  const tld = domain.slice(dot + 1);
  if (TLD_TYPOS[tld])
    return `${local}@${domain.slice(0, dot)}.${TLD_TYPOS[tld]}`;
  return null;
}

export function isPersonalEmail(email: string): boolean {
  const parts = split(email);
  return parts ? PERSONAL_DOMAINS.has(parts[1]) : false;
}

export type Webmail = { label: string; href: string };

/** Where to open the inbox. A work domain could be either provider, so both. */
export function webmailFor(email: string): Webmail[] {
  const domain = split(email)?.[1] ?? "";
  if (domain === "gmail.com" || domain === "googlemail.com") {
    return [{ label: "Open Gmail", href: "https://mail.google.com/" }];
  }
  if (["outlook.com", "hotmail.com", "live.com", "msn.com"].includes(domain)) {
    return [{ label: "Open Outlook", href: "https://outlook.live.com/mail/" }];
  }
  if (domain === "yahoo.com")
    return [{ label: "Open Yahoo Mail", href: "https://mail.yahoo.com/" }];
  if (domain === "icloud.com" || domain === "me.com") {
    return [
      { label: "Open iCloud Mail", href: "https://www.icloud.com/mail/" },
    ];
  }
  if (domain === "proton.me" || domain === "protonmail.com") {
    return [{ label: "Open Proton Mail", href: "https://mail.proton.me/" }];
  }
  return [
    { label: "Open Gmail", href: "https://mail.google.com/" },
    { label: "Open Outlook", href: "https://outlook.office.com/mail/" },
  ];
}
