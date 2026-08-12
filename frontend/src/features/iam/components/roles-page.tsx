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
  const alertRef = useAlertFocus(error !== null);

  const query = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      iamApi.createRole({ name: name.trim(), permission_keys: keys }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["roles", principal?.tenant_id],
        exact: true,
      });
      setOpen(false);
      setName("");
      setKeys(["tenant:read"]);
      setError(null);
    },
    onError: (err: unknown) => {
      setError(
        err instanceof ApiError
          ? err.message
          : "The role didn't reach the server — check your connection and try again.",
      );
    },
  });

  const canManage = principal?.permissions.includes("roles:manage");

  if (query.isLoading) {
    return <TableSkeleton rows={4} density="standard" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load roles"
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

  const roles = query.data ?? [];

  return (
    <div>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-heading-sm text-text-primary">
            Roles &amp; permissions
          </h2>
          <p className="mt-1 text-body-md text-text-secondary">
            Built-in roles are fixed by the platform; custom roles pick from
            the same permission keys.
          </p>
        </div>
        {canManage ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="shrink-0">
                <Icon name="plus" className="size-4" />
                New custom role
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
              <form
                className="flex flex-col gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (name.trim()) createMutation.mutate();
                }}
                noValidate
              >
                {error ? (
                  <ErrorBanner ref={alertRef} title="Couldn't create the role">
                    {error}
                  </ErrorBanner>
                ) : null}
                <TextField
                  label="Role name"
                  placeholder="Compliance analyst"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <fieldset>
                  <legend className="mb-2 font-sans text-label-sm text-text-secondary">
                    Permissions
                  </legend>
                  <div className="space-y-2">
                    {PERMISSIONS.map((perm) => {
                      const checked = keys.includes(perm.key);
                      return (
                        <label
                          key={perm.key}
                          className="flex items-center gap-2 text-body-md text-text-primary"
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
                  </div>
                </fieldset>
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
                    Create role
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {roles.length === 0 ? (
        <EmptyState
          icon="shield"
          title="No roles to show"
          description="Built-in roles should always exist — retry, or contact support if this persists."
        />
      ) : (
        <Table density="standard">
          <THead>
            <TR>
              <TH>Role</TH>
              <TH numeric>Permissions</TH>
              <TH numeric>Assignments</TH>
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
                <TD numeric>{role.permission_keys.length}</TD>
                <TD numeric>{role.assignment_count}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
