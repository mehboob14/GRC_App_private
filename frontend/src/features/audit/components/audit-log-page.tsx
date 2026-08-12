import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  EmptyState,
  ErrorState,
  Skeleton,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";
import { auditApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

function formatWhen(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function AuditLogPage() {
  const { principal } = useAuth();

  const query = useQuery({
    queryKey: ["audit-log", principal?.tenant_id],
    queryFn: () => auditApi.list(),
  });

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-5xl space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="mx-auto max-w-5xl">
        <ErrorState
          title="Couldn’t load audit log"
          description={
            query.error instanceof ApiError ? query.error.message : "Try again."
          }
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  }

  const items = query.data?.items ?? [];

  return (
    <div className="mx-auto max-w-5xl">
      <p className="type-overline mb-2">Access &amp; Audit</p>
      <h1 className="font-display text-heading-lg text-text">Audit log</h1>
      <p className="mt-1 mb-6 text-body-md text-text-muted">
        Append-only trail for this workspace. Never updated or deleted.
      </p>

      {items.length === 0 ? (
        <EmptyState
          title="No events yet"
          description="State-changing actions will appear here."
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>When</TH>
              <TH>Actor</TH>
              <TH>Action</TH>
              <TH>Object</TH>
            </TR>
          </THead>
          <TBody>
            {items.map((event) => (
              <TR key={event.id}>
                <TD className="whitespace-nowrap text-text-muted">
                  {formatWhen(event.occurred_at)}
                </TD>
                <TD>{event.actor_label}</TD>
                <TD>
                  <Badge variant="neutral">{event.action}</Badge>
                </TD>
                <TD>
                  <div>
                    <p className="font-semibold text-text">{event.object_label}</p>
                    <p className="text-body-sm text-text-faint">
                      {event.object_type}
                    </p>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
