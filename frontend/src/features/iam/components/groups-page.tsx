import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  EmptyState,
  ErrorBanner,
  ErrorState,
  Icon,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  TextField,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

export function GroupsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const alertRef = useAlertFocus(error !== null);

  const query = useQuery({
    queryKey: ["groups", principal?.tenant_id],
    queryFn: () => iamApi.listGroups(),
  });

  const createMutation = useMutation({
    mutationFn: () => iamApi.createGroup(name.trim()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["groups", principal?.tenant_id],
        exact: true,
      });
      setOpen(false);
      setName("");
      setError(null);
    },
    onError: (err: unknown) => {
      setError(
        err instanceof ApiError
          ? err.message
          : "The group didn't reach the server — check your connection and try again.",
      );
    },
  });

  const canManage = principal?.permissions.includes("groups:manage");

  if (query.isLoading) {
    return <TableSkeleton rows={4} density="standard" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load groups"
        description={
          query.error instanceof ApiError
            ? query.error.message
            : "The request failed. Retry, or contact support if it keeps happening."
        }
        referenceId={
          query.error instanceof ApiError
            ? query.error.correlationId
            : undefined
        }
        onRetry={() => void query.refetch()}
      />
    );
  }

  const groups = query.data ?? [];

  return (
    <div>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-heading-sm text-text-primary">
            Groups
          </h2>
          <p className="mt-1 text-body-md text-text-secondary">
            The join between IdP group, Verity role, and access-review scope.
          </p>
        </div>
        {canManage ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="shrink-0">
                <Icon name="plus" className="size-4" />
                New group
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create group</DialogTitle>
                <DialogDescription>
                  Name a group, then add memberships from People.
                </DialogDescription>
              </DialogHeader>
              <form
                className="flex flex-col gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (name.trim()) createMutation.mutate();
                }}
                noValidate
              >
                {error ? (
                  <ErrorBanner ref={alertRef} title="Couldn't create the group">
                    {error}
                  </ErrorBanner>
                ) : null}
                <TextField
                  label="Group name"
                  placeholder="Engineering"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <DialogFooter>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    loading={createMutation.isPending}
                    disabled={!name.trim()}
                  >
                    Create group
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {groups.length === 0 ? (
        <EmptyState
          icon="users"
          title="No groups yet"
          description="Create a group to assign people together — reviews and role changes then move group-by-group."
        />
      ) : (
        <Table density="standard">
          <THead>
            <TR>
              <TH>Name</TH>
              <TH numeric>Members</TH>
            </TR>
          </THead>
          <TBody>
            {groups.map((group) => (
              <TR key={group.id}>
                <TD className="font-semibold">{group.name}</TD>
                <TD numeric>{group.member_count}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
