import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ConfirmDialog,
  Dialog,
  DialogBody,
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
import { SettingsPageHeader } from "@/features/iam/components/settings-page-header";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { MemberPickerDialog } from "@/features/iam/components/member-picker-dialog";
import { PermissionPicker } from "@/features/iam/components/permission-picker";
import type { PermissionKey, Role } from "@/lib/api/types";

export function RolesPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = principal?.permissions.includes("roles:manage");

  const [open, setOpen] = useState(false);
  // null = creating a new role; a role id = editing that role.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [keys, setKeys] = useState<PermissionKey[]>(["tenant:read"]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Role | null>(null);
  const [assigning, setAssigning] = useState<Role | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);
  const alertRef = useAlertFocus(error !== null);

  const query = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  // Deleting or editing a role changes what the People table shows in its Role
  // column, so both lists are busted together — the same scope groups-page uses.
  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["roles", principal?.tenant_id],
        exact: true,
      }),
      queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      }),
    ]);

  function openCreate() {
    setEditingId(null);
    setName("");
    setDescription("");
    setKeys(["tenant:read"]);
    setError(null);
    setOpen(true);
  }

  function openEdit(role: Role) {
    setEditingId(role.id);
    setName(role.name);
    setDescription(role.description ?? "");
    setKeys([...role.permission_keys]);
    setError(null);
    setOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        name: name.trim(),
        description: description.trim() || null,
        permission_keys: keys,
      };
      return editingId
        ? iamApi.updateRole(editingId, body)
        : iamApi.createRole(body);
    },
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
          : "The role didn't reach the server. Check your connection and try again.",
      );
    },
  });

  // One request per person: the backend is idempotent per assignee, so a bulk
  // endpoint would only be moving this loop across the wire.
  const assignMutation = useMutation({
    mutationFn: async ({ role, added }: { role: Role; added: string[] }) => {
      for (const membershipId of added) {
        await iamApi.assignRoleTo(role.id, membershipId);
      }
      return added.length;
    },
    onSuccess: async (count, { role }) => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({
          queryKey: ["members", principal?.tenant_id],
        }),
      ]);
      setAssigning(null);
      setAssignError(null);
      toast({
        title: `${role.name} assigned to ${count} ${count === 1 ? "person" : "people"}`,
        tone: "success",
      });
    },
    onError: (err: unknown) => {
      setAssignError(
        err instanceof ApiError
          ? err.message
          : "The assignment didn't reach the server. Try again.",
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
            : "Couldn't delete the role. Try again.",
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
      <SettingsPageHeader
        title="Roles & permissions"
        count={{ value: roles.length, noun: "roles" }}
        description="What each role may do. Built-in roles are fixed; custom roles carry the keys you choose."
        action={
          canManage ? (
            <Button onClick={openCreate}>
              <Icon name="plus" className="size-4" />
              New custom role
            </Button>
          ) : null
        }
      />

      {roles.length === 0 ? (
        <EmptyState
          icon="shield"
          title="No roles to show"
          description="Built-in roles should always exist. Retry, or contact support if this persists."
        />
      ) : (
        <Table density="standard">
          <THead>
            <TR>
              <TH>Role</TH>
              <TH>Description</TH>
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
                <TD className="max-w-[24rem]">
                  {role.description ? (
                    <span className="line-clamp-2 text-text-secondary">
                      {role.description}
                    </span>
                  ) : (
                    <span className="text-text-faint">—</span>
                  )}
                </TD>
                <TD numeric>{role.permission_keys.length}</TD>
                <TD numeric>{role.assignment_count}</TD>
                <TD className="text-right">
                  {canManage ? (
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
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(() => {
                              setAssignError(null);
                              setAssigning(role);
                            }, 0)
                          }
                        >
                          Assign to…
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
        <DialogContent size="md" scrollBody>
          <DialogHeader>
            <DialogTitle>
              {editingId ? "Edit role" : "Create custom role"}
            </DialogTitle>
            <DialogDescription>
              {editingId
                ? "Rename this role or change what it can do. Changes apply to everyone who holds it."
                : "Give the role a name, say what it is for, then pick what it can do."}
            </DialogDescription>
          </DialogHeader>
          <form
            className="flex min-h-0 flex-1 flex-col"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) saveMutation.mutate();
            }}
            noValidate
          >
            <DialogBody className="flex flex-col gap-3 pb-1">
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
              <TextField
                label="Description"
                hint="Optional. What this role is for, so whoever assigns it knows."
                placeholder="Reviews control evidence ahead of the audit window."
                maxLength={500}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              {/* min-w-0: a <fieldset> defaults to min-width:min-content, so
                  without it the element refuses to shrink below its longest
                  permission label and spills out of the dialog when narrow. */}
              <fieldset className="min-w-0">
                <legend className="mb-2 font-sans text-label-sm text-text-secondary">
                  Permissions
                </legend>
                <PermissionPicker value={keys} onChange={setKeys} />
              </fieldset>
            </DialogBody>
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

      <MemberPickerDialog
        open={assigning !== null}
        onOpenChange={(next) => {
          if (!next) {
            setAssigning(null);
            setAssignError(null);
          }
        }}
        title={`Assign “${assigning?.name ?? ""}”`}
        description="Pick everyone who should hold this role. People who already hold it are unaffected."
        confirmLabel="Assign role"
        initialSelected={[]}
        saving={assignMutation.isPending}
        error={assignError}
        onConfirm={({ added }) => {
          if (assigning && added.length > 0) {
            assignMutation.mutate({ role: assigning, added });
          }
        }}
      />

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
            {toDelete?.built_in ? (
              <>
                {" "}
                Verity refuses the delete if it would leave the workspace with
                no role that can manage roles.
              </>
            ) : null}
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
