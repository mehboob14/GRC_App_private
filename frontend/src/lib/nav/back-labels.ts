/**
 * What to call the page a Back link goes to, from its path.
 *
 * Specific shapes come before general ones. A path no one has named returns null,
 * and the caller then keeps the static "Back to <parent>" it was given rather than
 * guess: a wrong label on a link is worse than a plain one.
 */
const LABELS: readonly [RegExp, string][] = [
  [/^\/controls\/[^/]+$/, "Back to control"],
  [/^\/controls$/, "Back to controls"],
  [/^\/evidence\/[^/]+$/, "Back to evidence item"],
  [/^\/evidence$/, "Back to evidence"],
  [/^\/documents\/campaigns\/[^/]+$/, "Back to campaign"],
  [/^\/documents\/[^/]+\/approvals\/[^/]+$/, "Back to review"],
  [/^\/documents\/[^/]+$/, "Back to document"],
  [/^\/documents$/, "Back to documents"],
  [/^\/tasks\/(overview|settings|automations)$/, "Back to tasks"],
  [/^\/tasks\/[^/]+$/, "Back to task"],
  [/^\/tasks$/, "Back to tasks"],
  [/^\/assets\/(overview|settings|import)$/, "Back to assets"],
  [/^\/assets\/[^/]+$/, "Back to asset"],
  [/^\/assets$/, "Back to assets"],
  [/^\/vendors\/questionnaires\/[^/]+$/, "Back to questionnaire"],
  [/^\/vendors\/(overview|intake|findings|questionnaires|roster|policy)$/, "Back to vendors"],
  [/^\/vendors\/[^/]+$/, "Back to vendor"],
  [/^\/vendors$/, "Back to vendors"],
  [/^\/risks\/(overview|library|assessments|indicators|settings)$/, "Back to risks"],
  [/^\/risks\/[^/]+$/, "Back to risk"],
  [/^\/risks$/, "Back to risks"],
  [/^\/vulnerabilities\/(overview|settings|import)$/, "Back to vulnerabilities"],
  [/^\/vulnerabilities\/[^/]+$/, "Back to vulnerability"],
  [/^\/vulnerabilities$/, "Back to vulnerabilities"],
  [/^\/frameworks\/(dashboard|list|scope|coverage)$/, "Back to frameworks"],
  [/^\/frameworks\/[^/]+$/, "Back to framework"],
  [/^\/frameworks$/, "Back to frameworks"],
  [/^\/trace\/.+$/, "Back to trace"],
  [/^\/connectors(\/.*)?$/, "Back to connections"],
  [/^\/dashboard$/, "Back to dashboard"],
  [/^\/quick-start$/, "Back to Get Started"],
  [/^\/audit-log$/, "Back to audit log"],
  [/^\/settings(\/.*)?$/, "Back to settings"],
  [/^\/provider\/tenants$/, "Back to tenants"],
  [/^\/provider\/tenants\/.+$/, "Back to tenant"],
];

/**
 * The record a path belongs to, or null for a list or any other page.
 *
 * A record's tabs are pushed as routes (`/provider/tenants/7/profile`, then
 * `/provider/tenants/7/branding`). The page before one of them is then another tab of
 * the same record, and Back must not step through the tabs: it goes to the parent.
 */
export function recordOf(path: string): string | null {
  const pathname = path.split("?")[0].replace(/\/+$/, "");
  const match =
    /^(\/provider\/tenants\/[^/]+|\/(?:controls|evidence|documents|tasks|assets|vendors|risks|vulnerabilities|frameworks)\/[^/]+)(?:\/.*)?$/.exec(
      pathname,
    );
  return match ? match[1] : null;
}

export function backLabelFor(path: string): string | null {
  const pathname = path.split("?")[0].replace(/\/+$/, "") || "/";
  for (const [pattern, label] of LABELS) {
    if (pattern.test(pathname)) return label;
  }
  return null;
}
