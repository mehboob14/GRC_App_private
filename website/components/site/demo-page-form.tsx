"use client";

import { useSearchParams } from "next/navigation";
import { DemoForm } from "./demo-form";

/** The /demo/ form, preselecting interests from ?interest=… links. */
export function DemoPageForm({ endpoint }: { endpoint: string | null }) {
  const params = useSearchParams();
  return <DemoForm endpoint={endpoint} interest={params.get("interest")} source="demo-page" />;
}
