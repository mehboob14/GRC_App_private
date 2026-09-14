import { z } from "zod";

/**
 * The password rules a new workspace starts with, mirrored from the backend's
 * DEFAULT_PASSWORD_POLICY (modules/iam/service.py): 12 characters, an upper and
 * a lower case letter, a digit and a symbol. Showing them live means nobody
 * learns a rule from a rejected submit.
 */

// The backend's symbol set, character for character.
const SYMBOLS = "!@#$%^&*()-_=+[]{};:'\",.<>/?\\|`~ ";

export type PasswordRule = {
  key: string;
  label: string;
  test: (password: string) => boolean;
};

export const DEFAULT_PASSWORD_RULES: PasswordRule[] = [
  {
    key: "length",
    label: "12 or more characters",
    test: (p) => p.length >= 12,
  },
  {
    key: "upper",
    label: "An uppercase letter",
    test: (p) => /\p{Lu}/u.test(p),
  },
  { key: "lower", label: "A lowercase letter", test: (p) => /\p{Ll}/u.test(p) },
  { key: "digit", label: "A number", test: (p) => /\p{Nd}/u.test(p) },
  {
    key: "symbol",
    label: "A symbol",
    test: (p) => Array.from(p).some((c) => SYMBOLS.includes(c)),
  },
];

export type Strength = {
  met: number;
  total: number;
  level: 0 | 1 | 2 | 3 | 4;
  label: string;
};

const LABELS = ["Too weak", "Weak", "Fair", "Good", "Strong"] as const;

export function passwordStrength(
  password: string,
  rules: PasswordRule[] = DEFAULT_PASSWORD_RULES,
): Strength {
  const met = rules.filter((r) => r.test(password)).length;
  if (!password)
    return { met, total: rules.length, level: 0, label: LABELS[0] };
  // Every rule met is Good; a long password on top of that is Strong.
  const allMet = met === rules.length;
  const level = (
    allMet
      ? password.length >= 16
        ? 4
        : 3
      : Math.min(2, Math.floor((met / rules.length) * 3))
  ) as Strength["level"];
  return { met, total: rules.length, level, label: LABELS[level] };
}

export function unmetRules(
  password: string,
  rules: PasswordRule[] = DEFAULT_PASSWORD_RULES,
): PasswordRule[] {
  return rules.filter((r) => !r.test(password));
}

/** "Your password needs a number and a symbol." Every gap named at once, like the server does. */
export function describeUnmet(unmet: PasswordRule[]): string {
  const parts = unmet.map(
    (r) => r.label.charAt(0).toLowerCase() + r.label.slice(1),
  );
  const list =
    parts.length === 1
      ? parts[0]
      : `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
  return `Your password needs ${list}.`;
}

/**
 * A new password, checked against the default rules. A workspace with a
 * stricter policy still has the last word: the server's answer lands on the
 * password field.
 */
export const newPasswordSchema = z
  .string()
  .min(1, "Choose a password.")
  .superRefine((value, ctx) => {
    const unmet = unmetRules(value);
    if (unmet.length)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: describeUnmet(unmet),
      });
  });
