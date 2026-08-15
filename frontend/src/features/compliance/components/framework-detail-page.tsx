import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  SearchInput,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";
import { complianceApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import type { Requirement } from "@/lib/api/types";

/** DS §6.4 code chip — Sora on the accent tint. A criterion renders the same
 *  way on every screen it appears. */
function CodeChip({ code }: { code: string }) {
  return (
    <span className="inline-flex rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link">
      {code}
    </span>
  );
}

export function FrameworkDetailPage() {
  const { frameworkId = "" } = useParams();
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState<string[]>([]);

  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
  });
  const requirementsQuery = useQuery({
    queryKey: ["requirements", frameworkId],
    queryFn: () => complianceApi.listRequirements(frameworkId),
    enabled: frameworkId.length > 0,
  });

  const framework = (frameworksQuery.data ?? []).find((f) => f.id === frameworkId);
  const requirements = useMemo(
    () => requirementsQuery.data ?? [],
    [requirementsQuery.data],
  );

  // The Trust Services Categories present, in the order the criteria arrive.
  const categoryOptions = useMemo(() => {
    const seen: string[] = [];
    for (const requirement of requirements) {
      if (!seen.includes(requirement.trust_services_category)) {
        seen.push(requirement.trust_services_category);
      }
    }
    return seen.map((value) => ({ value, label: value }));
  }, [requirements]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return requirements.filter(
      (requirement) =>
        (categories.length === 0 ||
          categories.includes(requirement.trust_services_category)) &&
        (query === "" ||
          requirement.code.toLowerCase().includes(query) ||
          requirement.name.toLowerCase().includes(query)),
    );
  }, [requirements, search, categories]);

  const activeFilters = [
    ...categories.map((category) => `Category: ${category}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];

  function clearFilters() {
    setSearch("");
    setCategories([]);
  }

  if (requirementsQuery.isError) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <ErrorState
          title="Couldn’t load criteria"
          description={
            requirementsQuery.error instanceof ApiError
              ? requirementsQuery.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          referenceId={
            requirementsQuery.error instanceof ApiError
              ? requirementsQuery.error.correlationId
              : undefined
          }
          onRetry={() => void requirementsQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <Link
        to="/frameworks"
        className="mb-3 inline-flex items-center gap-1.5 text-body-sm font-semibold text-text-link"
      >
        <Icon name="chevr" className="size-3.5 rotate-180" aria-hidden />
        Frameworks
      </Link>

      <h1 className="font-display text-heading-lg text-text-primary">
        {framework?.name ?? "Framework"}
      </h1>
      <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
        Every criterion in this framework, and how many shipped control
        templates satisfy each one.
      </p>

      <div className="mb-4 mt-5 flex flex-wrap items-center gap-2">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by code or text…"
          aria-label="Search criteria"
          className="w-full sm:w-72"
        />
        {categoryOptions.length > 1 ? (
          <FilterFacet
            label="Category"
            options={categoryOptions}
            values={categories}
            onChange={setCategories}
          />
        ) : null}
        {activeFilters.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
        <p aria-live="polite" className="ml-auto text-caption text-text-subtle">
          Showing <span className="tabular">{visible.length}</span> of{" "}
          <span className="tabular">{requirements.length}</span> criteria
        </p>
      </div>

      {requirementsQuery.isLoading ? (
        <TableSkeleton rows={8} density="comfortable" />
      ) : visible.length === 0 ? (
        <EmptyState
          variant="no-match"
          title="No criteria match your filters"
          description={
            activeFilters.length > 0
              ? `Try removing ${activeFilters.map((f) => `'${f}'`).join(" or ")}.`
              : "This framework version has no criteria loaded."
          }
          onClearFilters={activeFilters.length > 0 ? clearFilters : undefined}
        />
      ) : (
        <Table density="comfortable">
          <THead>
            <TR>
              <TH>Criterion</TH>
              <TH>Category</TH>
              <TH>Trust services</TH>
              <TH numeric>Controls</TH>
            </TR>
          </THead>
          <TBody>
            {visible.map((requirement: Requirement) => (
              <TR key={requirement.id}>
                <TD>
                  <div className="flex items-start gap-2.5">
                    <CodeChip code={requirement.code} />
                    <span className="min-w-0 text-body-md text-text-primary">
                      {requirement.name}
                    </span>
                  </div>
                </TD>
                <TD>
                  <span className="text-body-sm text-text-secondary">
                    {requirement.category}
                  </span>
                </TD>
                <TD>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="neutral">
                      {requirement.trust_services_category}
                    </Badge>
                    {requirement.is_always_in_scope ? (
                      <span className="text-caption text-text-subtle">
                        always in scope
                      </span>
                    ) : null}
                  </div>
                </TD>
                {/* A criterion with no mapped template is a real gap in the
                    shipped library, so the zero is shown, not hidden. */}
                <TD numeric>
                  <span
                    className={
                      requirement.template_count === 0
                        ? "text-status-warning-text"
                        : undefined
                    }
                  >
                    {requirement.template_count}
                  </span>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
