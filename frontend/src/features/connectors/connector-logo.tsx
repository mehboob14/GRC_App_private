import { Icon } from "@/components/ui";

/**
 * Neutral brand tile for a connector. Same-origin only: this page calls no
 * logo CDN, so a tenant's tool fires no third-party request per card.
 *
 * The real vendor marks land as bundled SVGs at public/connectors/<id>.svg
 * once they are licensed and exported; swap the icon for an <img> pointing at
 * that path then. Until then the tile is a plug glyph and the connector's name
 * — rendered beside it on both the card and the drawer — carries the identity,
 * so the tile itself is decorative.
 */
export function ConnectorLogo({
  size = 34,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  // DS §4.2: child radius never exceeds parent − inset. The 22px "Source /
  // vendor" tile (§6.4) takes radius xs (6); larger feature tiles take md (10).
  const radius = size <= 24 ? "rounded-xs" : "rounded-md";
  // §4.5 icon scale is closed: 12 · 14 · 16 · 20 · 24 — never a computed size.
  const glyph = size <= 24 ? "size-3" : "size-4";

  return (
    <span
      className={`flex shrink-0 items-center justify-center ${radius} bg-surface-sunken text-text-secondary ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <Icon name="plug" className={glyph} />
    </span>
  );
}
