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
  ErrorState,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  Switch,
  TextField,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { iamApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Settings → Security → SSO (openspec/changes/add-keycloak-sso, phases B and C). In order: name the
 * Keycloak organization and the email domains, prove each domain with a DNS record, connect the
 * identity provider (Verity sets it up in Keycloak), sign in once with SSO to prove it works, then
 * require it if wanted. Phase D: accounts made on first sign in, Keycloak groups giving roles, and
 * the directory sync (hourly, or Sync now).
 */

type Setup = {
  configured: boolean;
  organization_alias: string;
  domains: string[];
  verified_domains: string[];
  txt_name_prefix: string;
  txt_value: string | null;
  enabled: boolean;
  enforce: boolean;
  jit_enabled: boolean;
  default_role_id: string | null;
  verified_at: string | null;
  provider: string | null;
  idp_alias: string | null;
  redirect_uri: string | null;
  entity_id: string;
  providers: { key: string; label: string }[];
  synced_at: string | null;
  group_roles: { id: string; group_name: string; role_id: string }[];
};

type SyncResult = {
  skipped: string | null;
  created: number;
  disabled: number;
  granted: number;
  revoked: number;
  kept: number;
};

function syncSummary(r: SyncResult): string {
  if (r.skipped === "off") return "Turn on Sign in with SSO first.";
  if (r.skipped === "empty") return "Keycloak returned no members, so nothing changed.";
  const parts = [
    r.created && `${r.created} added`,
    r.disabled && `${r.disabled} disabled`,
    r.granted && `${r.granted} roles given`,
    r.revoked && `${r.revoked} roles taken back`,
    r.kept && `${r.kept} kept so an Admin remains`,
  ].filter(Boolean);
  return parts.length ? `Synced: ${parts.join(", ")}` : "Synced. Nothing changed";
}

type ProviderForm = {
  provider: string;
  tenant_id: string;
  okta_domain: string;
  discovery_url: string;
  metadata_url: string;
  client_id: string;
  client_secret: string;
};

const PATH = "/tenant/security/sso";
const EMPTY_FORM: ProviderForm = {
  provider: "entra",
  tenant_id: "",
  okta_domain: "",
  discovery_url: "",
  metadata_url: "",
  client_id: "",
  client_secret: "",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-surface-primary px-5 py-4">
      <h3 className="font-display text-title-md text-text-primary">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Row({ title, description, control }: { title: string; description: string; control: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 border-t border-border py-3 first:border-t-0 first:pt-0">
      <div className="min-w-0 flex-1">
        <p className="text-body-lg font-semibold text-text-primary">{title}</p>
        <p className="text-body-sm text-text-subtle">{description}</p>
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

function Copyable({ value }: { value: string }) {
  const { toast } = useToast();
  return (
    <button
      type="button"
      onClick={() => void navigator.clipboard.writeText(value).then(() => toast({ title: "Copied", tone: "success" }))}
      className="max-w-full truncate rounded-sm bg-surface-sunken px-1.5 py-0.5 text-left font-mono text-caption text-text-primary hover:bg-surface-hover"
      title="Copy"
    >
      {value}
    </button>
  );
}

export function SsoSettingsPage() {
  const { principal } = useAuth();
  const canManage = principal?.permissions.includes("security:manage") ?? false;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = ["tenant-sso", principal?.tenant_id];
  const query = useQuery({ queryKey: key, queryFn: () => apiFetch<Setup>(PATH), enabled: canManage });
  const [alias, setAlias] = useState("");
  const [domains, setDomains] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [form, setForm] = useState<ProviderForm>(EMPTY_FORM);
  const [choosingRole, setChoosingRole] = useState(false);
  const [jitRole, setJitRole] = useState("");
  const [mapping, setMapping] = useState(false);
  const [group, setGroup] = useState({ name: "", role: "" });
  const rolesQuery = useQuery({
    queryKey: ["roles", principal?.tenant_id],
    queryFn: () => iamApi.listRoles(),
    enabled: canManage,
  });
  useEffect(() => {
    if (query.data) {
      setAlias(query.data.organization_alias);
      setDomains(query.data.domains.join(", "));
    }
  }, [query.data]);

  const onSaved = (data: Setup, title: string) => {
    queryClient.setQueryData(key, data);
    toast({ title, tone: "success" });
  };
  const onError = (error: unknown) => toast({ title: errorToast(error, "SSO settings"), tone: "danger" });

  const save = useMutation({
    mutationFn: (patch: Partial<Setup>) => {
      const current = query.data;
      return apiFetch<Setup>(PATH, {
        method: "PUT",
        body: JSON.stringify({
          organization_alias: alias,
          domains: domains.split(/[\s,]+/).filter(Boolean),
          enabled: current?.enabled ?? false,
          enforce: current?.enforce ?? false,
          jit_enabled: current?.jit_enabled ?? false,
          default_role_id: current?.default_role_id ?? null,
          ...patch,
        }),
      });
    },
    onSuccess: (data) => onSaved(data, "SSO settings saved"),
    onError,
  });
  const addGroup = useMutation({
    mutationFn: () =>
      apiFetch<Setup>(`${PATH}/groups`, {
        method: "POST",
        body: JSON.stringify({ group_name: group.name.trim(), role_id: group.role }),
      }),
    onSuccess: (data) => {
      onSaved(data, "Group added");
      setMapping(false);
      setGroup({ name: "", role: "" });
    },
    onError,
  });
  const removeGroup = useMutation({
    mutationFn: (id: string) => apiFetch<Setup>(`${PATH}/groups/${id}`, { method: "DELETE" }),
    onSuccess: (data) => onSaved(data, "Group removed"),
    onError,
  });
  const sync = useMutation({
    mutationFn: () => apiFetch<SyncResult>(`${PATH}/sync`, { method: "POST" }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: key });
      void queryClient.invalidateQueries({ queryKey: ["members", principal?.tenant_id] });
      toast({ title: syncSummary(result), tone: result.skipped ? "neutral" : "success" });
    },
    onError,
  });
  const verify = useMutation({
    mutationFn: (domain: string) =>
      apiFetch<Setup>(`${PATH}/domains/${encodeURIComponent(domain)}/verify`, { method: "POST" }),
    onSuccess: (data, domain) => onSaved(data, `${domain} is proven`),
    onError,
  });
  const connect = useMutation({
    mutationFn: () => {
      const body: Record<string, string> = { provider: form.provider };
      for (const [k, v] of Object.entries(form)) if (k !== "provider" && v.trim()) body[k] = v.trim();
      return apiFetch<Setup>(`${PATH}/provider`, { method: "PUT", body: JSON.stringify(body) });
    },
    onSuccess: (data) => {
      onSaved(data, "Identity provider connected");
      setConnecting(false);
      setForm(EMPTY_FORM);
    },
    onError,
  });

  if (!canManage) {
    return <p className="text-body-md text-text-secondary">Only workspace admins can see SSO settings.</p>;
  }
  if (query.isLoading) return <Skeleton className="h-72 w-full max-w-[860px] rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "SSO settings");
    return <ErrorState title={failure.title} description={failure.message} referenceId={failure.referenceId} />;
  }
  const data = query.data;
  const proven = new Set(data.verified_domains);
  const verified = data.verified_at ? new Date(data.verified_at).toLocaleString() : null;
  const providerLabel = data.providers.find((p) => p.key === data.provider)?.label;
  const roles = (rolesQuery.data ?? []).slice().sort((a, b) => a.name.localeCompare(b.name));
  const roleName = (id: string | null) => roles.find((r) => r.id === id)?.name ?? "a role";
  const synced = data.synced_at ? new Date(data.synced_at).toLocaleString() : null;
  const roleSelect = (value: string, onChange: (v: string) => void, choices = roles) => (
    <SelectField label="Role">
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger aria-label="Role" />
        <SelectContent>
          {choices.map((r) => (
            <SelectItem key={r.id} value={r.id}>
              {r.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </SelectField>
  );
  const redirectFor = (provider: string) =>
    data.redirect_uri?.replace(/\/broker\/[^/]+\/endpoint$/, `/broker/${data.organization_alias}-${provider}/endpoint`) ?? "";
  const field = (name: keyof ProviderForm, label: string, placeholder?: string, secret?: boolean) => (
    <TextField
      label={label}
      type={secret ? "password" : "text"}
      value={form[name]}
      placeholder={placeholder}
      autoComplete="off"
      onChange={(e) => setForm({ ...form, [name]: e.target.value })}
    />
  );

  return (
    <div className="max-w-[860px] space-y-4">
      <Section title="Organization and email domains">
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="Keycloak organization" value={alias} onChange={(e) => setAlias(e.target.value)} />
          <TextField
            label="Email domains"
            value={domains}
            onChange={(e) => setDomains(e.target.value)}
            placeholder="acme.com, acme.co.uk"
          />
        </div>
        <div className="mt-3 flex justify-end">
          <Button loading={save.isPending} disabled={!alias.trim()} onClick={() => save.mutate({})}>
            Save
          </Button>
        </div>
        {data.configured && data.domains.length ? (
          <div className="mt-3 space-y-2">
            {data.domains.map((d) => (
              <div key={d} className="flex flex-wrap items-center gap-3 rounded-md border border-border px-3 py-2">
                <span className="font-semibold text-text-primary">{d}</span>
                <StatusPill status={proven.has(d) ? "success" : "pending"} label={proven.has(d) ? "Proven" : "Not proven"} />
                {!proven.has(d) && data.txt_value ? (
                  <>
                    <span className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5 text-caption text-text-secondary">
                      TXT record at <Copyable value={`${data.txt_name_prefix}.${d}`} /> with value
                      <Copyable value={data.txt_value} />
                    </span>
                    <Button size="sm" variant="secondary" loading={verify.isPending && verify.variables === d} onClick={() => verify.mutate(d)}>
                      Check
                    </Button>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {data.configured ? (
        <Section title="Identity provider">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-body-md text-text-primary">
              {providerLabel ? `${providerLabel} is connected.` : "Not connected yet."}
            </span>
            <Button
              variant={providerLabel ? "secondary" : "primary"}
              disabled={!data.verified_domains.length}
              onClick={() => setConnecting(true)}
            >
              {providerLabel ? "Change" : "Connect"}
            </Button>
            {!data.verified_domains.length ? (
              <span className="text-caption text-text-subtle">Prove a domain first.</span>
            ) : null}
          </div>
        </Section>
      ) : null}

      {data.configured ? (
        <Section title="Use">
          <Row
            title="Sign in with SSO"
            description="Members can use the SSO button on the sign in page."
            control={
              <Switch
                checked={data.enabled}
                onCheckedChange={(value) => save.mutate({ enabled: value, enforce: value && data.enforce })}
                disabled={save.isPending}
                aria-label="Sign in with SSO"
              />
            }
          />
          <Row
            title="Require SSO"
            description={
              !verified
                ? "Sign out and sign in with SSO once to prove it works. Then you can require it."
                : data.enforce
                  ? `Members can only sign in with SSO. Admins with MFA keep a password for emergencies. SSO worked on ${verified}.`
                  : `Stop members signing in with a password. Admins with MFA keep it for emergencies. SSO worked on ${verified}.`
            }
            control={
              <Switch
                checked={data.enforce}
                onCheckedChange={(value) => save.mutate({ enforce: value })}
                disabled={save.isPending || !data.enabled || !verified}
                aria-label="Require SSO"
              />
            }
          />
          <Row
            title="Create accounts automatically"
            description={
              data.jit_enabled
                ? `People from your proven domains join on their first SSO sign in, as ${roleName(data.default_role_id)}.`
                : "People from your proven domains join on their first SSO sign in."
            }
            control={
              <Switch
                checked={data.jit_enabled}
                onCheckedChange={(value) => {
                  if (!value) save.mutate({ jit_enabled: false });
                  else {
                    setJitRole(data.default_role_id ?? "");
                    setChoosingRole(true);
                  }
                }}
                disabled={save.isPending}
                aria-label="Create accounts automatically"
              />
            }
          />
        </Section>
      ) : null}

      {data.configured ? (
        <Section title="Groups and sync">
          <div className="space-y-2">
            {data.group_roles.map((g) => (
              <div key={g.id} className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                <span className="font-mono text-body-sm text-text-primary">{g.group_name}</span>
                <span className="text-body-sm text-text-subtle">gives</span>
                <span className="flex-1 text-body-md font-semibold text-text-primary">{roleName(g.role_id)}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={removeGroup.isPending && removeGroup.variables === g.id}
                  onClick={() => removeGroup.mutate(g.id)}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button variant="secondary" onClick={() => setMapping(true)}>
              Add group
            </Button>
            <span className="flex-1 text-caption text-text-subtle">
              {synced ? `Last synced ${synced}` : "Not synced yet"}
            </span>
            <Button loading={sync.isPending} disabled={!data.enabled} onClick={() => sync.mutate()}>
              Sync now
            </Button>
          </div>
        </Section>
      ) : null}

      <Dialog open={choosingRole} onOpenChange={setChoosingRole}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Role for new people</DialogTitle>
            <DialogDescription>Groups can give more roles later.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            {roleSelect(jitRole, setJitRole, roles.filter((r) => !(r.built_in && r.name === "Admin")))}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setChoosingRole(false)}>
              Cancel
            </Button>
            <Button
              disabled={!jitRole}
              loading={save.isPending}
              onClick={() =>
                save.mutate({ jit_enabled: true, default_role_id: jitRole }, { onSuccess: () => setChoosingRole(false) })
              }
            >
              Turn on
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={mapping} onOpenChange={setMapping}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Add a group</DialogTitle>
            <DialogDescription>Members of this Keycloak group get the role at each sync.</DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <TextField
              label="Group"
              value={group.name}
              placeholder="engineering"
              autoComplete="off"
              onChange={(e) => setGroup({ ...group, name: e.target.value })}
            />
            {roleSelect(group.role, (role) => setGroup({ ...group, role }))}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setMapping(false)}>
              Cancel
            </Button>
            <Button
              disabled={!group.name.trim() || !group.role}
              loading={addGroup.isPending}
              onClick={() => addGroup.mutate()}
            >
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={connecting} onOpenChange={setConnecting}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Connect your identity provider</DialogTitle>
            <DialogDescription>Verity sets it up in Keycloak. The secret is passed on, never stored here.</DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <SelectField label="Provider">
              <Select value={form.provider} onValueChange={(v) => setForm({ ...form, provider: v })}>
                <SelectTrigger aria-label="Provider" />
                <SelectContent>
                  {data.providers.map((p) => (
                    <SelectItem key={p.key} value={p.key}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <div className="rounded-md bg-surface-sunken p-3 text-caption text-text-secondary">
              <p className="mb-1">
                {form.provider === "saml" ? "Register at your provider. ACS URL:" : "Register this redirect URI at your provider:"}
              </p>
              <Copyable value={redirectFor(form.provider)} />
              {form.provider === "saml" ? (
                <p className="mt-2">
                  Entity ID: <Copyable value={data.entity_id} />
                </p>
              ) : null}
            </div>
            {form.provider === "entra" ? field("tenant_id", "Directory (tenant) ID") : null}
            {form.provider === "okta" ? field("okta_domain", "Okta domain", "acme.okta.com") : null}
            {form.provider === "oidc" ? field("discovery_url", "Discovery URL", "https://…/.well-known/openid-configuration") : null}
            {form.provider === "saml" ? field("metadata_url", "Metadata URL") : null}
            {form.provider !== "saml" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {field("client_id", "Client ID")}
                {field("client_secret", "Client secret", undefined, true)}
              </div>
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConnecting(false)}>
              Cancel
            </Button>
            <Button loading={connect.isPending} onClick={() => connect.mutate()}>
              Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
