import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/cn";
import { identityTone, initials, type IdentityTone } from "@/lib/color";

/**
 * Pale fill, same-hue initials. A solid dark disc with white text is heavy at
 * 24px and makes two different people read as the same mark; the tint keeps the
 * hue legible while letting the name stay the loudest thing in the row.
 */
const toneClass: Record<IdentityTone, string> = {
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

type AvatarProps = {
  name: string;
  seed?: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

/** DS: owner-cell avatar 24 · skeleton/list avatar 32 · card avatar 36. */
const sizeClass = {
  sm: "size-6 text-[10px]",
  md: "size-8 text-caption",
  lg: "size-9 text-label-sm",
} as const;

export function Avatar({
  name,
  seed,
  src,
  size = "md",
  className,
}: AvatarProps) {
  const tone = identityTone(seed ?? name);
  return (
    <AvatarPrimitive.Root
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-sans font-bold",
        toneClass[tone],
        sizeClass[size],
        className,
      )}
    >
      {src ? <AvatarPrimitive.Image src={src} alt="" className="size-full object-cover" /> : null}
      <AvatarPrimitive.Fallback delayMs={src ? 400 : 0} className="leading-none">
        {initials(name)}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}
