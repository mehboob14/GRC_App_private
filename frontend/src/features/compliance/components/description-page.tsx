import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { DraftButton } from "@/features/onboarding/components/draft-button";
import { Link, useNavigate } from "react-router-dom";
import { Button, ErrorState, Skeleton, useToast } from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";

/**
 * SOC 2 system description (guided onboarding EN-6): for each area, what your records already
 * say and what you still need to write. The description itself is a document from the
 * template, approved like any other.
 */

type Area = { key: string; title: string; filled: string[]; to_write: string };
type Required = { rows: { template: string | null; document_id: string | null; state: string }[] };

const TEMPLATE = "soc2-system-description";

export function DescriptionPage() {
  const { principal } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const canDraft = hasPermission(principal, "controls:manage");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const areas = useQuery({
    queryKey: ["description-inputs", principal?.tenant_id],
    queryFn: () => apiFetch<Area[]>("/engagement/description-inputs"),
  });
  const required = useQuery({
    queryKey: ["required-documents", principal?.tenant_id],
    queryFn: () => apiFetch<Required>("/onboarding/required-documents"),
    enabled: hasPermission(principal, "documents:read"),
  });
  const start = useMutation({
    mutationFn: () =>
      apiFetch<{ id: string }>("/documents/from-template", {
        method: "POST",
        body: JSON.stringify({ template_key: TEMPLATE }),
      }),
    onSuccess: (doc) => navigate(`/documents/${doc.id}`),
    onError: (error: unknown) => toast({ title: errorToast(error, "description"), tone: "danger" }),
  });

  if (areas.isLoading) return <Skeleton className="h-64 w-full rounded-lg" />;
  if (areas.isError || !areas.data) {
    const failure = describeError(areas.error, "description");
    return <ErrorState title={failure.title} description={failure.message} referenceId={failure.referenceId} />;
  }
  const doc = required.data?.rows.find((r) => r.template === TEMPLATE);

  return (
    <div className="max-w-[900px]">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {doc?.document_id ? (
          <Button asChild>
            <Link to={`/documents/${doc.document_id}`}>Open the description</Link>
          </Button>
        ) : hasPermission(principal, "documents:manage") ? (
          <Button loading={start.isPending} onClick={() => start.mutate()}>
            Start the description
          </Button>
        ) : null}
      </div>
      <div className="space-y-3">
        {areas.data.map((a) => (
          <section key={a.key} className="rounded-lg border border-border bg-surface-primary px-5 py-4">
            <h2 className="font-display text-title-md text-text-primary">{a.title}</h2>
            {a.filled.length ? (
              <ul className="mt-2 list-disc pl-5 text-body-sm text-text-secondary">
                {a.filled.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-body-sm text-text-subtle">Nothing in your records yet.</p>
            )}
            <p className="mt-2 text-body-sm text-text-primary">{a.to_write}</p>
            {canDraft ? (
              <div className="mt-2">
                <DraftButton kind="description_section" subject={a.key} onDraft={(t) => setDrafts({ ...drafts, [a.key]: t })} />
                {drafts[a.key] ? (
                  <p className="mt-2 whitespace-pre-wrap rounded-md bg-surface-sunken p-3 text-body-sm text-text-primary">
                    {drafts[a.key]}
                  </p>
                ) : null}
              </div>
            ) : null}
          </section>
        ))}
      </div>
    </div>
  );
}
