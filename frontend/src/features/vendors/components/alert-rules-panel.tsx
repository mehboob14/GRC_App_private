import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { deleteAlertRule, listAlertRules, saveAlertRule } from "../api";
import {
  ALERT_ACTIONS,
  FINDING_SEVERITIES,
  SIGNAL_TYPES,
  type AlertRule,
  type AlertRuleInput,
} from "../types";
import { TIER_META } from "../tokens";

const ACTION_LABEL: Record<string, string> = {
  notify: "Tell the owner and the TPRM lead",
  create_task: "Open a task",
  trigger_reassessment: "Bring the review forward",
};

const TYPE_LABEL: Record<string, string> = {
  breach: "Breach",
  adverse_media: "Adverse news",
  rating_change: "Rating change",
  financial: "Financial",
  sla_breach: "Service level",
  cert_expiry: "Certificate lapsed",
};

const TIERS = ["critical", "high", "medium", "low"] as const;

const BLANK: AlertRuleInput = {
  name: "",
  signal_types: [],
  tier_scope: [],
  min_severity: "high",
  action: "notify",
  channel: "in_app",
  is_enabled: true,
};

/**
 * What a signal sets off, and for which vendors.
 *
 * A rule with no signal types or no tiers matches all of them: an empty filter
 * reads as "anything" everywhere else in the product, and a rule that matched
 * nothing until every box was ticked would be a rule people quietly stop using.
 */
export function AlertRulesPanel({ canManage }: { canManage: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["vendor-alert-rules"], queryFn: listAlertRules });
  const [draft, setDraft] = useState<AlertRuleInput | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const apply = (items: AlertRule[]) => {
    queryClient.setQueryData(["vendor-alert-rules"], items);
    setDraft(null);
    setEditingId(null);
  };

  const save = useMutation({
    mutationFn: (input: AlertRuleInput) => saveAlertRule(input, editingId ?? undefined),
    onSuccess: (items) => {
      apply(items);
      toast({ title: "Alert rule saved", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "alert rule"), tone: "danger" }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteAlertRule(id),
    onSuccess: (items) => {
      apply(items);
      toast({ title: "Alert rule removed", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "alert rule"), tone: "danger" }),
  });

  const rules = query.data ?? [];
  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-title-sm text-text-primary">Alert rules</h2>
          <p className="mt-0.5 text-caption text-text-subtle">
            What a recorded signal sets off. Leave a filter empty to match everything.
          </p>
        </div>
        {canManage && draft === null ? (
          <Button variant="secondary" size="sm" onClick={() => setDraft({ ...BLANK })}>
            <Icon name="plus" className="size-4" />
            Add rule
          </Button>
        ) : null}
      </div>

      {query.isLoading ? (
        <Skeleton className="mt-3 h-24 w-full" />
      ) : rules.length === 0 && draft === null ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          No rules yet. Signals are still recorded and visible on the vendor.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {rules.map((r) => (
            <li key={r.id} className="flex flex-wrap items-start justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-body-md text-text-primary">
                  <span className="font-semibold">{r.name}</span>
                  {r.is_enabled ? null : <Badge variant="count">Off</Badge>}
                </p>
                <p className="mt-0.5 text-caption text-text-subtle">
                  {r.signal_types.length
                    ? r.signal_types.map((t) => TYPE_LABEL[t] ?? t).join(", ")
                    : "Any signal"}
                  {" · "}
                  {r.min_severity} and above
                  {" · "}
                  {r.tier_scope.length
                    ? r.tier_scope.map((t) => TIER_META[t]?.label ?? t).join(", ")
                    : "any tier"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <StatusPill
                  status="progress"
                  label={ACTION_LABEL[r.action] ?? r.action}
                  kind="inline"
                />
                {canManage ? (
                  <>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Edit ${r.name}`}
                      onClick={() => {
                        setEditingId(r.id);
                        setDraft({
                          name: r.name,
                          signal_types: [...r.signal_types],
                          tier_scope: [...r.tier_scope],
                          min_severity: r.min_severity,
                          action: r.action,
                          channel: r.channel,
                          is_enabled: r.is_enabled,
                        });
                      }}
                    >
                      <Icon name="edit" className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Remove ${r.name}`}
                      loading={remove.isPending && remove.variables === r.id}
                      onClick={() => remove.mutate(r.id)}
                    >
                      <Icon name="trash" className="size-4" />
                    </Button>
                  </>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {draft !== null ? (
        <form
          className="mt-3 space-y-3 rounded-md border border-border bg-surface-sunken p-3.5"
          onSubmit={(e) => {
            e.preventDefault();
            if (draft.name.trim()) save.mutate(draft);
          }}
        >
          <TextField
            label="Name"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="Breach at a critical vendor"
            autoFocus
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <SelectField label="From this severity up">
              <Select
                value={draft.min_severity}
                onValueChange={(v) => setDraft({ ...draft, min_severity: v })}
              >
                <SelectTrigger aria-label="Minimum severity" />
                <SelectContent>
                  {FINDING_SEVERITIES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Then">
              <Select
                value={draft.action}
                onValueChange={(v) => setDraft({ ...draft, action: v })}
              >
                <SelectTrigger aria-label="Action" />
                <SelectContent>
                  {ALERT_ACTIONS.map((a) => (
                    <SelectItem key={a} value={a}>
                      {ACTION_LABEL[a] ?? a}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          </div>
          <div>
            <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Signals</p>
            <div className="flex flex-wrap gap-2">
              {SIGNAL_TYPES.map((t) => {
                const on = draft.signal_types.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() =>
                      setDraft({ ...draft, signal_types: toggle(draft.signal_types, t) })
                    }
                    className={
                      on
                        ? "rounded-full border border-action-accent-border bg-action-accent-tint px-3 py-1 text-label-sm text-text-link"
                        : "rounded-full border border-border px-3 py-1 text-label-sm text-text-secondary hover:bg-surface-hover"
                    }
                  >
                    {TYPE_LABEL[t] ?? t}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Tiers</p>
            <div className="flex flex-wrap gap-2">
              {TIERS.map((t) => {
                const on = draft.tier_scope.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setDraft({ ...draft, tier_scope: toggle(draft.tier_scope, t) })}
                    className={
                      on
                        ? "rounded-full border border-action-accent-border bg-action-accent-tint px-3 py-1 text-label-sm text-text-link"
                        : "rounded-full border border-border px-3 py-1 text-label-sm text-text-secondary hover:bg-surface-hover"
                    }
                  >
                    {TIER_META[t]?.label ?? t}
                  </button>
                );
              })}
            </div>
          </div>
          <label className="flex items-center gap-2 text-body-sm text-text-secondary">
            <input
              type="checkbox"
              className="size-4 accent-action-accent"
              checked={draft.is_enabled}
              onChange={(e) => setDraft({ ...draft, is_enabled: e.target.checked })}
            />
            Rule is on
          </label>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setDraft(null);
                setEditingId(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={save.isPending} disabled={!draft.name.trim()}>
              {editingId ? "Save rule" : "Add rule"}
            </Button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
