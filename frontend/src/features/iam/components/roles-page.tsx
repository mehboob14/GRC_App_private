import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
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
import type { PermissionKey } from "@/lib/api/types";

const PERMISSIONS: { key: PermissionKey; label: string }[] = [
  { key: "tenant:read", label: "Read workspace" },
  { key: "members:read", label: "View members" },
  { key: "members:invite", label: "Invite members" },
  { key: "members:disable", label: "Disable members" },
  { key: "groups:read", label: "View groups" },
  { key: "groups:manage", label: "Manage groups" },
  { key: "roles:read", label: "View roles" },
  { key: "roles:manage", label: "Manage roles" },
  { key: "audit:read", label: "Read audit log" },
];

export function RolesPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [keys, setKeys] = useState<PermissionKey[]>(["tenant:read"]);
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      iamApi.createRole({ name: name.trim(), permission_keys: keys }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      setOpen(false);
      setName("");
      setKeys(["tenant:read"]);
      setError(null);
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError ? err.message : "Could not create role.");
    },
  });

  const canManage = principal?.permissions.includes("roles:manage");

  if (query.isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load roles"
        description={
          query.error instanceof ApiError ? query.error.message : "Try again."
        }
        onRetry={() => void query.refetch()}
      />
    );
  }

  const roles = query.data ?? [];

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-[28px] font-extrabold leading-8 tracking-[-0.56px] text-text">
            Roles &amp; permissions
          </h1>
          <p className="mt-2 text-[14px] leading-5 text-text-muted">
            Permission diff — what a role adds and removes versus today.
          </p>
        </div>
        {canManage ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Icon name="plus" className="size-4" />
                Custom role
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create custom role</DialogTitle>
                <DialogDescription>
                  Built-in names (Admin, Auditor, …) stay reserved for the
                  platform.
                </DialogDescription>
              </DialogHeader>
              <TextField
                label="Role name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <fieldset className="mt-3 space-y-2">
                <legend className="mb-2 text-label-sm text-text-muted">
                  Permissions
                </legend>
                {PERMISSIONS.map((perm) => {
                  const checked = keys.includes(perm.key);
                  return (
                    <label
                      key={perm.key}
                      className="flex items-center gap-2 text-body-md text-text"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(value) => {
                          setKeys((prev) =>
                            value
                              ? [...prev, perm.key]
                              : prev.filter((k) => k !== perm.key),
                          );
                        }}
                      />
                      {perm.label}
                    </label>
                  );
                })}
              </fieldset>
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
                  Create role
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {roles.length === 0 ? (
        <EmptyState title="No roles" description="Unexpected empty role list." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Role</TH>
              <TH>Permissions</TH>
              <TH>Assignments</TH>
            </TR>
          </THead>
          <TBody>
            {roles.map((role) => (
              <TR key={role.id}>
                <TD>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{role.name}</span>
                    {role.built_in ? (
                      <Badge variant="neutral">Built-in</Badge>
                    ) : (
                      <Badge variant="role">Custom</Badge>
                    )}
                  </div>
                </TD>
                <TD>
                  <span className="text-text-muted">
                    {role.permission_keys.length} keys
                  </span>
                </TD>
                <TD>{role.assignment_count}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
