import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
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
  useToast,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type { PermissionKey, Role } from "@/lib/api/types";

const PERMISSIONS: { key: PermissionKey; label: string }[] = [
  { key: "tenant:read", label: "Read workspace" },
  { key: "tenant:manage", label: "Manage company profile" },
  { key: "members:read", label: "View members" },
  { key: "members:invite", label: "Invite members" },
  { key: "members:disable", label: "Disable members" },
  { key: "groups:read", label: "View groups" },
  { key: "groups:manage", label: "Manage groups" },
  { key: "roles:read", label: "View roles" },
  { key: "roles:manage", label: "Manage roles" },
  { key: "security:manage", label: "Manage security policy" },
  { key: "audit:read", label: "Read audit log" },
];

export function RolesPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = principal?.permissions.includes("roles:manage");

  const [open, setOpen] = useState(false);
  // null = creating a new role; a role id = editing that role.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [keys, setKeys] = useState<PermissionKey[]>(["tenant:read"]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Role | null>(null);
  const alertRef = useAlertFocus(error !== null);

  const query = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ["roles", principal?.tenant_id],
      exact: true,
    });

  function openCreate() {
    setEditingId(null);
    setName("");
    setKeys(["tenant:read"]);
    setError(null);
    setOpen(true);
  }

  function openEdit(role: Role) {
    setEditingId(role.id);
    setName(role.name);
    setKeys([...role.permission_keys]);
    setError(null);
    setOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      editingId
        ? iamApi.updateRole(editingId, { name: name.trim(), permission_keys: keys })
        : iamApi.createRole({ name: name.trim(), permission_keys: keys }),
    onSuccess: async () => {
      await invalidate();
      setOpen(false);
      toast({
        title: editingId ? "Role updated" : "Role created",
        tone: "success",
      });
    },
    onError: (err: unknown) => {
      setError(
        err instanceof ApiError
          ? err.message
          : "The role didn't reach the server — check your connection and try again.",
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (role: Role) => iamApi.deleteRole(role.id),
    onSuccess: async (_data, role) => {
      await invalidate();
      setToDelete(null);
      toast({ title: `Deleted role “${role.name}”`, tone: "neutral" });
    },
    onError: (err: unknown) => {
      setToDelete(null);
      toast({
        title:
          err instanceof ApiError
            ? err.message
            : "Couldn't delete the role — try again.",
        tone: "danger",
      });
    },
  });

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
          query.error instanceof ApiError ? query.error.correlationId : undefined
        }
        onRetry={() => void query.refetch()}
      />
    );
  }

  const roles = query.data ?? [];

  return (
    <div>
      <div className="mb-4 flex justify-end gap-3">
        {canManage ? (
          <Button className="shrink-0" onClick={openCreate}>
            <Icon name="plus" className="size-4" />
            New custom role
          </Button>
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
              <TH>
                <span className="sr-only">Actions</span>
              </TH>
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
                <TD className="text-right">
                  {canManage && !role.built_in ? (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Actions for ${role.name}`}
                        >
                          <Icon name="more" className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(() => openEdit(role), 0)
                          }
                        >
                          Edit role
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          variant="danger"
                          onSelect={() =>
                            window.setTimeout(() => setToDelete(role), 0)
                          }
                        >
                          Delete role
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  ) : null}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {/* Create / edit share one form. */}
      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setError(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingId ? "Edit role" : "Create custom role"}
            </DialogTitle>
            <DialogDescription>
              {editingId
                ? "Rename this role or change what it can do. Changes apply to everyone who holds it."
                : "Built-in names (Admin, Auditor, …) stay reserved for the platform."}
            </DialogDescription>
          </DialogHeader>
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) saveMutation.mutate();
            }}
            noValidate
          >
            {error ? (
              <ErrorBanner ref={alertRef} title="Couldn't save the role">
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
                loading={saveMutation.isPending}
                disabled={!name.trim()}
              >
                {editingId ? "Save changes" : "Create role"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(next) => {
          if (!next) setToDelete(null);
        }}
        title={`Delete role “${toDelete?.name ?? ""}”?`}
        consequence={
          <>
            This removes the role and any assignments to it. Members keep their
            other roles. This can’t be undone.
          </>
        }
        confirmLabel="Delete role"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (toDelete) deleteMutation.mutate(toDelete);
        }}
      />
    </div>
  );
}
