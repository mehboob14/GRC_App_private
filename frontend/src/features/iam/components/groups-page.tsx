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
  ErrorState,
  Icon,
  Skeleton,
  Table,
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

export function GroupsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

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
      setError(err instanceof ApiError ? err.message : "Could not create group.");
    },
  });

  const canManage = principal?.permissions.includes("groups:manage");

  if (query.isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load groups"
        description={
          query.error instanceof ApiError ? query.error.message : "Try again."
        }
        onRetry={() => void query.refetch()}
      />
    );
  }

  const groups = query.data ?? [];

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-[28px] font-extrabold leading-8 tracking-[-0.56px] text-text">
            Groups
          </h1>
          <p className="mt-2 text-[14px] leading-5 text-text-muted">
            The join between IdP group, Verity role, and access-review scope.
          </p>
        </div>
        {canManage ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Icon name="plus" className="size-4" />
                New group
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create group</DialogTitle>
                <DialogDescription>
                  Name a group, then add memberships from Team.
                </DialogDescription>
              </DialogHeader>
              <TextField
                label="Group name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              {error ? (
                <p className="mt-2 text-body-sm text-fail-fg" role="alert">
                  {error}
                </p>
              ) : null}
              <DialogFooter>
                <Button variant="secondary" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button
                  loading={createMutation.isPending}
                  disabled={!name.trim()}
                  onClick={() => void createMutation.mutate()}
                >
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {groups.length === 0 ? (
        <EmptyState
          title="No groups yet"
          description="Create a group to assign people together."
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Members</TH>
            </TR>
          </THead>
          <TBody>
            {groups.map((group) => (
              <TR key={group.id}>
                <TD className="font-semibold">{group.name}</TD>
                <TD>{group.member_count}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
