/**
 * The app's brand mark, in one place so every surface shows the same thing.
 *
 * TEMPORARY — DEMO ONLY. `public/brand/app-mark.png` is currently the Vimeo
 * logo, which belongs to Vimeo Inc. and is not Verity's. It is here at the
 * client's request to have *a* mark for demos, and must be replaced with the
 * real Verity mark before this is shown to anyone outside the project or
 * deployed anywhere public.
 *
 * Replacing it is one step: drop the real file at `public/brand/app-mark.png`.
 * Removing it is one step: restore the `<Icon name="check" />` block below.
 * Nothing else in the app references the asset path.
 */
export function BrandMark({
  size = 32,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-md ${className}`}
      style={{ width: size, height: size }}
    >
      <img
        src="/brand/app-mark.png"
        alt=""
        aria-hidden
        width={size}
        height={size}
        className="size-full object-contain"
        decoding="async"
      />
    </span>
  );
}
