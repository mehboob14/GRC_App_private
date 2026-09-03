import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ColumnPicker,
  type ColumnDef,
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
  useColumnPrefs,
  useToast,
} from "@/components/ui";
import { SettingsPageHeader } from "@/features/iam/components/settings-page-header";
import { iamApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { MemberPickerDialog } from "@/features/iam/components/member-picker-dialog";
import type { Group } from "@/lib/api/types";

/** Optional columns only — Name and the actions cell always render. */
const GROUP_COLUMNS = [
  { key: "description", label: "Description" },
  { key: "members", label: "Members" },
] as const satisfies readonly ColumnDef<string>[];

export function GroupsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = principal?.permissions.includes("groups:manage");

  const [open, setOpen] = useState(false);
  // null = creating a new group; a group id = editing that group.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Group | null>(null);
  const [managing, setManaging] = useState<Group | null>(null);
  const [memberError, setMemberError] = useState<string | null>(null);
  const alertRef = useAlertFocus(error !== null);
  const cols = useColumnPrefs("verity.groups.columns", GROUP_COLUMNS);

  const query = useQuery({
    queryKey: ["groups", principal?.tenant_id],
    queryFn: () => iamApi.listGroups(),
  });

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["groups", principal?.tenant_id],
        exact: true,
      }),
      // Members carry group_names, so the People table is stale after any of this.
      queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
      }),
    ]);

  function openCreate() {
    setEditingId(null);
    setName("");
    setDescription("");
    setError(null);
    setOpen(true);
  }

  function openEdit(group: Group) {
    setEditingId(group.id);
    setName(group.name);
    setDescription(group.description ?? "");
    setError(null);
    setOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        name: name.trim(),
        description: description.trim() || null,
      };
      return editingId
        ? iamApi.updateGroup(editingId, body)
        : iamApi.createGroup(body);
    },
    onSuccess: async () => {
      await invalidate();
      setOpen(false);
      toast({
        title: editingId ? "Group updated" : "Group created",
        tone: "success",
      });
    },
    onError: (err: unknown) => {
      setError(errorToast(err, "group"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (group: Group) => iamApi.deleteGroup(group.id),
    onSuccess: async (_data, group) => {
      await invalidate();
      setToDelete(null);
      toast({ title: `Deleted group “${group.name}”`, tone: "neutral" });
    },
    onError: (err: unknown) => {
      setToDelete(null);
      toast({ title: errorToast(err, "group"), tone: "danger" });
    },
  });

  // One request per person added or removed — the endpoints are per-member and
  // each one is its own audit row, which is what an access review wants to read.
  const membersMutation = useMutation({
    mutationFn: async ({
      group,
      added,
      removed,
    }: {
      group: Group;
      added: string[];
      removed: string[];
    }) => {
      for (const membershipId of added) {
        await iamApi.addGroupMember(group.id, membershipId);
      }
      for (const membershipId of removed) {
        await iamApi.removeGroupMember(group.id, membershipId);
      }
      return added.length + removed.length;
    },
    onSuccess: async (count, { group }) => {
      await invalidate();
      setManaging(null);
      setMemberError(null);
      toast({
        title: `Updated ${count} ${
          count === 1 ? "membership" : "memberships"
        } in ${group.name}`,
        tone: "success",
      });
    },
    onError: (err: unknown) => {
      setMemberError(errorToast(err, "group membership"));
    },
  });

  if (query.isLoading) {
    return <TableSkeleton rows={4} density="standard" />;
  }

  if (query.isError) {
    const failure = describeError(query.error, "group list");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const groups = query.data ?? [];

  return (
    <div>
      <SettingsPageHeader
        title="Groups"
        count={{ value: groups.length, noun: "groups" }}
        description="The join between IdP group, Verity role, and access-review scope."
        action={
          canManage ? (
            <Button onClick={openCreate}>
              <Icon name="plus" className="size-4" />
              New group
            </Button>
          ) : null
        }
      />

      {groups.length === 0 ? (
        <EmptyState
          icon="users"
          title="No groups yet"
          description="Create a group to assign people together. Reviews and role changes then move group-by-group."
        />
      ) : (
        <Table density="standard" actions={<ColumnPicker {...cols} />}>
          <THead>
            <TR>
              <TH>Name</TH>
              {cols.isVisible("description") ? <TH>Description</TH> : null}
              {cols.isVisible("members") ? <TH numeric>Members</TH> : null}
              <TH>
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {groups.map((group) => (
              <TR key={group.id}>
                <TD className="font-semibold">{group.name}</TD>
                {cols.isVisible("description") ? (
                  <TD className="max-w-[24rem]">
                    {group.description ? (
                      <span className="line-clamp-2 text-text-secondary">
                        {group.description}
                      </span>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </TD>
                ) : null}
                {cols.isVisible("members") ? (
                  <TD numeric>{group.member_count}</TD>
                ) : null}
                <TD className="text-right">
                  {canManage ? (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Actions for ${group.name}`}
                        >
                          <Icon name="more" className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(() => openEdit(group), 0)
                          }
                        >
                          Edit group
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(() => {
                              setMemberError(null);
                              setManaging(group);
                            }, 0)
                          }
                        >
                          Manage members
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          variant="danger"
                          onSelect={() =>
                            window.setTimeout(() => setToDelete(group), 0)
                          }
                        >
                          Delete group
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
              {editingId ? "Edit group" : "Create group"}
            </DialogTitle>
            <DialogDescription>
              {editingId
                ? "Rename this group or change what it is for. Members are managed separately."
                : "Name the group, then add people to it from the actions menu."}
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
                <ErrorBanner ref={alertRef} title="Couldn't save the group">
                  {error}
                </ErrorBanner>
              ) : null}
              <TextField
                label="Group name"
                placeholder="Engineering"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <TextField
                label="Description"
                hint="Optional. What this group is for, so access reviews read cleanly."
                placeholder="Engineers who own technical controls and their evidence."
                maxLength={500}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
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
                {editingId ? "Save changes" : "Create group"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <MemberPickerDialog
        open={managing !== null}
        onOpenChange={(next) => {
          if (!next) {
            setManaging(null);
            setMemberError(null);
          }
        }}
        title={`Members of “${managing?.name ?? ""}”`}
        description="Tick everyone who belongs to this group. Unticking removes them from the group only. Their roles are untouched."
        confirmLabel="Save members"
        initialSelected={managing?.member_ids ?? []}
        saving={membersMutation.isPending}
        error={memberError}
        onConfirm={({ added, removed }) => {
          if (managing) {
            membersMutation.mutate({ group: managing, added, removed });
          }
        }}
      />

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(next) => {
          if (!next) setToDelete(null);
        }}
        title={`Delete group “${toDelete?.name ?? ""}”?`}
        consequence={
          <>
            This removes the group and any role assigned <em>to the group</em>.
            {toDelete?.member_count === 1
              ? " Its 1 member keeps every role they hold directly."
              : ` Its ${toDelete?.member_count ?? 0} members keep every role they hold directly.`}{" "}
            This can’t be undone.
          </>
        }
        confirmLabel="Delete group"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (toDelete) deleteMutation.mutate(toDelete);
        }}
      />
    </div>
  );
}
