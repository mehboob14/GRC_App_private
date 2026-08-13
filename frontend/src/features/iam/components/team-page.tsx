import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Avatar,
  Badge,
  Button,
  ConfirmDialog,
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
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
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
  useToast,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
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

const inviteSchema = z
  .object({
    full_name: z.string().min(2, "Enter a name."),
    email: z.string().email("Enter a work email."),
    invite_as: z.enum(["member", "guest"]),
    role_id: z.string(),
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
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteResult, setInviteResult] = useState<InviteMemberResponse | null>(
    null,
  );
  const [copyFailed, setCopyFailed] = useState(false);
  const [toDisable, setToDisable] = useState<Member | null>(null);
  const inviteAlertRef = useAlertFocus(inviteError !== null);

  const membersQuery = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
  });
  const rolesQuery = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const roles = rolesQuery.data ?? [];
  const auditorRole = roles.find((role) => role.name === "Auditor");
  const employeeRole = roles.find((role) => role.name === "Employee");

  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: INVITE_DEFAULTS,
    mode: "onBlur",
  });
  const inviteAs = form.watch("invite_as");
  const memberRoleId = form.watch("role_id");

  // Preselect the tenant's built-in "Employee" role once roles load, resolved
  // by name rather than a hard-coded id. If it can't be resolved the field
  // stays unset and the submit is disabled until a role is chosen.
  useEffect(() => {
    if (open && inviteAs === "member" && !memberRoleId && employeeRole) {
      form.setValue("role_id", employeeRole.id);
    }
  }, [open, inviteAs, memberRoleId, employeeRole, form]);

  // The role actually submitted: guests always get Auditor, members the picked
  // role. Always a real role UUID from the roles query — never a literal.
  const submitRoleId = inviteAs === "guest" ? auditorRole?.id : memberRoleId;
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
      setInviteError(
        error instanceof ApiError
          ? error.message
          : "The invite didn't reach the server — check your connection and try again.",
      );
    },
  });

  function submitInvite(values: InviteValues) {
    const guest = values.invite_as === "guest";
    const roleId = guest ? auditorRole?.id : values.role_id;
    if (!roleId) {
      setInviteError(
        guest
          ? "The Auditor role isn't available in this workspace yet — ask an admin to add it, then try again."
          : "Choose a role for this member before sending the invite.",
      );
      return;
    }
    const body: InviteMemberRequest = {
      full_name: values.full_name,
      email: values.email,
      role_id: roleId,
    };
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
      toast({
        title:
          error instanceof ApiError
            ? error.message
            : "Couldn't disable the membership — try again.",
        tone: "danger",
      });
    },
  });

  const members = useMemo(() => membersQuery.data ?? [], [membersQuery.data]);
  const canInvite = principal?.permissions.includes("members:invite");
  const canDisable = principal?.permissions.includes("members:disable");

  if (membersQuery.isLoading) {
    // Bones mirror the real layout: title, description, member table.
    return (
      <div className="mx-auto max-w-[1200px]">
        <Skeleton className="h-[30px] w-40" />
        <Skeleton className="mb-5 mt-3 h-4 w-96 max-w-full" />
        <TableSkeleton rows={4} density="comfortable" />
      </div>
    );
  }

  if (membersQuery.isError) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <ErrorState
          title="Couldn’t load team"
          description={
            membersQuery.error instanceof ApiError
              ? membersQuery.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          referenceId={
            membersQuery.error instanceof ApiError
              ? membersQuery.error.correlationId
              : undefined
          }
          onRetry={() => void membersQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-heading-lg text-text-primary">People</h1>
      <p className="mb-5 mt-2 text-body-lg text-text-secondary">
        Everyone with a membership in this workspace — role, teams, and MFA
        state.
      </p>
      <div className="rounded-lg border border-border bg-surface-primary px-5 py-4">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-title-md text-text-primary">
              Team &amp; roles
            </h2>
            <p className="mt-1 text-body-sm text-text-subtle">
              <span className="tabular">{members.length}</span> members ·
              manage access to the Verity workspace
            </p>
          </div>
          {canInvite ? (
            <Dialog open={open} onOpenChange={handleDialogChange}>
              <DialogTrigger asChild>
                <Button className="shrink-0">
                  <Icon name="plus" className="size-4" />
                  Invite member
                </Button>
              </DialogTrigger>
              <DialogContent>
                {inviteResult ? (
                  <>
                    <DialogHeader>
                      <DialogTitle>Invite created</DialogTitle>
                      <DialogDescription>
                        {inviteResult.member.full_name} can join this workspace
                        with the one-time link below.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="rounded-md border border-border bg-surface-sunken px-3 py-3">
                      <p className="type-overline text-text-subtle">
                        One-time accept link
                      </p>
                      <div className="mt-1.5 flex items-center gap-2">
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
                          Copy failed — select the link text and copy it
                          manually.
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-3 text-body-sm text-text-subtle">
                      Email delivery arrives with the notifications module —
                      hand this link to the invitee yourself. It works once and
                      expires in 7 days.
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
                        Creates an invited membership and a one-time accept
                        link to hand over.
                      </DialogDescription>
                    </DialogHeader>
                    <form
                      className="flex flex-col gap-3"
                      onSubmit={(e) => void form.handleSubmit(submitInvite)(e)}
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
                          <RadioGroupItem
                            value="member"
                            label="Member"
                            description="A teammate in your organisation, with a role you pick."
                          />
                          <RadioGroupItem
                            value="guest"
                            label="Guest auditor"
                            description="An external auditor or consultant — read-only Auditor role, optionally time-boxed."
                          />
                        </RadioGroup>
                      </fieldset>
                      {inviteAs === "guest" ? (
                        <>
                          <SelectField label="Role">
                            <Select value={auditorRole?.id ?? ""} disabled>
                              <SelectTrigger aria-label="Role (fixed to Auditor for guests)" />
                              <SelectContent>
                                {auditorRole ? (
                                  <SelectItem value={auditorRole.id}>
                                    {auditorRole.name}
                                  </SelectItem>
                                ) : null}
                              </SelectContent>
                            </Select>
                          </SelectField>
                          <div className="grid grid-cols-2 gap-3">
                            <TextField
                              label="Access starts"
                              type="date"
                              optional
                              error={form.formState.errors.valid_from?.message}
                              {...form.register("valid_from")}
                            />
                            <TextField
                              label="Access ends"
                              type="date"
                              optional
                              error={form.formState.errors.valid_until?.message}
                              {...form.register("valid_until")}
                            />
                          </div>
                          <p className="text-body-sm text-text-subtle">
                            Time-boxes access for external auditors and
                            consultants — for example an engagement window.
                            Leave empty for open-ended access.
                          </p>
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
                              {roles
                                .filter((role) => role.name !== "Auditor")
                                .map((role) => (
                                  <SelectItem key={role.id} value={role.id}>
                                    {role.name}
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
          ) : null}
        </div>

        {members.length === 0 ? (
          <EmptyState
            icon="users"
            title="No members yet"
            description="Invite someone to this workspace."
          />
        ) : (
          <Table className="rounded-none border-0 bg-transparent">
            <THead>
              <TR>
                <TH>Member</TH>
                <TH>Role</TH>
                <TH>Teams</TH>
                <TH>MFA</TH>
                <TH>
                  <span className="sr-only">Actions</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {members.map((member: Member) => (
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
                  <TD>
                    <div className="flex flex-wrap gap-1">
                      {member.role_names.map((role) => (
                        <Badge key={role} variant={roleBadgeVariant(role)}>
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </TD>
                  <TD>
                    <span className="text-body-md text-text-secondary">
                      {member.group_names.length
                        ? member.group_names.join(" · ")
                        : "—"}
                    </span>
                  </TD>
                  <TD>
                    <StatusPill
                      kind="inline"
                      status={
                        statusFamilyFor(
                          member.mfa_enabled ? "Enrolled" : "Not enrolled",
                        ) ?? "unknown"
                      }
                      label={member.mfa_enabled ? "Enrolled" : "Not enrolled"}
                    />
                  </TD>
                  <TD className="text-right">
                    {canDisable &&
                    member.status !== "disabled" &&
                    member.membership_id !== principal?.membership_id ? (
                      <Button
                        variant="destructive-2"
                        size="sm"
                        onClick={() => setToDisable(member)}
                      >
                        Disable
                      </Button>
                    ) : null}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </div>

      {/* DS §7.3 destructive confirm — names the member and the consequence. */}
      <ConfirmDialog
        open={toDisable !== null}
        onOpenChange={(next) => {
          if (!next) setToDisable(null);
        }}
        title={`Disable ${toDisable?.full_name ?? "this member"}'s membership?`}
        consequence={
          <>
            {toDisable?.full_name} ({toDisable?.email}) immediately loses
            access to {principal?.tenant_name ?? "this workspace"}. Their
            history stays in the audit trail, and you can invite them again
            later.
          </>
        }
        confirmLabel="Disable membership"
        loading={disableMutation.isPending}
        onConfirm={() => {
          if (toDisable) disableMutation.mutate(toDisable);
        }}
      />
    </div>
  );
}
