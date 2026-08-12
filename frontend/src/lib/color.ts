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
  return parseHex(hex).join(" ");
}

/**
 * Mix two hex colours in sRGB and return "R G B" channels.
 * `weightB` is the share of `hexB` (0 → pure A, 1 → pure B). Used to derive
 * tenant-accent hover/tint/border shades in both themes.
 */
export function mixHexChannels(
  hexA: string,
  hexB: string,
  weightB: number,
): string {
  const a = parseHex(hexA);
  const b = parseHex(hexB);
  const w = Math.min(1, Math.max(0, weightB));
  return a.map((ch, i) => Math.round(ch * (1 - w) + (b[i] ?? 0) * w)).join(" ");
}

function parseHex(hex: string): [number, number, number] {
  const cleaned = hex.replace("#", "").trim();
  if (cleaned.length !== 6) {
    throw new Error(`Expected #RRGGBB, got ${hex}`);
  }
  return [
    Number.parseInt(cleaned.slice(0, 2), 16),
    Number.parseInt(cleaned.slice(2, 4), 16),
    Number.parseInt(cleaned.slice(4, 6), 16),
  ];
}
