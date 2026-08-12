const IDENTITY_KEYS = [1, 2, 3, 4, 5, 6] as const;

export type IdentityTone = (typeof IDENTITY_KEYS)[number];

/** Deterministic avatar tone from a stable person id / email. */
export function identityTone(seed: string): IdentityTone {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return IDENTITY_KEYS[hash % IDENTITY_KEYS.length] ?? 1;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  if (!first) return "?";
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const second = parts[1] ?? "";
  return `${first.charAt(0)}${second.charAt(0)}`.toUpperCase();
}

/** Convert #RRGGBB to "R G B" for CSS custom properties. */
export function hexToRgbChannels(hex: string): string {
  const cleaned = hex.replace("#", "").trim();
  if (cleaned.length !== 6) {
    throw new Error(`Expected #RRGGBB, got ${hex}`);
  }
  const r = Number.parseInt(cleaned.slice(0, 2), 16);
  const g = Number.parseInt(cleaned.slice(2, 4), 16);
  const b = Number.parseInt(cleaned.slice(4, 6), 16);
  return `${r} ${g} ${b}`;
}
