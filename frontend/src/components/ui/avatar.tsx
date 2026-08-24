import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/cn";
import { identityTone, initials } from "@/lib/color";
import { toneClass } from "./identity-color";

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
