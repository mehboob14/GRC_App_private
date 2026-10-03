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

/** WCAG 2.x relative luminance of #RRGGBB. */
function relativeLuminance(hex: string): number {
  const [r = 0, g = 0, b = 0] = parseHex(hex).map((channel) => {
    const s = channel / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two #RRGGBB colours, 1 to 21. */
export function contrastRatio(hexA: string, hexB: string): number {
  const a = relativeLuminance(hexA);
  const b = relativeLuminance(hexB);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function mixHex(hexA: string, hexB: string, weightB: number): string {
  const channels = mixHexChannels(hexA, hexB, weightB)
    .split(" ")
    .map((channel) => Number(channel).toString(16).padStart(2, "0"));
  return `#${channels.join("")}`;
}

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
const WHITE = "#FFFFFF";
const BLACK = "#000000";
/** AA for body text: white labels on the accent, and the accent as text on its tint. */
const MIN_TEXT_CONTRAST = 4.5;
/** Darken in small steps, and give up past this share: a colour that needs more is a
 *  light colour that cannot carry text, not one to bend into a grey. */
const DARKEN_STEP = 0.04;
const MAX_DARKEN = 0.5;
/** The tint the theme derives from the accent (see ThemeProvider.setAccent). */
const TINT_WEIGHT = 0.9;

/**
 * A workspace's brand colour, made safe to use as the app's accent, or null.
 *
 * The accent fills buttons under white labels, colours links on white, and colours
 * the active item's text on its own light tint, so a colour that cannot hold 4.5:1
 * on all three would make the UI unreadable. A colour that fails is darkened in
 * small steps until it passes; one that is not #RRGGBB, or is so light it would
 * need darkening past half, is ignored and the caller keeps Verity's own accent.
 */
export function readableAccent(hex: string | null | undefined): string | null {
  if (!hex || !HEX_COLOR.test(hex)) return null;
  for (let darkened = 0; darkened <= MAX_DARKEN; darkened += DARKEN_STEP) {
    const candidate = mixHex(hex, BLACK, darkened);
    const tint = mixHex(candidate, WHITE, TINT_WEIGHT);
    if (
      contrastRatio(candidate, WHITE) >= MIN_TEXT_CONTRAST &&
      contrastRatio(candidate, tint) >= MIN_TEXT_CONTRAST
    ) {
      return candidate;
    }
  }
  return null;
}
