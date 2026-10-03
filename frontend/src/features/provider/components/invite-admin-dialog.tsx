import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  Icon,
  TextField,
} from "@/components/ui";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { tenantsApi } from "../api";
import { describeProviderError } from "../errors";
import { providerKeys } from "../hooks";
import type { AdminInvite, Tenant } from "../types";

const schema = z.object({
  full_name: z.string().trim().min(1, "Enter the admin's full name."),
  email: z
    .string()
    .trim()
    .min(1, "Enter the admin's email.")
    .email("Enter a valid email, like name@company.com."),
});

type FormValues = z.infer<typeof schema>;

export function InviteAdminDialog({
  tenant,
  open,
  onOpenChange,
}: {
  tenant: Tenant;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const first = tenant.status === "provisioning";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{first ? "Invite first admin" : "Invite admin"}</DialogTitle>
          <DialogDescription>
            {first
              ? "The workspace goes live when they accept."
              : "They get full access to this workspace."}
          </DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so the form and the result start fresh. */}
        <InviteAdminForm tenant={tenant} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}

function InviteAdminForm({
  tenant,
  onClose,
}: {
  tenant: Tenant;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [invite, setInvite] = useState<AdminInvite | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "" },
    mode: "onTouched",
  });

  const send = useMutation({
    mutationFn: (values: FormValues) =>
      tenantsApi.inviteAdmin(tenant.id, {
        full_name: values.full_name.trim(),
        email: values.email.trim(),
      }),
    onSuccess: (result) => {
      setInvite(result);
      // The invite completes a provisioning step, and may be what moves the tenant on.
      void queryClient.invalidateQueries({
        queryKey: providerKeys.provisioning(tenant.id),
      });
      void queryClient.invalidateQueries({
        queryKey: providerKeys.tenant(tenant.id),
      });
      void queryClient.invalidateQueries({ queryKey: providerKeys.tenantsRoot });
    },
  });

  const failure = send.isError ? describeProviderError(send.error, "tenant") : null;
  const alertRef = useAlertFocus(Boolean(failure));

  if (invite) {
    return <InviteResult invite={invite} onClose={onClose} />;
  }

  return (
    <form
      noValidate
      onSubmit={(event) =>
        void form.handleSubmit((values) => send.mutate(values))(event)
      }
    >
      <DialogBody className="space-y-3.5">
        {failure ? (
          <ErrorBanner ref={alertRef} title={failure.title}>
            {failure.message}
          </ErrorBanner>
        ) : null}
        <TextField
          label="Full name"
          placeholder="Jordan Lee"
          autoFocus
          autoComplete="off"
          error={form.formState.errors.full_name?.message}
          {...form.register("full_name")}
        />
        <TextField
          label="Email"
          type="email"
          inputMode="email"
          placeholder="jordan@acme.example"
          autoComplete="off"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
      </DialogBody>
      <DialogFooter>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" loading={send.isPending}>
          Send invite
        </Button>
      </DialogFooter>
    </form>
  );
}

/**
 * The invite came back. Whether mail went out is the API's answer, so the screen
 * says exactly that; the link is the way to hand it over when it did not.
 */
function InviteResult({
  invite,
  onClose,
}: {
  invite: AdminInvite;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(invite.accept_url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the link is on screen to copy by hand.
    }
  }

  return (
    <div>
      <DialogBody className="space-y-3.5">
        <div
          role="status"
          className="flex items-start gap-2.5 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3"
        >
          <Icon
            name="check"
            className="mt-px size-4 shrink-0 text-status-success-text"
          />
          <p className="text-body-sm font-semibold text-status-success-text">
            {invite.email_sent
              ? `Invite emailed to ${invite.member.email}.`
              : `Invite created for ${invite.member.email}. Nothing was emailed.`}
          </p>
        </div>
        <div>
          <p className="mb-1.5 font-sans text-label-sm text-text-secondary">
            {invite.email_sent ? "Invite link" : "Share this link"}
          </p>
          <div className="flex items-center gap-2 rounded-sm border border-border bg-surface-sunken py-1.5 pl-3 pr-1.5">
            <span className="min-w-0 flex-1 select-all break-all font-mono text-body-sm text-text-primary">
              {invite.accept_url}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void copy()}
              aria-label="Copy invite link"
            >
              <Icon name={copied ? "check" : "copy"} className="size-3.5" />
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
          <p className="mt-1.5 text-body-sm text-text-subtle">
            It works once. Copy it now, it is not shown again.
          </p>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button onClick={onClose}>Done</Button>
      </DialogFooter>
    </div>
  );
}
