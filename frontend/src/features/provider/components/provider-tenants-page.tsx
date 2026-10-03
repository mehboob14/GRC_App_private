import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Button,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PageHeader,
  Pagination,
  SearchInput,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
} from "@/components/ui";
import { describeProviderError } from "../errors";
import { useDebouncedValue, useTenantsPage } from "../hooks";
import { STATUS_META, formatDate, tenantName } from "../tokens";
import { TENANT_STATUSES, type TenantStatus } from "../types";
import { RegisterTenantDialog } from "./register-tenant-dialog";

const PAGE_SIZE = 25;

export function ProviderTenantsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TenantStatus | undefined>(undefined);
  const [registerOpen, setRegisterOpen] = useState(false);
  // The register pages by cursor, so a page number can only be jumped to once its
  // cursor is known: cursors[n - 1] opens page n, and each page teaches us the next.
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [page, setPage] = useState(1);

  const term = useDebouncedValue(search.trim());
  const query = useTenantsPage({
    search: term || undefined,
    status,
    cursor: cursors[page - 1] ?? null,
    limit: PAGE_SIZE,
  });

  const nextCursor = query.data?.next_cursor ?? null;
  const settled = !query.isPlaceholderData;
  useEffect(() => {
    if (settled && nextCursor && cursors.length === page) {
      setCursors((known) => [...known, nextCursor]);
    }
  }, [settled, nextCursor, cursors.length, page]);

  function changeFilter(apply: () => void) {
    apply();
    setCursors([null]);
    setPage(1);
  }

  const filtered = Boolean(term || status);
  const items = query.data?.items ?? [];
  const failure = query.isError
    ? describeProviderError(query.error, "register")
    : null;

  return (
    <div>
      <PageHeader
        title="Tenants"
        icon="vendor"
        subtitle="Every workspace on the platform"
        actions={
          <Button onClick={() => setRegisterOpen(true)}>
            <Icon name="plus" className="size-4" />
            Register tenant
          </Button>
        }
      />

      <Toolbar
        searchLabel="Filter tenants"
        search={
          <SearchInput
            value={search}
            onChange={(value) => changeFilter(() => setSearch(value))}
            placeholder="Search name or address"
            aria-label="Search tenants"
          />
        }
      >
        <FilterFacet
          label="Status"
          options={TENANT_STATUSES.map((value) => ({
            value,
            label: STATUS_META[value].label,
          }))}
          values={status ? [status] : []}
          onChange={(values) =>
            changeFilter(() =>
              setStatus(values[values.length - 1] as TenantStatus | undefined),
            )
          }
        />
        {filtered ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              changeFilter(() => {
                setSearch("");
                setStatus(undefined);
              })
            }
          >
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      <div className="mt-4">
        {query.isLoading ? (
          <TableSkeleton rows={6} />
        ) : failure ? (
          <ErrorState
            title={failure.title}
            description={failure.message}
            referenceId={failure.referenceId}
            onRetry={failure.retryable ? () => void query.refetch() : undefined}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon="vendor"
            variant={filtered ? "no-match" : "no-data"}
            title={filtered ? "No tenants match" : "No tenants yet"}
            description={
              filtered
                ? "Try a different name or clear the filters."
                : "Register the first workspace to get started."
            }
            onClearFilters={() =>
              changeFilter(() => {
                setSearch("");
                setStatus(undefined);
              })
            }
            action={
              <Button onClick={() => setRegisterOpen(true)}>
                Register tenant
              </Button>
            }
          />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Tenant</TH>
                <TH>Plan</TH>
                <TH>Status</TH>
                <TH>Registered</TH>
              </TR>
            </THead>
            <TBody>
              {items.map((tenant) => (
                <TR
                  key={tenant.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/provider/tenants/${tenant.id}`)}
                >
                  <TD>
                    <Link
                      to={`/provider/tenants/${tenant.id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="block min-w-0 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
                    >
                      <span className="block truncate text-body-md font-medium text-text-primary">
                        {tenantName(tenant)}
                      </span>
                      <span className="block truncate font-mono text-caption text-text-subtle">
                        {tenant.slug}
                      </span>
                    </Link>
                  </TD>
                  <TD>
                    <span className="text-body-sm text-text-secondary">
                      {tenant.plan}
                    </span>
                  </TD>
                  <TD>
                    <StatusPill
                      status={STATUS_META[tenant.status].family}
                      label={STATUS_META[tenant.status].label}
                    />
                  </TD>
                  <TD>
                    <span className="text-body-sm text-text-secondary">
                      {formatDate(tenant.created_at)}
                    </span>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </div>

      <Pagination
        className="mt-4 justify-end"
        page={page}
        pageCount={cursors.length}
        onPageChange={setPage}
      />

      <RegisterTenantDialog open={registerOpen} onOpenChange={setRegisterOpen} />
    </div>
  );
}
