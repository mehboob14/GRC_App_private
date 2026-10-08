/**
 * How a likelihood and an impact become a score. The server holds the same rule in the
 * `risk_score` SQL function; this copy only draws what the register already stores.
 */
export type ScoringMethod = "product" | "additive" | "weighted";

export type ScoringFormula = {
  method: ScoringMethod;
  likelihood_weight?: number;
  impact_weight?: number;
};

export const PRODUCT_FORMULA: ScoringFormula = { method: "product" };

export function scoreOf(formula: ScoringFormula | undefined, likelihood: number, impact: number): number {
  switch (formula?.method) {
    case "additive":
      return likelihood + impact;
    case "weighted":
      return likelihood * (formula.likelihood_weight ?? 1) + impact * (formula.impact_weight ?? 1);
    default:
      return likelihood * impact;
  }
}

export const METHOD_META: Record<ScoringMethod, { label: string; text: string }> = {
  product: { label: "Likelihood times impact", text: "The usual matrix. A 4 and a 3 score 12." },
  additive: { label: "Likelihood plus impact", text: "Flatter scores. A 4 and a 3 score 7." },
  weighted: { label: "Weighted", text: "Each axis counts for more or less. Likelihood x 2 plus impact scores 11 for a 4 and a 3." },
};

export type Appetite = Record<string, { appetite: number; tolerance: number }>;

export const APPETITE_META: Record<string, { label: string; family: "success" | "warning" | "danger" }> = {
  within: { label: "Within appetite", family: "success" },
  tolerated: { label: "Above appetite", family: "warning" },
  breach: { label: "Beyond tolerance", family: "danger" },
};
