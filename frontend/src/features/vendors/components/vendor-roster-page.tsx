import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  ErrorState,
  Icon,
  PersonSelect,
  Skeleton,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getRoster, listMembers, removeRosterRole, setRosterRole } from "../api";
import { ROSTER_ROLES } from "../types";
import { ROSTER_ROLE_META } from "../tokens";

/**
 * Who plays which part in the programme.
 *
 * This is not a permission editor — permissions live on roles in Settings. It
 * decides who gets named and notified when a stage needs a particular kind of
 * review, which is why every row says what the part actually does.
 */
export function VendorRosterPage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const rosterQuery = useQuery({ queryKey: ["vendor-roster"], queryFn: getRoster });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  const assign = useMutation({
    mutationFn: (input: { role: string; membershipId: string }) =>
      setRosterRole(input.role, input.membershipId),
    onSuccess: (next) => {
      queryClient.setQueryData(["vendor-roster"], next);
      toast({ title: "Roster updated", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "roster"), tone: "danger" }),
  });

  const unassign = useMutation({
    mutationFn: (input: { role: string; membershipId: string }) =>
      removeRosterRole(input.role, input.membershipId),
    onSuccess: (next) => {
      queryClient.setQueryData(["vendor-roster"], next);
      toast({ title: "Removed from the roster", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "roster"), tone: "danger" }),
  });

  if (rosterQuery.isError) {
    const error = describeError(rosterQuery.error, "roster");
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        referenceId={error.referenceId}
        onRetry={error.retryable ? () => void rosterQuery.refetch() : undefined}
      />
    );
  }

  const people = (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name }));
  const nameFor = (id: string) => people.find((p) => p.id === id)?.name ?? "Unknown member";

  return (
    <div className="mt-4 max-w-3xl">
      <p className="text-body-md text-text-secondary">Who the workflow asks at each review stage.</p>

      {!canManage ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          View only. Changing the roster needs the Manage vendors permission.
        </p>
      ) : null}

      <div className="mt-4 divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface-primary">
        {rosterQuery.isLoading
          ? ROSTER_ROLES.map((role) => (
              <div key={role} className="p-4">
                <Skeleton className="h-14 w-full" />
              </div>
            ))
          : ROSTER_ROLES.map((role) => {
              const meta = ROSTER_ROLE_META[role];
              const ids = rosterQuery.data?.roles[role] ?? [];
              return (
                <div
                  key={role}
                  className="grid gap-3 p-4 sm:grid-cols-[minmax(12rem,18rem)_1fr] sm:items-start"
                >
                  <div className="min-w-0">
                    <h2 className="font-display text-title-sm text-text-primary">{meta.label}</h2>
                    <p className="mt-0.5 text-caption text-text-subtle">{meta.blurb}</p>
                  </div>
                  <div className="min-w-0 space-y-2">
                    {ids.length > 0 ? (
                      <ul className="flex flex-wrap gap-2">
                        {ids.map((id) => (
                          <li
                            key={id}
                            className="flex items-center gap-2 rounded-full border border-border bg-surface-sunken py-0.5 pl-0.5 pr-1"
                          >
                            <Avatar name={nameFor(id)} seed={id} size="sm" />
                            <span className="text-body-sm text-text-primary">{nameFor(id)}</span>
                            {canManage ? (
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Remove ${nameFor(id)} from ${meta.label}`}
                                disabled={unassign.isPending}
                                onClick={() => unassign.mutate({ role, membershipId: id })}
                              >
                                <Icon name="x" className="size-3.5" />
                              </Button>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-body-sm text-text-subtle">Nobody assigned</p>
                    )}
                    {canManage ? (
                      <PersonSelect
                        people={people.filter((p) => !ids.includes(p.id))}
                        value={null}
                        onChange={(id) => {
                          if (id) assign.mutate({ role, membershipId: id });
                        }}
                        placeholder={ids.length > 0 ? "Add another…" : "Assign…"}
                        aria-label={`Assign to ${meta.label}`}
                        disabled={assign.isPending}
                      />
                    ) : null}
                  </div>
                </div>
              );
            })}
      </div>

    </div>
  );
}
