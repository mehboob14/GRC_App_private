import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  CodeChip,
  DetailHeader,
  EmptyState,
  ErrorState,
  FilterFacet,
  SearchInput,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
} from "@/components/ui";
import { complianceApi } from "@/lib/api/endpoints";
import { describeError } from "@/lib/api/describe-error";
import type { Requirement } from "@/lib/api/types";

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
    const failure = describeError(requirementsQuery.error, "framework");
    return (
      <div className="w-full">
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          onRetry={
            failure.retryable
              ? () => void requirementsQuery.refetch()
              : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="w-full">
      <DetailHeader
        backTo="/frameworks/list"
        backLabel="Back to frameworks"
        title={framework?.name ?? "Framework"}
        meta={framework?.description}
      />

      <Toolbar
        searchLabel="Filter criteria"
        search={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by code or text…"
            aria-label="Search criteria"
          />
        }
        actions={
          <p aria-live="polite" className="text-caption text-text-subtle">
            Showing <span className="tabular">{visible.length}</span> of{" "}
            <span className="tabular">{requirements.length}</span> criteria
          </p>
        }
      >
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
      </Toolbar>

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
