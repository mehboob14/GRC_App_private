import { identityTone, type IdentityTone } from "@/lib/color";

/**
 * Pale fill, same-hue initials. A solid dark disc with white text is heavy at
 * 24px and makes two different people read as the same mark; the tint keeps the
 * hue legible while letting the name stay the loudest thing in the row.
 *
 * These live outside `avatar.tsx` so that file exports only its component: a
 * module that mixes components with plain helpers loses fast refresh.
 */
export const toneClass: Record<IdentityTone, string> = {
  1: "bg-identity-tint-1 text-identity-1",
  2: "bg-identity-tint-2 text-identity-2",
  3: "bg-identity-tint-3 text-identity-3",
  4: "bg-identity-tint-4 text-identity-4",
  5: "bg-identity-tint-5 text-identity-5",
  6: "bg-identity-tint-6 text-identity-6",
};

/**
 * Deterministic identity-ramp fill for non-person marks that share the
 * avatar vocabulary (workspace tiles in the switcher). Identity colours are
 * per-entity hashes, never semantic tokens.
 */
export function identityBgClass(seed: string): string {
  return toneClass[identityTone(seed)];
}
