import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/cn";
import { identityTone, initials, type IdentityTone } from "@/lib/color";

const toneClass: Record<IdentityTone, string> = {
  1: "bg-identity-1",
  2: "bg-identity-2",
  3: "bg-identity-3",
  4: "bg-identity-4",
  5: "bg-identity-5",
  6: "bg-identity-6",
};

type AvatarProps = {
  name: string;
  seed?: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClass = {
  sm: "size-6 text-[10px]",
  md: "size-[30px] text-[11.5px]",
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
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-sans font-bold text-text-inverse",
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
