import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  Skeleton,
  Switch,
  TextField,
  useToast,
} from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { SmtpConfig, SmtpConfigUpdate } from "@/lib/api/types";

type Form = {
  host: string;
  port: string;
  username: string;
  from_name: string;
  from_address: string;
  use_tls: boolean;
  enabled: boolean;
};

function toForm(c: SmtpConfig): Form {
  return {
    host: c.host ?? "",
    port: String(c.port ?? 587),
    username: c.username ?? "",
    from_name: c.from_name ?? "",
    from_address: c.from_address ?? "",
    use_tls: c.use_tls,
    enabled: c.enabled,
  };
}

function buildPatch(form: Form, password: string): SmtpConfigUpdate {
  const patch: SmtpConfigUpdate = {
    host: form.host || null,
    port: Number(form.port) || 587,
    username: form.username || null,
    from_name: form.from_name || null,
    from_address: form.from_address || null,
    use_tls: form.use_tls,
    enabled: form.enabled,
  };
  if (password) patch.password = password; // omit → keep the stored one
  return patch;
}

/** Outbound email — the tenant's own SMTP server. Rendered on the Company tab. */
export function SmtpSettings({ canManage }: { canManage: boolean }) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = ["tenant-smtp", principal?.tenant_id];

  const query = useQuery({ queryKey: key, queryFn: () => tenantApi.getSmtp() });
  const [form, setForm] = useState<Form | null>(null);
  const [password, setPassword] = useState("");
  const [testTo, setTestTo] = useState(principal?.user.email ?? "");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (query.data) setForm(toForm(query.data));
  }, [query.data]);

  const set = <K extends keyof Form>(k: K, v: Form[K]) =>
    setForm((f) => (f ? { ...f, [k]: v } : f));

  const saveMutation = useMutation({
    mutationFn: () => tenantApi.updateSmtp(buildPatch(form!, password)),
    onSuccess: (updated) => {
      queryClient.setQueryData(key, updated);
      setPassword("");
      toast({ title: "SMTP settings saved", tone: "success" });
    },
  });

  // Persist what's on screen first, so the test reflects the current form.
  const testMutation = useMutation({
    mutationFn: async () => {
      const updated = await tenantApi.updateSmtp(buildPatch(form!, password));
      queryClient.setQueryData(key, updated);
      setPassword("");
      return tenantApi.testSmtp(testTo);
    },
  });

  if (query.isLoading || !form) {
    return <Skeleton className="h-72 w-full rounded-lg" />;
  }

  const hasPassword = query.data?.has_password ?? false;
  const busy = saveMutation.isPending || testMutation.isPending;

  const summary =
    form.enabled && form.host.trim()
      ? `Sending through ${form.host.trim()}`
      : "Using the platform default mail server";

  return (
    // A summary row, not the whole form: SMTP is set once and rarely revisited,
    // so it earns a line on the page and a dialog for the eight fields behind it.
    <div className="rounded-lg border border-border bg-surface-primary p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-display text-heading-sm text-text-primary">
            Outbound email (SMTP)
          </h2>
          <p className="mt-1 text-body-md text-text-secondary">
            Send Verity emails (invites, verification) from your own mail
            server.
          </p>
          <p className="mt-2.5 text-body-sm text-text-subtle">{summary}</p>
        </div>
        <Button
          variant="secondary"
          className="shrink-0"
          onClick={() => setOpen(true)}
        >
          {canManage ? "Configure" : "View settings"}
        </Button>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent size="md" scrollBody>
          <DialogHeader>
            <DialogTitle>Outbound email (SMTP)</DialogTitle>
            <DialogDescription>
              Verity sends invites and verification links through this server.
              Leave it off to use the platform default.
            </DialogDescription>
          </DialogHeader>

          <DialogBody className="space-y-4 pb-1">
            {saveMutation.isError ? (
              <ErrorBanner className="mb-4" title="Couldn’t save">
                {saveMutation.error instanceof ApiError
                  ? saveMutation.error.message
                  : "The request didn’t reach the server."}
              </ErrorBanner>
            ) : null}

            <div className="mb-4 flex items-center justify-between rounded-md border border-border bg-surface-sunken px-3.5 py-3">
              <div>
                <p className="text-body-md font-semibold text-text-primary">
                  Use my own SMTP
                </p>
                <p className="text-body-sm text-text-subtle">
                  When on, Verity sends this workspace’s email through the
                  server below.
                </p>
              </div>
              <Switch
                checked={form.enabled}
                onCheckedChange={(v) => set("enabled", v)}
                disabled={!canManage}
              />
            </div>

            <fieldset
              disabled={!canManage}
              className="grid gap-4 sm:grid-cols-2"
            >
              <TextField
                label="SMTP host"
                placeholder="smtp.yourcompany.com"
                value={form.host}
                onChange={(e) => set("host", e.target.value)}
              />
              <TextField
                label="Port"
                inputMode="numeric"
                placeholder="587"
                value={form.port}
                onChange={(e) =>
                  set("port", e.target.value.replace(/\D/g, "").slice(0, 5))
                }
              />
              <TextField
                label="Username"
                optional
                autoComplete="off"
                placeholder="mailer@yourcompany.com"
                value={form.username}
                onChange={(e) => set("username", e.target.value)}
              />
              <TextField
                label="Password"
                type="password"
                optional
                autoComplete="new-password"
                placeholder={
                  hasPassword
                    ? "•••••••• (leave blank to keep)"
                    : "SMTP password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <TextField
                label="From name"
                optional
                placeholder="Acme Security"
                value={form.from_name}
                onChange={(e) => set("from_name", e.target.value)}
              />
              <TextField
                label="From address"
                type="email"
                placeholder="no-reply@yourcompany.com"
                value={form.from_address}
                onChange={(e) => set("from_address", e.target.value)}
              />
              <label className="flex items-center gap-2.5 text-body-md text-text-primary sm:col-span-2">
                <Switch
                  checked={form.use_tls}
                  onCheckedChange={(v) => set("use_tls", v)}
                  disabled={!canManage}
                />
                Use STARTTLS (recommended for port 587)
              </label>
            </fieldset>

            {canManage ? (
              <>
                <div className="mt-6 border-t border-border pt-5">
                  <p className="mb-2 font-sans text-label-sm text-text-secondary">
                    Send a test email
                  </p>
                  {testMutation.data ? (
                    testMutation.data.ok ? (
                      <div
                        className="mb-3 flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-2.5"
                        role="status"
                      >
                        <Icon
                          name="check"
                          className="size-4 text-status-success-text"
                        />
                        <p className="text-body-sm font-semibold text-status-success-text">
                          Test email sent to {testTo}.
                        </p>
                      </div>
                    ) : (
                      <ErrorBanner className="mb-3" title="Test failed">
                        {testMutation.data.detail}
                      </ErrorBanner>
                    )
                  ) : null}
                  <div className="flex flex-wrap items-end gap-2">
                    <div className="min-w-0 flex-1">
                      <TextField
                        label="Send to"
                        type="email"
                        value={testTo}
                        onChange={(e) => setTestTo(e.target.value)}
                      />
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="lg"
                      loading={testMutation.isPending}
                      disabled={busy || !testTo}
                      onClick={() => testMutation.mutate()}
                    >
                      Save &amp; send test
                    </Button>
                  </div>
                  <p className="mt-1.5 text-caption text-text-subtle">
                    Saves the settings above, then sends through your server.
                  </p>
                </div>
              </>
            ) : (
              <p className="mt-4 text-body-sm text-text-subtle">
                View-only. Ask an Admin to change SMTP settings.
              </p>
            )}
          </DialogBody>

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setOpen(false)}
            >
              Close
            </Button>
            {canManage ? (
              <Button
                type="button"
                loading={saveMutation.isPending}
                disabled={busy}
                onClick={() => saveMutation.mutate()}
              >
                Save settings
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
