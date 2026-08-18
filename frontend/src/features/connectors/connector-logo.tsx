import { useState } from "react";

/**
 * The vendor's own mark for a connector, from the design's integration-logo
 * set, bundled at `public/connectors/<id>.svg`.
 *
 * Same-origin only: this page calls no logo CDN, so opening the catalogue
 * fires no third-party request per card — a tenant's browser never announces
 * which tools they are shopping for.
 *
 * Not every connector in the catalogue has a mark in the design yet. Rather
 * than keep a list that drifts every time an asset is added, a missing file
 * simply fails to load and the tile falls back to the vendor's initials — drop
 * a new SVG into `public/connectors/` and it starts rendering with no code
 * change.
 */
function initials(name: string): string {
  const cleaned = (name || "").replace(/[^A-Za-z0-9 ]/g, " ").trim();
  const tokens = cleaned.split(/\s+/).filter(Boolean);
  if (tokens.length >= 2) return (tokens[0][0] + tokens[1][0]).toUpperCase();
  return (cleaned.replace(/\s/g, "").slice(0, 2) || "?").toUpperCase();
}

export function ConnectorLogo({
  id,
  name = "",
  size = 34,
  className = "",
}: {
  /** Catalogue id — also the asset filename. */
  id?: string;
  name?: string;
  size?: number;
  className?: string;
}) {
  const [assetFailed, setAssetFailed] = useState(false);

  // DS §4.2: child radius never exceeds parent − inset. The 22px "Source /
  // vendor" tile (§6.4) takes radius xs (6); larger feature tiles take md (10).
  const radius = size <= 24 ? "rounded-xs" : "rounded-md";

  if (!id || assetFailed) {
    return (
      <span
        className={`flex shrink-0 items-center justify-center ${radius} bg-surface-sunken font-sans font-bold text-text-secondary ${className}`}
        style={{ width: size, height: size, fontSize: Math.max(9, size * 0.34) }}
        aria-hidden
      >
        {initials(name)}
      </span>
    );
  }

  return (
    <span
      className={`flex shrink-0 items-center justify-center overflow-hidden ${radius} bg-surface-primary ring-1 ring-border ${className}`}
      style={{ width: size, height: size }}
    >
      <img
        src={`/connectors/${id}.svg`}
        alt=""
        width={Math.round(size * 0.68)}
        height={Math.round(size * 0.68)}
        style={{ width: Math.round(size * 0.68), height: Math.round(size * 0.68) }}
        className="object-contain"
        // The catalogue renders 40 cards at once, all above the fold on a wide
        // screen — lazy-loading would pop them in as the grid settles.
        loading="eager"
        decoding="async"
        onError={() => setAssetFailed(true)}
      />
    </span>
  );
}
