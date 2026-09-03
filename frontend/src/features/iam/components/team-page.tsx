import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Avatar,
  Badge,
  Button,
  ColumnPicker,
  type ColumnDef,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorBanner,
  ErrorState,
  Icon,
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  statusFamilyFor,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TextField,
  TH,
  THead,
  TR,
  useColumnPrefs,
  useToast,
} from "@/components/ui";
import { SettingsPageHeader } from "@/features/iam/components/settings-page-header";
import { iamApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type {
  InviteMemberRequest,
  InviteMemberResponse,
  Member,
} from "@/lib/api/types";

function formatDate(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
      new Date(`${iso}T00:00:00`),
    );
  } catch {
    return iso;
  }
}

/** "3 hours ago" / "98 days ago" / "Never" — native, locale-aware. */
function timeAgo(iso: string | null): string {
  if (!iso) return "Never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diffMs = then - Date.now();
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000_000],
    ["month", 2_592_000_000],
    ["day", 86_400_000],
    ["hour", 3_600_000],
    ["minute", 60_000],
  ];
  for (const [unit, ms] of units) {
    if (Math.abs(diffMs) >= ms)
      return rtf.format(Math.round(diffMs / ms), unit);
  }
  return "just now";
}

/** Radix Select forbids an empty string as an item value, so "no group" needs
 *  a sentinel that is mapped back to "" before it reaches the request. */
const NO_GROUP = "__none__";

/** Optional columns only — Member and the actions cell always render. */
const TEAM_COLUMNS = [
  { key: "role", label: "Role" },
  { key: "groups", label: "Groups" },
  { key: "mfa", label: "MFA" },
  { key: "background", label: "Background" },
  { key: "documents", label: "Documents" },
  { key: "lastActive", label: "Last active" },
] as const satisfies readonly ColumnDef<string>[];

const inviteSchema = z
  .object({
    full_name: z.string().min(2, "Enter a name."),
    email: z.string().email("Enter a work email."),
    invite_as: z.enum(["member", "guest"]),
    role_id: z.string(),
    group_id: z.string(),
    valid_from: z.string(),
    valid_until: z.string(),
  })
  .superRefine((values, ctx) => {
    if (
      values.invite_as === "guest" &&
      values.valid_from &&
      values.valid_until &&
      values.valid_until <= values.valid_from
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["valid_until"],
        message: `Access must end after ${formatDate(values.valid_from)}.`,
      });
    }
  });

type InviteValues = z.infer<typeof inviteSchema>;

const INVITE_DEFAULTS: InviteValues = {
  full_name: "",
  email: "",
  invite_as: "member",
  // No hard-coded role id: the built-in "Employee" role is resolved by name
  // from the roles query once it loads (see TeamPage). A literal like
  // "role-employee" is not a valid UUID and matches no option → 422.
  role_id: "",
  // "" means no group — the Select renders it as the "No group" option.
  group_id: "",
  valid_from: "",
  valid_until: "",
};

/** Roles are a taxonomy, not a status — neutral chips, accent for Admin. */
function roleBadgeVariant(role: string) {
  return role === "Admin" ? ("role" as const) : ("neutral" as const);
}

function MemberStatusPill({ status }: { status: Member["status"] }) {
  if (status === "active") return null;
  const label = status === "invited" ? "Invited" : "Disabled";
  return (
    <StatusPill
      status={statusFamilyFor(label) ?? "unknown"}
      label={label}
      kind="pill"
    />
  );
}

export function TeamPage() {
  const { principal, refreshPrincipal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteResult, setInviteResult] = useState<InviteMemberResponse | null>(
    null,
  );
  const [copyFailed, setCopyFailed] = useState(false);
  const [toDisable, setToDisable] = useState<Member | null>(null);
  const [roleEdit, setRoleEdit] = useState<Member | null>(null);
  const [renaming, setRenaming] = useState<Member | null>(null);
  const [nameDraft, setNameDraft] = useState("");
  const [roleChoice, setRoleChoice] = useState("");
  const [groupAdd, setGroupAdd] = useState<Member | null>(null);
  const [groupChoice, setGroupChoice] = useState("");
  const inviteAlertRef = useAlertFocus(inviteError !== null);
  const cols = useColumnPrefs("verity.team.columns", TEAM_COLUMNS);

  const membersQuery = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
  });
  const rolesQuery = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const groupsQuery = useQuery({
    queryKey: ["groups", principal?.tenant_id],
    queryFn: () => iamApi.listGroups(),
    // Adding to a group is the only reason this page reads groups; skip the
    // request (and its 403) for anyone who can't manage them.
    enabled: Boolean(principal?.permissions.includes("groups:manage")),
  });

  const roles = rolesQuery.data ?? [];
  const groups = groupsQuery.data ?? [];
  // The built-in set is the client's own list of appointments now, so there is
  // no "Employee" default and no dedicated "Auditor" to pin guests to. Fall
  // back to the least-privileged option available rather than a magic name:
  // any name we hard-coded here would break the next time the set changes.
  const defaultRole = roles.find((role) => role.name !== "Admin") ?? roles[0];

  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: INVITE_DEFAULTS,
    mode: "onBlur",
  });
  const inviteAs = form.watch("invite_as");
  const memberRoleId = form.watch("role_id");

  // Preselect a sensible default once roles load. If none resolves the field
  // stays unset and the submit is disabled until a role is chosen.
  useEffect(() => {
    if (open && !memberRoleId && defaultRole) {
      form.setValue("role_id", defaultRole.id);
    }
  }, [open, memberRoleId, defaultRole, form]);

  // The role actually submitted: guests always get Auditor, members the picked
  // role. Always a real role UUID from the roles query — never a literal.
  const submitRoleId = memberRoleId;
  const canSubmitInvite = Boolean(submitRoleId);

  const inviteMutation = useMutation({
    mutationFn: (body: InviteMemberRequest) => iamApi.inviteMember(body),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
      // Keep the dialog open: the accept link is returned exactly once and
      // the inviter must hand it over (no email delivery until notifications).
      setInviteResult(result);
      form.reset(INVITE_DEFAULTS);
      setInviteError(null);
    },
    onError: (error: unknown) => {
      setInviteError(errorToast(error, "invitation"));
    },
  });

  function submitInvite(values: InviteValues) {
    const guest = values.invite_as === "guest";
    const roleId = values.role_id;
    if (!roleId) {
      setInviteError(
        "Choose a role for this member before sending the invite.",
      );
      return;
    }
    const body: InviteMemberRequest = {
      full_name: values.full_name,
      email: values.email,
      role_id: roleId,
    };
    if (values.group_id) body.group_id = values.group_id;
    if (guest && values.valid_from) body.valid_from = values.valid_from;
    if (guest && values.valid_until) body.valid_until = values.valid_until;
    inviteMutation.mutate(body);
  }

  function handleDialogChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setInviteResult(null);
      setInviteError(null);
      setCopyFailed(false);
      form.reset(INVITE_DEFAULTS);
    }
  }

  async function copyAcceptLink() {
    if (!inviteResult) return;
    try {
      await navigator.clipboard.writeText(inviteResult.accept_url);
      setCopyFailed(false);
      toast({ title: "Accept link copied", tone: "success" });
    } catch {
      setCopyFailed(true);
    }
  }

  const disableMutation = useMutation({
    mutationFn: (member: Member) => iamApi.disableMember(member.membership_id),
    onSuccess: async (_, member) => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
      setToDisable(null);
      toast({
        title: `Disabled ${member.full_name}'s membership`,
        tone: "neutral",
      });
    },
    onError: (error: unknown) => {
      setToDisable(null);
      toast({ title: errorToast(error, "membership"), tone: "danger" });
    },
  });

  const members = useMemo(() => membersQuery.data ?? [], [membersQuery.data]);
  const canInvite = principal?.permissions.includes("members:invite");
  const canDisable = principal?.permissions.includes("members:disable");
  const canEditMember = principal?.permissions.includes("members:manage");
  const canManageRoles = principal?.permissions.includes("roles:manage");
  const canManageGroups = principal?.permissions.includes("groups:manage");

  const renameMutation = useMutation({
    mutationFn: (vars: { membershipId: string; fullName: string }) =>
      iamApi.renameMember(vars.membershipId, vars.fullName),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
      setRenaming(null);
      // Renaming yourself changes the name in your own topbar; the principal
      // cache holds the copy that is displayed.
      void refreshPrincipal();
      toast({ title: "Name updated", tone: "success" });
    },
    onError: (error: unknown) => {
      toast({ title: errorToast(error, "member"), tone: "danger" });
    },
  });

  const roleMutation = useMutation({
    mutationFn: (vars: { membershipId: string; roleId: string }) =>
      iamApi.assignRole(vars.membershipId, vars.roleId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
      setRoleEdit(null);
      toast({ title: "Role updated", tone: "success" });
    },
    onError: (error: unknown) => {
      toast({ title: errorToast(error, "role"), tone: "danger" });
    },
  });

  const groupMutation = useMutation({
    mutationFn: (vars: { groupId: string; membershipId: string }) =>
      iamApi.addGroupMember(vars.groupId, vars.membershipId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["members", principal?.tenant_id],
          exact: true,
        }),
        queryClient.invalidateQueries({
          queryKey: ["groups", principal?.tenant_id],
          exact: true,
        }),
      ]);
      setGroupAdd(null);
      toast({ title: "Added to group", tone: "success" });
    },
    onError: (error: unknown) => {
      toast({ title: errorToast(error, "group membership"), tone: "danger" });
    },
  });

  // Groups this member isn't in yet — add is idempotent, but offering a group
  // they already hold is just noise.
  const availableGroups = groupAdd
    ? groups.filter((group) => !groupAdd.group_names.includes(group.name))
    : [];

  function openRename(member: Member) {
    setNameDraft(member.full_name);
    setRenaming(member);
  }

  function openRoleEdit(member: Member) {
    const current = roles.find((role) => member.role_names.includes(role.name));
    setRoleChoice(current?.id ?? "");
    setRoleEdit(member);
  }

  function openGroupAdd(member: Member) {
    setGroupChoice("");
    setGroupAdd(member);
  }

  if (membersQuery.isLoading) {
    return <TableSkeleton rows={4} density="comfortable" />;
  }

  if (membersQuery.isError) {
    const failure = describeError(membersQuery.error, "team list");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void membersQuery.refetch() : undefined}
      />
    );
  }

  return (
    <div>
      <SettingsPageHeader
        title="People"
        count={{ value: members.length, noun: "members" }}
        description="Everyone with access to this workspace, and what they can do."
        action={
          canInvite ? (
            <Dialog open={open} onOpenChange={handleDialogChange}>
              <DialogTrigger asChild>
                <Button className="shrink-0">
                  <Icon name="plus" className="size-4" />
                  Invite member
                </Button>
              </DialogTrigger>
              <DialogContent size="md">
                {inviteResult ? (
                  <>
                    <DialogHeader>
                      <DialogTitle>Invite created</DialogTitle>
                      {/* Only claim delivery the server actually reports. */}
                      <DialogDescription>
                        {inviteResult.email_sent ? (
                          <>
                            Sent to{" "}
                            <span className="font-semibold text-text-primary">
                              {inviteResult.member.email}
                            </span>
                            .
                          </>
                        ) : (
                          <>
                            Email is not configured, so nothing was sent.
                            Share this link with{" "}
                            <span className="font-semibold text-text-primary">
                              {inviteResult.member.email}
                            </span>
                            .
                          </>
                        )}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="rounded-md border border-border bg-surface-sunken px-3 py-3">
                      <div className="flex items-center gap-2">
                        <input
                          readOnly
                          aria-label="Invite accept link"
                          value={inviteResult.accept_url}
                          onFocus={(e) => e.currentTarget.select()}
                          className="h-9 min-w-0 flex-1 rounded-sm border border-border bg-surface-primary px-3 font-mono text-body-sm text-text-primary"
                        />
                        {/* One primary per region: copying the link IS the task. */}
                        <Button
                          type="button"
                          className="shrink-0"
                          onClick={() => void copyAcceptLink()}
                        >
                          Copy link
                        </Button>
                      </div>
                      {copyFailed ? (
                        <p
                          className="mt-2 text-body-sm text-status-danger-text"
                          role="alert"
                        >
                          Copy failed. Select the link text and copy it
                          manually.
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-2.5 text-caption text-text-subtle">
                      Works once · expires in 7 days
                    </p>
                    <DialogFooter>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => handleDialogChange(false)}
                      >
                        Done
                      </Button>
                    </DialogFooter>
                  </>
                ) : (
                  <>
                    <DialogHeader>
                      <DialogTitle>Invite member</DialogTitle>
                      <DialogDescription>
                        They get a one-time accept link by email.
                      </DialogDescription>
                    </DialogHeader>
                    <form
                      className="flex flex-col gap-3"
                      onSubmit={(e) =>
                        void form.handleSubmit(submitInvite)(e)
                      }
                    >
                      {inviteError ? (
                        <ErrorBanner
                          ref={inviteAlertRef}
                          title="Couldn't create the invite"
                        >
                          {inviteError}
                        </ErrorBanner>
                      ) : null}
                      <TextField
                        label="Full name"
                        error={form.formState.errors.full_name?.message}
                        {...form.register("full_name")}
                      />
                      <TextField
                        label="Work email"
                        type="email"
                        error={form.formState.errors.email?.message}
                        {...form.register("email")}
                      />
                      <fieldset>
                        <legend className="mb-1.5 font-sans text-label-sm text-text-secondary">
                          Invite as
                        </legend>
                        <RadioGroup
                          value={inviteAs}
                          onValueChange={(value) =>
                            form.setValue(
                              "invite_as",
                              value === "guest" ? "guest" : "member",
                              { shouldValidate: true },
                            )
                          }
                        >
                          <RadioGroupItem value="member" label="Member" />
                          <RadioGroupItem
                            value="guest"
                            label="Guest auditor"
                          />
                        </RadioGroup>
                      </fieldset>
                      {inviteAs === "guest" ? (
                        <>
                          <div className="grid grid-cols-2 gap-3">
                            <TextField
                              label="Access starts"
                              type="date"
                              optional
                              error={
                                form.formState.errors.valid_from?.message
                              }
                              {...form.register("valid_from")}
                            />
                            <TextField
                              label="Access ends"
                              type="date"
                              optional
                              error={
                                form.formState.errors.valid_until?.message
                              }
                              {...form.register("valid_until")}
                            />
                          </div>
                        </>
                      ) : (
                        <SelectField label="Role">
                          <Select
                            value={memberRoleId}
                            onValueChange={(value) =>
                              form.setValue("role_id", value, {
                                shouldValidate: true,
                              })
                            }
                          >
                            <SelectTrigger aria-label="Role" />
                            <SelectContent>
                              {roles.map((role) => (
                                <SelectItem key={role.id} value={role.id}>
                                  {role.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {/* An empty role list is not "no roles exist". */}
                          {rolesQuery.isError ? (
                            <p className="mt-1 text-body-sm text-status-danger-text">
                              {describeError(rolesQuery.error, "role list").message}
                            </p>
                          ) : null}
                        </SelectField>
                      )}
                      {groups.length > 0 ? (
                        <SelectField label="Group" optional>
                          <Select
                            value={form.watch("group_id")}
                            onValueChange={(value) =>
                              form.setValue(
                                "group_id",
                                value === NO_GROUP ? "" : value,
                              )
                            }
                          >
                            <SelectTrigger aria-label="Group" />
                            <SelectContent>
                              <SelectItem value={NO_GROUP}>
                                No group
                              </SelectItem>
                              {groups.map((group) => (
                                <SelectItem key={group.id} value={group.id}>
                                  {group.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </SelectField>
                      ) : null}
                      <DialogFooter>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => handleDialogChange(false)}
                        >
                          Cancel
                        </Button>
                        <Button
                          type="submit"
                          loading={inviteMutation.isPending}
                          disabled={!canSubmitInvite}
                        >
                          Create invite
                        </Button>
                      </DialogFooter>
                    </form>
                  </>
                )}
              </DialogContent>
            </Dialog>
          ) : null
        }
      />

      {members.length === 0 ? (
        <EmptyState
          icon="users"
          title="No members yet"
          description="Invite someone to this workspace."
        />
      ) : (
        <Table actions={<ColumnPicker {...cols} />}>
          <THead>
            <TR>
              <TH>Member</TH>
              {cols.isVisible("role") ? <TH>Role</TH> : null}
              {cols.isVisible("groups") ? <TH>Groups</TH> : null}
              {cols.isVisible("mfa") ? <TH>MFA</TH> : null}
              {cols.isVisible("background") ? <TH>Background</TH> : null}
              {cols.isVisible("documents") ? <TH>Documents</TH> : null}
              {cols.isVisible("lastActive") ? <TH>Last active</TH> : null}
              <TH>
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {members.map((member: Member) => {
              const isSelf = member.membership_id === principal?.membership_id;
              const active = member.status !== "disabled";
              const canChangeRole = canManageRoles && active && !isSelf;
              const canAddToGroup = canManageGroups && active;
              const canDisableMember = canDisable && active && !isSelf;
              const canRename = Boolean(canEditMember) && active;
              const hasActions =
                canRename || canChangeRole || canAddToGroup || canDisableMember;
              return (
                <TR key={member.membership_id}>
                  <TD>
                    <div className="flex items-center gap-3">
                      <Avatar name={member.full_name} seed={member.email} />
                      <div className="min-w-0">
                        <p className="flex items-center gap-2 text-body-md font-semibold text-text-primary">
                          {member.full_name}
                          <MemberStatusPill status={member.status} />
                        </p>
                        <p className="truncate text-body-sm text-text-subtle">
                          {member.email}
                        </p>
                      </div>
                    </div>
                  </TD>
                  {cols.isVisible("role") ? (
                    <TD>
                      <div className="flex flex-wrap gap-1">
                        {member.role_names.map((role) => (
                          <Badge key={role} variant={roleBadgeVariant(role)}>
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </TD>
                  ) : null}
                  {cols.isVisible("groups") ? (
                    <TD>
                      <span className="text-body-md text-text-secondary">
                        {member.group_names.length
                          ? member.group_names.join(" · ")
                          : "—"}
                      </span>
                    </TD>
                  ) : null}
                  {cols.isVisible("mfa") ? (
                    <TD>
                      <StatusPill
                        kind="inline"
                        status={member.mfa_enabled ? "success" : "warning"}
                        label={member.mfa_enabled ? "Enabled" : "No MFA"}
                      />
                    </TD>
                  ) : null}
                  {/* Background checks & document acknowledgement aren't tracked
                        yet (no module) — honest "Unknown", never a fabricated pass. */}
                  {cols.isVisible("background") ? (
                    <TD>
                      <StatusPill
                        kind="inline"
                        status="unknown"
                        label="Unknown"
                      />
                    </TD>
                  ) : null}
                  {cols.isVisible("documents") ? (
                    <TD>
                      <StatusPill
                        kind="inline"
                        status="unknown"
                        label="Unknown"
                      />
                    </TD>
                  ) : null}
                  {cols.isVisible("lastActive") ? (
                    <TD>
                      <span className="text-body-md text-text-secondary">
                        {timeAgo(member.last_login_at)}
                      </span>
                    </TD>
                  ) : null}
                  <TD className="text-right">
                    {hasActions ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Actions for ${member.full_name}`}
                          >
                            <Icon name="more" className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {canRename ? (
                            <DropdownMenuItem
                              onSelect={() =>
                                window.setTimeout(() => openRename(member), 0)
                              }
                            >
                              Edit name
                            </DropdownMenuItem>
                          ) : null}
                          {canChangeRole ? (
                            <DropdownMenuItem
                              onSelect={() =>
                                window.setTimeout(() => openRoleEdit(member), 0)
                              }
                            >
                              Change role
                            </DropdownMenuItem>
                          ) : null}
                          {canAddToGroup ? (
                            <DropdownMenuItem
                              onSelect={() =>
                                window.setTimeout(() => openGroupAdd(member), 0)
                              }
                            >
                              Add to group
                            </DropdownMenuItem>
                          ) : null}
                          {canDisableMember ? (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                variant="danger"
                                onSelect={() =>
                                  window.setTimeout(
                                    () => setToDisable(member),
                                    0,
                                  )
                                }
                              >
                                Disable member
                              </DropdownMenuItem>
                            </>
                          ) : null}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : null}
                  </TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      )}

      {/* Rename. The name is the person's, not the membership's, so the copy
          says plainly that it changes everywhere they work. */}
      <Dialog
        open={renaming !== null}
        onOpenChange={(next) => {
          if (!next) setRenaming(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit name</DialogTitle>
            <DialogDescription>
              {renaming?.email} · this is the person&rsquo;s name across every
              workspace they belong to.
            </DialogDescription>
          </DialogHeader>
          <TextField
            label="Full name"
            value={nameDraft}
            onChange={(event) => setNameDraft(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                nameDraft.trim() &&
                renaming &&
                !renameMutation.isPending
              ) {
                renameMutation.mutate({
                  membershipId: renaming.membership_id,
                  fullName: nameDraft.trim(),
                });
              }
            }}
            placeholder="Riya Mehta"
            autoFocus
          />
          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setRenaming(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              loading={renameMutation.isPending}
              disabled={
                !nameDraft.trim() || nameDraft.trim() === renaming?.full_name
              }
              onClick={() => {
                if (renaming && nameDraft.trim()) {
                  renameMutation.mutate({
                    membershipId: renaming.membership_id,
                    fullName: nameDraft.trim(),
                  });
                }
              }}
            >
              Save name
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DS §7.3 destructive confirm — names the member and the consequence. */}
      <ConfirmDialog
        open={toDisable !== null}
        onOpenChange={(next) => {
          if (!next) setToDisable(null);
        }}
        title={`Disable ${toDisable?.full_name ?? "this member"}'s membership?`}
        consequence={
          <>
            {toDisable?.full_name} ({toDisable?.email}) immediately loses access
            to {principal?.tenant_name ?? "this workspace"}. Their history stays
            in the audit trail, and you can invite them again later.
          </>
        }
        confirmLabel="Disable membership"
        loading={disableMutation.isPending}
        onConfirm={() => {
          if (toDisable) disableMutation.mutate(toDisable);
        }}
      />

      {/* Change a member's single direct role (roles:manage). */}
      <Dialog
        open={roleEdit !== null}
        onOpenChange={(next) => {
          if (!next) setRoleEdit(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change role</DialogTitle>
            <DialogDescription>
              {roleEdit?.full_name}&rsquo;s access is set by their role.
              Replacing it takes effect immediately.
            </DialogDescription>
          </DialogHeader>
          <SelectField label="Role">
            <Select value={roleChoice} onValueChange={setRoleChoice}>
              <SelectTrigger aria-label="Role" />
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {rolesQuery.isError ? (
              <p className="mt-1 text-body-sm text-status-danger-text">
                {describeError(rolesQuery.error, "role list").message}
              </p>
            ) : null}
          </SelectField>
          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setRoleEdit(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              loading={roleMutation.isPending}
              disabled={!roleChoice}
              onClick={() => {
                if (roleEdit && roleChoice)
                  roleMutation.mutate({
                    membershipId: roleEdit.membership_id,
                    roleId: roleChoice,
                  });
              }}
            >
              Save role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add a member to a group (groups:manage). Add-only — no remove yet. */}
      <Dialog
        open={groupAdd !== null}
        onOpenChange={(next) => {
          if (!next) setGroupAdd(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to group</DialogTitle>
            <DialogDescription>
              Add {groupAdd?.full_name} to a group. Groups scope access reviews
              and role changes.
            </DialogDescription>
          </DialogHeader>
          {availableGroups.length === 0 ? (
            <p className="text-body-sm text-text-subtle">
              {groups.length === 0
                ? "No groups yet. Create one in Settings → Groups first."
                : `${groupAdd?.full_name ?? "This member"} is already in every group.`}
            </p>
          ) : (
            <SelectField label="Group">
              <Select value={groupChoice} onValueChange={setGroupChoice}>
                <SelectTrigger aria-label="Group" />
                <SelectContent>
                  {availableGroups.map((group) => (
                    <SelectItem key={group.id} value={group.id}>
                      {group.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setGroupAdd(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              loading={groupMutation.isPending}
              disabled={!groupChoice}
              onClick={() => {
                if (groupAdd && groupChoice)
                  groupMutation.mutate({
                    groupId: groupChoice,
                    membershipId: groupAdd.membership_id,
                  });
              }}
            >
              Add to group
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
