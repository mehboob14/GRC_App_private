import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Avatar,
  Badge,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Skeleton,
  TextField,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
  TableIconButton,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { Member } from "@/lib/api/types";
import { cn } from "@/lib/cn";

const inviteSchema = z.object({
  full_name: z.string().min(2, "Enter a name."),
  email: z.string().email("Enter a work email."),
  role_id: z.string().min(1, "Choose a role."),
});

type InviteValues = z.infer<typeof inviteSchema>;

function roleBadgeVariant(role: string) {
  if (role === "Admin") return "role" as const;
  if (role === "Auditor") return "statusPass" as const;
  return "neutral" as const;
}

export function TeamPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const membersQuery = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
  });
  const rolesQuery = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
  });

  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { full_name: "", email: "", role_id: "role-employee" },
  });

  const inviteMutation = useMutation({
    mutationFn: (values: InviteValues) => iamApi.inviteMember(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
      setOpen(false);
      form.reset({ full_name: "", email: "", role_id: "role-employee" });
      setInviteError(null);
    },
    onError: (error: unknown) => {
      setInviteError(
        error instanceof ApiError ? error.message : "Invite failed.",
      );
    },
  });

  const disableMutation = useMutation({
    mutationFn: (membershipId: string) => iamApi.disableMember(membershipId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["members", principal?.tenant_id],
        exact: true,
      });
    },
  });

  const members = useMemo(() => membersQuery.data ?? [], [membersQuery.data]);
  const canInvite = principal?.permissions.includes("members:invite");
  const canDisable = principal?.permissions.includes("members:disable");

  if (membersQuery.isLoading) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <Skeleton className="h-72 w-full rounded-xl" />
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
              : "Try again."
          }
          onRetry={() => void membersQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-heading-xl text-text">People</h1>
      <p className="mb-5 mt-2 text-body-lg text-text-muted">
        Everyone with a membership in this workspace — role, teams, and MFA
        state.
      </p>
      <div className="rounded-xl border border-border bg-bg-elevated px-5 py-[18px] shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-title-md text-text">
            Team &amp; roles
          </h2>
          <p className="mt-1 text-body-sm text-text-faint">
            {members.length} members · manage access to the Verity workspace
          </p>
        </div>
        {canInvite ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="h-9 shrink-0">
                <Icon name="plus" className="size-4" />
                Invite
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite member</DialogTitle>
                <DialogDescription>
                  Sends an invite into this workspace with a built-in role.
                </DialogDescription>
              </DialogHeader>
              <form
                className="flex flex-col gap-2"
                onSubmit={(e) =>
                  void form.handleSubmit((values) =>
                    inviteMutation.mutate(values),
                  )(e)
                }
              >
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
                <label className="mb-1 block text-label-sm text-text-muted">
                  Role
                </label>
                <Select
                  value={form.watch("role_id")}
                  onValueChange={(value) =>
                    form.setValue("role_id", value, { shouldValidate: true })
                  }
                >
                  <SelectTrigger aria-label="Role" />
                  <SelectContent>
                    {(rolesQuery.data ?? []).map((role) => (
                      <SelectItem key={role.id} value={role.id}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {inviteError ? (
                  <p className="text-body-sm text-fail-fg" role="alert">
                    {inviteError}
                  </p>
                ) : null}
                <DialogFooter>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" loading={inviteMutation.isPending}>
                    Send invite
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {members.length === 0 ? (
        <EmptyState
          title="No members yet"
          description="Invite someone to this workspace."
        />
      ) : (
        <Table className="rounded-none border-0 bg-transparent shadow-none">
          <THead>
            <TR>
              <TH>Member</TH>
              <TH>Role</TH>
              <TH>Teams</TH>
              <TH>MFA</TH>
              <TH aria-label="Actions" />
            </TR>
          </THead>
          <TBody>
            {members.map((member: Member) => (
              <TR key={member.membership_id}>
                <TD>
                  <div className="flex items-center gap-3">
                    <Avatar name={member.full_name} seed={member.email} />
                    <div>
                      <p className="text-body-md font-semibold text-text">
                        {member.full_name}
                      </p>
                      <p className="text-body-sm text-text-faint">
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
                  <span className="text-body-md text-text-muted">
                    {member.group_names.length
                      ? member.group_names.join(" · ")
                      : "—"}
                  </span>
                </TD>
                <TD>
                  {member.mfa_enabled ? (
                    <span className="inline-flex items-center gap-1.5 text-body-md text-text">
                      <Icon name="check" className="size-3.5 text-pass" />
                      On
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-body-md text-fail-fg">
                      <Icon name="alert" className="size-3.5" />
                      Off
                    </span>
                  )}
                </TD>
                <TD>
                  <TableIconButton
                    aria-label={`Actions for ${member.full_name}`}
                    disabled={
                      !canDisable ||
                      member.status === "disabled" ||
                      member.membership_id === principal?.membership_id ||
                      disableMutation.isPending
                    }
                    onClick={() => {
                      if (
                        canDisable &&
                        member.membership_id !== principal?.membership_id
                      ) {
                        void disableMutation.mutate(member.membership_id);
                      }
                    }}
                    className={cn(
                      member.membership_id === principal?.membership_id &&
                        "opacity-40",
                    )}
                  >
                    <Icon name="more" className="size-4" />
                  </TableIconButton>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
      </div>
    </div>
  );
}
