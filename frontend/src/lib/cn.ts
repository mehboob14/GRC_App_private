import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * tailwind-merge cannot tell a custom font-size class (`text-label-md`)
 * from a custom text-colour class (`text-action-primary-fg`) and would drop
 * one as a "conflict". Teach it the DS type ramp so sizes only conflict with
 * sizes and colours with colours.
 */
const typeRamp = [
  "display-hero",
  "display-xl",
  "heading-xl",
  "heading-lg",
  "heading-md",
  "heading-sm",
  "title-md",
  "title-sm",
  "body-lg",
  "body-md",
  "body-sm",
  "label-md",
  "label-sm",
  "caption",
  "overline",
  "code-chip",
  "numeral-lg",
  "numeral-md",
  "numeral-sm",
];

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: typeRamp }],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
