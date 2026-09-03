import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  Icon,
  TextField,
  Tooltip,
  useToast,
} from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";
import type { SecuritySettings, SecuritySettingsPatch } from "@/lib/api/types";

/**
 * The password policy every account created inside the platform must satisfy —
 * invited guests, auditors and members alike. It is applied wherever a password
 * is set: signup, invitation acceptance, and password reset.
 *
 * Some fields on the reference design need machinery this phase does not ship
 * (expiry needs a forced-change flow, lockout a state machine, idle timeout a
 * client timer). Those are stored and shown, but marked "Not enforced yet"
 * rather than presented as active controls — in a compliance product a settings
 * screen is read as a control statement, and an unenforced one is a false one.
 */

type Draft = Pick<
  SecuritySettings,
  | "password_min_length"
  | "password_require_upper"
  | "password_require_lower"
  | "password_require_digit"
  | "password_require_symbol"
  | "password_history_depth"
  | "password_max_age_days"
  | "lockout_threshold"
  | "lockout_duration_minutes"
  | "idle_timeout_minutes"
>;

const DRAFT_KEYS = [
  "password_min_length",
  "password_require_upper",
  "password_require_lower",
  "password_require_digit",
  "password_require_symbol",
  "password_history_depth",
  "password_max_age_days",
  "lockout_threshold",
  "lockout_duration_minutes",
  "idle_timeout_minutes",
] as const satisfies readonly (keyof Draft)[];

function draftOf(settings: SecuritySettings): Draft {
  return Object.fromEntries(
    DRAFT_KEYS.map((key) => [key, settings[key]]),
  ) as unknown as Draft;
}

/** Marks a field the platform stores but does not yet apply. */
function NotEnforced() {
  return (
    <Tooltip content="Saved, but not applied yet. This control arrives in a later phase">
      <span tabIndex={0} className="rounded-2xs">
        <Badge variant="neutral">Not enforced yet</Badge>
      </span>
    </Tooltip>
  );
}

function Section({
  icon,
  title,
  description,
  action,
  children,
}: {
  icon: "shield" | "controls";
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface-primary">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 font-display text-title-md text-text-primary">
            <Icon name={icon} className="size-4 text-text-subtle" />
            {title}
          </h2>
          {description ? (
            <p className="mt-1 text-body-sm text-text-subtle">{description}</p>
          ) : null}
        </div>
        {action}
      </header>
      <div className="grid grid-cols-1 gap-x-8 gap-y-5 px-5 py-5 md:grid-cols-2">
        {children}
      </div>
    </section>
  );
}

function CheckRow({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled: boolean;
}) {
  return (
    <label
      className={cn(
        "flex items-center gap-2.5 text-body-md text-text-primary",
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
      )}
    >
      <Checkbox
        checked={checked}
        onCheckedChange={onChange}
        disabled={disabled}
        aria-label={label}
      />
      {label}
    </label>
  );
}

export function PasswordPolicyCard() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = principal?.permissions.includes("security:manage") ?? false;

  const settingsQuery = useQuery({
    queryKey: ["security", principal?.tenant_id],
    queryFn: () => tenantApi.getSecurity(),
  });

  const [draft, setDraft] = useState<Draft | null>(null);

  // Re-seed whenever the server's answer changes and there is nothing unsaved,
  // so an edit made elsewhere shows up without clobbering work in progress.
  const serverDraft = settingsQuery.data ? draftOf(settingsQuery.data) : null;
  const serverKey = serverDraft ? JSON.stringify(serverDraft) : "";
  useEffect(() => {
    if (serverKey) setDraft(JSON.parse(serverKey) as Draft);
  }, [serverKey]);

  const dirtyKeys = useMemo(() => {
    if (!draft || !serverDraft) return [];
    return DRAFT_KEYS.filter((key) => draft[key] !== serverDraft[key]);
  }, [draft, serverDraft]);
  const dirty = dirtyKeys.length > 0;

  const saveMutation = useMutation({
    mutationFn: () => {
      // Send only what changed — the server patches a subset.
      const patch: SecuritySettingsPatch = {};
      for (const key of dirtyKeys) {
        Object.assign(patch, { [key]: draft![key] });
      }
      return tenantApi.updateSecurity(patch);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["security", principal?.tenant_id],
      });
      toast({ title: "Password policy updated", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "password policy"), tone: "danger" }),
  });

  if (settingsQuery.isError) {
    return (
      <div className="rounded-lg border border-status-danger-border bg-status-danger-bg px-5 py-4">
        <p className="text-body-md text-status-danger-text">
          {describeError(settingsQuery.error, "password policy").message}
        </p>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="rounded-lg border border-border bg-surface-primary px-5 py-8 text-center text-body-sm text-text-subtle">
        Loading policy…
      </div>
    );
  }

  const locked = !canManage || saveMutation.isPending;
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((previous) => (previous ? { ...previous, [key]: value } : previous));

  // Numbers arrive as strings from the input; an empty field means 0 rather
  // than NaN, which is what the "0 disables …" hints promise.
  const setNumber = (key: keyof Draft, raw: string, max: number) => {
    const parsed = Number(raw);
    const next = Number.isFinite(parsed) ? Math.min(max, Math.max(0, Math.trunc(parsed))) : 0;
    set(key, next as Draft[typeof key]);
  };

  return (
    <div className="space-y-5">
      <Section
        icon="shield"
        title="Password complexity"
        description="Applies to every account created in this workspace, including members, invited guests and auditors."
        action={
          dirty ? (
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => serverDraft && setDraft(serverDraft)}
                disabled={saveMutation.isPending}
              >
                Cancel
              </Button>
              <Button loading={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
                Save changes
              </Button>
            </div>
          ) : null
        }
      >
        <TextField
          label="Minimum length"
          type="number"
          min={8}
          max={128}
          value={String(draft.password_min_length)}
          onChange={(event) => setNumber("password_min_length", event.target.value, 128)}
          disabled={locked}
          hint="NIST minimum is 8; 12 or more is recommended for organisation accounts."
        />

        <fieldset>
          <legend className="mb-2 font-sans text-label-sm text-text-secondary">
            Character requirements
          </legend>
          <div className="space-y-2">
            <CheckRow
              label="Uppercase letter (A–Z)"
              checked={draft.password_require_upper}
              onChange={(value) => set("password_require_upper", value)}
              disabled={locked}
            />
            <CheckRow
              label="Lowercase letter (a–z)"
              checked={draft.password_require_lower}
              onChange={(value) => set("password_require_lower", value)}
              disabled={locked}
            />
            <CheckRow
              label="Digit (0–9)"
              checked={draft.password_require_digit}
              onChange={(value) => set("password_require_digit", value)}
              disabled={locked}
            />
            <CheckRow
              label="Special character (!@#$ etc.)"
              checked={draft.password_require_symbol}
              onChange={(value) => set("password_require_symbol", value)}
              disabled={locked}
            />
          </div>
        </fieldset>

        <TextField
          label="Disallow reuse of last N passwords"
          type="number"
          min={0}
          max={24}
          value={String(draft.password_history_depth)}
          onChange={(event) => setNumber("password_history_depth", event.target.value, 24)}
          disabled={locked}
          hint="0 disables history checks. Counts the password currently in force."
        />

        <div>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-sans text-label-sm text-text-secondary">
              Max password age (days)
            </span>
            <NotEnforced />
          </div>
          <TextField
            label=""
            aria-label="Max password age in days"
            type="number"
            min={0}
            max={3650}
            value={String(draft.password_max_age_days)}
            onChange={(event) => setNumber("password_max_age_days", event.target.value, 3650)}
            disabled={locked}
            hint="0 disables expiry. Current NIST guidance discourages forced rotation."
          />
        </div>
      </Section>

      <Section
        icon="controls"
        title="Account lockout & session"
        description="Brute-force protection and idle-session enforcement."
        action={
          dirty ? (
            <span className="shrink-0 text-caption text-text-subtle">
              Unsaved changes above
            </span>
          ) : null
        }
      >
        <div>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-sans text-label-sm text-text-secondary">
              Failed attempts before lock
            </span>
            <NotEnforced />
          </div>
          <TextField
            label=""
            aria-label="Failed attempts before lock"
            type="number"
            min={0}
            max={100}
            value={String(draft.lockout_threshold)}
            onChange={(event) => setNumber("lockout_threshold", event.target.value, 100)}
            disabled={locked}
            hint="0 disables lockout. Every failed sign-in is already recorded in the audit trail."
          />
        </div>

        <div>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-sans text-label-sm text-text-secondary">
              Lock duration (minutes)
            </span>
            <NotEnforced />
          </div>
          <TextField
            label=""
            aria-label="Lock duration in minutes"
            type="number"
            min={0}
            max={10080}
            value={String(draft.lockout_duration_minutes)}
            onChange={(event) =>
              setNumber("lockout_duration_minutes", event.target.value, 10080)
            }
            disabled={locked}
            hint="How long an account stays locked once the threshold is hit."
          />
        </div>

        <div>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-sans text-label-sm text-text-secondary">
              Idle session timeout (minutes)
            </span>
            <NotEnforced />
          </div>
          <TextField
            label=""
            aria-label="Idle session timeout in minutes"
            type="number"
            min={0}
            max={10080}
            value={String(draft.idle_timeout_minutes)}
            onChange={(event) => setNumber("idle_timeout_minutes", event.target.value, 10080)}
            disabled={locked}
            hint="0 disables idle timeout. Sessions already expire 12 hours after sign-in."
          />
        </div>

        <div className="rounded-md border border-border bg-surface-sunken p-3.5">
          <p className="type-overline mb-2">Current configuration</p>
          <dl className="space-y-1 text-body-sm text-text-secondary">
            <div className="flex justify-between gap-3">
              <dt>Minimum length</dt>
              <dd className="tabular font-semibold text-text-primary">
                {draft.password_min_length}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>Character classes</dt>
              <dd className="tabular font-semibold text-text-primary">
                {
                  [
                    draft.password_require_upper,
                    draft.password_require_lower,
                    draft.password_require_digit,
                    draft.password_require_symbol,
                  ].filter(Boolean).length
                }{" "}
                of 4
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>Reuse blocked</dt>
              <dd className="tabular font-semibold text-text-primary">
                {draft.password_history_depth === 0
                  ? "Off"
                  : `Last ${draft.password_history_depth}`}
              </dd>
            </div>
          </dl>
        </div>
      </Section>

      {!canManage ? (
        <p className="text-caption text-text-subtle">
          Only members with the security permission can change this policy.
        </p>
      ) : null}
    </div>
  );
}
