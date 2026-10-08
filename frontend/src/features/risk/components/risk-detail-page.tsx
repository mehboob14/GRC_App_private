import { useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  DetailHeader,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  TabStrip,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { TraceButton } from "@/features/linkage/components/trace-button";
import {
  changeStatus,
  getRisk,
  listRegisters,
  markReviewed,
  revokeAcceptance,
  unlinkControl,
  unlinkRecord,
  withdrawAcceptance,
} from "../api";
import type { Acceptance, LinkType, Register, RiskDetail } from "../types";
import {
  ATTENTION_META,
  BAND_TONE,
  daysUntil,
  EVENT_ICON,
  EVENT_LABEL,
  fmtDate,
  humanise,
  isoDate,
  LINK_META,
  ORIGIN_LABEL,
  REGISTER_TYPE_LABEL,
  STATUS_META,
  TREATMENT_META,
} from "../tokens";
import { Heatmap } from "./heatmap";
import { AppetitePill, CustomValues } from "./risk-extras";
import {
  AcceptanceRequestDialog,
  AcceptanceStatus,
  ActionDialog,
  ControlPickerDialog,
  DecisionDialog,
  LinkRecordDialog,
  NoteDialog,
} from "./risk-dialogs";
import { RiskFormDialog } from "./risk-form-dialog";
import { BandPill, ScoreChip } from "./score";
import { SoonSection } from "./soon";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "treatment", label: "Treatment" },
  { id: "controls", label: "Controls" },
  { id: "links", label: "Links" },
  { id: "acceptance", label: "Acceptance" },
  { id: "history", label: "History" },
  { id: "assessments", label: "Assessments", soon: true },
  { id: "indicators", label: "KRIs", soon: true },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function RiskDetailPage() {
  const { riskId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "overview") as TabId;
  const goTo = (id: TabId) => setParams(id === "overview" ? {} : { tab: id }, { replace: true });

  const { principal } = useAuth();
  const canManage = hasPermission(principal, "risks:manage");
  const canApprove = hasPermission(principal, "risks:approve");
  const me = principal?.membership_id ?? null;

  const queryClient = useQueryClient();
  const { toast } = useToast();
  const riskQuery = useQuery({ queryKey: ["risk", riskId], queryFn: () => getRisk(riskId) });
  const registersQuery = useQuery({ queryKey: ["risk-registers"], queryFn: listRegisters });

  const [editing, setEditing] = useState(false);
  const [dialog, setDialog] = useState<
    null | "controls" | "link" | "action" | "accept" | "decide" | "close" | "reopen" | "review" | "revoke"
  >(null);
  const [linkType, setLinkType] = useState<LinkType>("asset");
  const [target, setTarget] = useState<Acceptance | null>(null);

  const seed = (next: RiskDetail, message: string) => {
    queryClient.setQueryData(["risk", next.id], next);
    void queryClient.invalidateQueries({ queryKey: ["risks"] });
    void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
    toast({ title: message, tone: "success" });
    setDialog(null);
  };
  const fail = (e: unknown) => toast({ title: errorToast(e, "risk"), tone: "danger" });

  const status = useMutation({
    mutationFn: ({ to, note }: { to: string; note: string }) => changeStatus(riskId, to, note),
    onSuccess: (next) => seed(next, `Marked ${STATUS_META[next.status].label.toLowerCase()}`),
    onError: fail,
  });
  const review = useMutation({
    mutationFn: ({ note, date }: { note: string; date: string | null }) => markReviewed(riskId, note || null, date),
    onSuccess: (next) => seed(next, "Review recorded"),
    onError: fail,
  });
  const revoke = useMutation({
    mutationFn: (reason: string) => revokeAcceptance(riskId, target!.id, reason),
    onSuccess: (next) => seed(next, "Acceptance revoked"),
    onError: fail,
  });
  const withdraw = useMutation({
    mutationFn: (id: string) => withdrawAcceptance(riskId, id),
    onSuccess: (next) => seed(next, "Request withdrawn"),
    onError: fail,
  });
  const removeControl = useMutation({
    mutationFn: (controlId: string) => unlinkControl(riskId, controlId),
    onSuccess: (next) => seed(next, "Control unlinked"),
    onError: fail,
  });
  const removeLink = useMutation({
    mutationFn: (linkId: string) => unlinkRecord(riskId, linkId),
    onSuccess: (next) => seed(next, "Link removed"),
    onError: fail,
  });

  if (riskQuery.isError) {
    const error = describeError(riskQuery.error, "risk");
    return (
      <div className="mt-4">
        <ErrorState title={error.title} description={error.message} onRetry={() => void riskQuery.refetch()} />
      </div>
    );
  }
  const risk = riskQuery.data;
  const register = registersQuery.data?.find((r) => r.id === risk?.register_id);
  if (!risk || !register) {
    return (
      <div className="mt-2 space-y-4">
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  const bands = register.severity_bands;
  const open = risk.acceptances.find((a) => a.status === "pending" || a.status === "active");
  const pendingForMe = risk.acceptances.find((a) => a.status === "pending" && a.approver?.membership_id === me);
  const statusMeta = STATUS_META[risk.status];
  const tabs = TABS.map((t) => ({
    ...t,
    count:
      t.id === "controls"
        ? risk.controls.length || undefined
        : t.id === "links"
          ? risk.links.length || undefined
          : t.id === "treatment"
            ? risk.actions.length || undefined
            : undefined,
  }));

  return (
    <div>
      <DetailHeader
        backTo="/risks"
        backLabel="Back to risks"
        icon="risk"
        title={risk.title}
        chips={
          <>
            <Badge variant="neutral">{risk.code}</Badge>
            <StatusPill status={statusMeta.family} label={statusMeta.label} kind="inline" />
            <BandPill score={risk.residual_score ?? risk.inherent_score} bands={bands} />
            {risk.attention.includes("no_controls") ? (
              <StatusPill status="danger" label="No linked control" kind="inline" />
            ) : null}
            {risk.attention.includes("review_overdue") ? (
              <StatusPill status="warning" label="Review overdue" kind="inline" />
            ) : null}
          </>
        }
        meta={
          <span>
            {[risk.category_name, risk.sub_category_name, register.name].filter(Boolean).join(" · ")}
          </span>
        }
        actions={
          canManage || canApprove ? (
            <>
              <TraceButton type="risk" id={risk.id} />
              {pendingForMe && canApprove ? (
                <Button
                  variant="success-2"
                  onClick={() => {
                    setTarget(pendingForMe);
                    setDialog("decide");
                  }}
                >
                  <Icon name="scales" className="size-4" />
                  Decide acceptance
                </Button>
              ) : null}
              {canManage ? (
                <Button variant="secondary" onClick={() => setEditing(true)}>
                  <Icon name="edit" className="size-4" />
                  Edit
                </Button>
              ) : null}
              {canManage ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="secondary" aria-label={`Actions for ${risk.code}`}>
                      Actions
                      <Icon name="chev" className="size-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-60">
                    {risk.status !== "closed" ? (
                      <>
                        <DropdownMenuItem onSelect={() => setDialog("action")}>
                          <Icon name="checklist" className="size-4 text-text-subtle" />
                          Add treatment action
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => setDialog("controls")}>
                          <Icon name="controls" className="size-4 text-text-subtle" />
                          Link controls
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => setDialog("link")}>
                          <Icon name="link" className="size-4 text-text-subtle" />
                          Link a record
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => setDialog("review")}>
                          <Icon name="eye" className="size-4 text-text-subtle" />
                          Mark reviewed
                        </DropdownMenuItem>
                        {!open ? (
                          <DropdownMenuItem onSelect={() => setDialog("accept")}>
                            <Icon name="scales" className="size-4 text-text-subtle" />
                            Request acceptance
                          </DropdownMenuItem>
                        ) : null}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem variant="danger" onSelect={() => setDialog("close")}>
                          <Icon name="archive" className="size-4" />
                          Close risk
                        </DropdownMenuItem>
                      </>
                    ) : (
                      <DropdownMenuItem onSelect={() => setDialog("reopen")}>
                        <Icon name="activity" className="size-4 text-text-subtle" />
                        Reopen risk
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : null}
            </>
          ) : (
            <TraceButton type="risk" id={risk.id} />
          )
        }
      />

      <TabStrip
        label="Risk sections"
        items={tabs}
        value={tab}
        onSelect={(id) => goTo(id as TabId)}
        className="mt-1"
        variant="bar"
        inline
      />

      <div className="mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0 space-y-4">
          {tab === "overview" ? (
            <OverviewTab risk={risk} register={register} />
          ) : tab === "treatment" ? (
            <TreatmentTab risk={risk} canManage={canManage} onAdd={() => setDialog("action")} />
          ) : tab === "controls" ? (
            <ControlsTab
              risk={risk}
              canManage={canManage}
              onAdd={() => setDialog("controls")}
              onRemove={(id) => removeControl.mutate(id)}
            />
          ) : tab === "links" ? (
            <LinksTab
              risk={risk}
              canManage={canManage}
              onAdd={(type) => {
                setLinkType(type);
                setDialog("link");
              }}
              onRemove={(id) => removeLink.mutate(id)}
            />
          ) : tab === "acceptance" ? (
            <AcceptanceTab
              risk={risk}
              me={me}
              canManage={canManage}
              canApprove={canApprove}
              onRequest={() => setDialog("accept")}
              onDecide={(a) => {
                setTarget(a);
                setDialog("decide");
              }}
              onRevoke={(a) => {
                setTarget(a);
                setDialog("revoke");
              }}
              onWithdraw={(a) => withdraw.mutate(a.id)}
            />
          ) : tab === "history" ? (
            <HistoryTab risk={risk} />
          ) : tab === "assessments" ? (
            <SoonSection
              icon="clipboard"
              title="Risk assessments"
              text="Structured assessments that identify, analyse and sign off risks in cycles."
              items={[
                { icon: "team", title: "RCSA campaigns", text: "Control owners rate design and operating effectiveness." },
                { icon: "workflow", title: "Staged workflow", text: "Scope, identify, analyse, evaluate and treat, with sign off." },
                { icon: "calculator", title: "Quantification", text: "Loss ranges and annual exposure for material risks." },
              ]}
            />
          ) : (
            <SoonSection
              icon="trend"
              title="Key risk indicators"
              text="Measures that warn before this risk materialises."
              items={[
                { icon: "target", title: "Thresholds", text: "Alert above or below a limit you set." },
                { icon: "activity", title: "Measurements", text: "Periodic values with a trend line on the risk." },
                { icon: "bell", title: "Breach alerts", text: "The owner hears first when a threshold breaks." },
              ]}
            />
          )}
        </div>

        <aside className="space-y-4">
          <ScoreCard risk={risk} register={register} />
          <DetailsCard risk={risk} register={register} />
        </aside>
      </div>

      {editing ? (
        <RiskFormDialog
          open={editing}
          onOpenChange={setEditing}
          registers={registersQuery.data ?? []}
          register={register}
          risk={risk}
        />
      ) : null}
      <ControlPickerDialog open={dialog === "controls"} onOpenChange={(o) => setDialog(o ? "controls" : null)} risk={risk} />
      <LinkRecordDialog
        open={dialog === "link"}
        onOpenChange={(o) => setDialog(o ? "link" : null)}
        risk={risk}
        initialType={linkType}
      />
      <ActionDialog open={dialog === "action"} onOpenChange={(o) => setDialog(o ? "action" : null)} risk={risk} />
      <AcceptanceRequestDialog open={dialog === "accept"} onOpenChange={(o) => setDialog(o ? "accept" : null)} risk={risk} />
      <DecisionDialog
        open={dialog === "decide"}
        onOpenChange={(o) => setDialog(o ? "decide" : null)}
        risk={risk}
        acceptance={target}
      />
      <NoteDialog
        open={dialog === "close"}
        onOpenChange={(o) => setDialog(o ? "close" : null)}
        title={`Close ${risk.code}`}
        description="Closed risks stay on record with the reason."
        label="Why it no longer applies"
        confirm="Close risk"
        destructive
        loading={status.isPending}
        onConfirm={(note) => status.mutate({ to: "closed", note })}
      />
      <NoteDialog
        open={dialog === "reopen"}
        onOpenChange={(o) => setDialog(o ? "reopen" : null)}
        title={`Reopen ${risk.code}`}
        description="The risk returns to open."
        label="Why it applies again"
        confirm="Reopen"
        loading={status.isPending}
        onConfirm={(note) => status.mutate({ to: "open", note })}
      />
      <NoteDialog
        open={dialog === "review"}
        onOpenChange={(o) => setDialog(o ? "review" : null)}
        title="Mark reviewed"
        description="Records the review and schedules the next one."
        label="Review note"
        required={false}
        confirm="Record review"
        withDate={{ label: "Next review", value: isoDate(register.review_cadence_days) }}
        loading={review.isPending}
        onConfirm={(note, date) => review.mutate({ note, date })}
      />
      <NoteDialog
        open={dialog === "revoke"}
        onOpenChange={(o) => setDialog(o ? "revoke" : null)}
        title="Revoke acceptance"
        description="The risk reopens immediately."
        label="Why it is revoked"
        confirm="Revoke"
        destructive
        loading={revoke.isPending}
        onConfirm={(note) => revoke.mutate(note)}
      />
    </div>
  );
}

// -- shared chrome -------------------------------------------------------------------

function Panel({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-surface-primary p-5", className)}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function Prose({ label, value, icon }: { label: string; value: string | null; icon: Parameters<typeof Icon>[0]["name"] }) {
  return (
    <div className="rounded-lg bg-surface-sunken p-4">
      <p className="mb-1.5 flex items-center gap-1.5 text-label-sm text-text-secondary">
        <Icon name={icon} className="size-3.5 text-text-subtle" />
        {label}
      </p>
      {value ? (
        <p className="whitespace-pre-line text-body-sm text-text-primary">{value}</p>
      ) : (
        <p className="text-body-sm text-text-faint">Not recorded</p>
      )}
    </div>
  );
}

// -- tabs ------------------------------------------------------------------------------

function OverviewTab({ risk, register }: { risk: RiskDetail; register: Register }) {
  const flags = risk.attention;
  return (
    <>
      {flags.length ? (
        <div className="flex flex-wrap gap-2">
          {flags.map((a) => (
            <span
              key={a}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-label-sm",
                ATTENTION_META[a].family === "danger"
                  ? "bg-status-danger-bg text-status-danger-text"
                  : ATTENTION_META[a].family === "warning"
                    ? "bg-status-warning-bg text-status-warning-text"
                    : "bg-action-accent-tint text-action-accent",
              )}
            >
              <Icon name={ATTENTION_META[a].icon} className="size-3.5" />
              {ATTENTION_META[a].label}
            </span>
          ))}
        </div>
      ) : null}
      <Panel title="Description">
        {risk.description ? (
          <p className="whitespace-pre-line text-body-md text-text-primary">{risk.description}</p>
        ) : (
          <p className="text-body-sm text-text-faint">No description yet.</p>
        )}
      </Panel>
      <div className="grid gap-3 md:grid-cols-2">
        <Prose label="Root cause" value={risk.root_cause} icon="branch" />
        <Prose label="Consequences" value={risk.consequences} icon="lightning" />
      </div>
      <Prose label="Recommendations" value={risk.recommendations} icon="sparkle" />
      <CustomValues values={risk.custom_fields ?? {}} />
      <Panel title="Where it sits" action={<AppetitePill status={risk.appetite_status} />}>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="mb-2 text-label-sm text-text-secondary">Inherent</p>
            <Heatmap
              compact
              likelihoodScale={register.likelihood_scale}
              impactScale={register.impact_scale}
              formula={register.scoring_formula}
              bands={register.severity_bands}
              markers={
                risk.inherent_likelihood && risk.inherent_impact
                  ? [{ likelihood: risk.inherent_likelihood, impact: risk.inherent_impact, label: "I" }]
                  : []
              }
            />
          </div>
          <div>
            <p className="mb-2 text-label-sm text-text-secondary">Residual</p>
            <Heatmap
              compact
              likelihoodScale={register.likelihood_scale}
              impactScale={register.impact_scale}
              formula={register.scoring_formula}
              bands={register.severity_bands}
              markers={
                risk.residual_likelihood && risk.residual_impact
                  ? [{ likelihood: risk.residual_likelihood, impact: risk.residual_impact, label: "R" }]
                  : []
              }
            />
          </div>
        </div>
      </Panel>
    </>
  );
}

function TreatmentTab({ risk, canManage, onAdd }: { risk: RiskDetail; canManage: boolean; onAdd: () => void }) {
  const done = risk.actions.filter((a) => a.status === "closed").length;
  const pct = risk.actions.length ? Math.round((done / risk.actions.length) * 100) : 0;
  return (
    <>
      <Panel title="Decision">
        <div className="grid gap-2 sm:grid-cols-4">
          {(Object.keys(TREATMENT_META) as (keyof typeof TREATMENT_META)[]).map((t) => {
            const on = risk.treatment === t;
            return (
              <div
                key={t}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg border px-3 py-2.5",
                  on ? "border-action-accent bg-action-accent-tint" : "border-border bg-surface-primary opacity-60",
                )}
              >
                <span
                  className={cn(
                    "grid size-8 place-items-center rounded-md",
                    on ? "bg-action-accent text-white" : "bg-surface-sunken text-text-subtle",
                  )}
                >
                  <Icon name={TREATMENT_META[t].icon} className="size-4" />
                </span>
                <span className="text-label-md text-text-primary">{TREATMENT_META[t].label}</span>
              </div>
            );
          })}
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_14rem]">
          <Prose label="Treatment plan" value={risk.treatment_plan} icon="checklist" />
          <div className="rounded-lg bg-surface-sunken p-4">
            <p className="text-label-sm text-text-secondary">Treatment due</p>
            <p className="mt-1 text-body-md font-semibold text-text-primary">{fmtDate(risk.treatment_due_on)}</p>
            {risk.attention.includes("treatment_overdue") ? (
              <p className="mt-1 text-caption font-semibold text-status-danger-text">Overdue</p>
            ) : null}
          </div>
        </div>
      </Panel>
      <Panel
        title="Actions"
        action={
          canManage && risk.status !== "closed" ? (
            <Button size="sm" variant="secondary" onClick={onAdd}>
              <Icon name="plus" className="size-4" />
              Add action
            </Button>
          ) : null
        }
      >
        {risk.actions.length === 0 ? (
          <EmptyState icon="checklist" title="No actions yet" description="Each action becomes a task with an owner and a due date." />
        ) : (
          <>
            <div className="mb-3 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                <div className="h-full rounded-full bg-status-success-base" style={{ width: `${pct}%` }} />
              </div>
              <span className="tabular text-caption text-text-subtle">
                {done} of {risk.actions.length} done
              </span>
            </div>
            <ul className="divide-y divide-border rounded-lg border border-border">
              {risk.actions.map((a) => {
                const due = daysUntil(a.due_at);
                return (
                  <li key={a.task_id}>
                    <Link to={`/tasks/${a.task_id}`} className="flex items-center gap-3 px-3.5 py-3 hover:bg-surface-hover">
                      <Icon
                        name={a.status === "closed" ? "check" : "checklist"}
                        className={cn("size-4 shrink-0", a.status === "closed" ? "text-status-success-base" : "text-text-subtle")}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body-sm font-semibold text-text-primary">{a.title}</span>
                        <span className="block truncate text-caption text-text-subtle">
                          {[a.code, a.owner_name ?? "No owner", humanise(a.priority)].join(" · ")}
                        </span>
                      </span>
                      <span
                        className={cn(
                          "tabular shrink-0 text-caption",
                          due !== null && due < 0 && a.status !== "closed" ? "font-semibold text-status-danger-text" : "text-text-subtle",
                        )}
                      >
                        {a.due_at ? fmtDate(a.due_at) : "No due date"}
                      </span>
                      <StatusPill status={a.status === "closed" ? "success" : "progress"} label={humanise(a.status)} kind="inline" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </Panel>
    </>
  );
}

function ControlsTab({
  risk,
  canManage,
  onAdd,
  onRemove,
}: {
  risk: RiskDetail;
  canManage: boolean;
  onAdd: () => void;
  onRemove: (id: string) => void;
}) {
  return (
    <Panel
      title="Mitigating controls"
      action={
        <div className="flex items-center gap-2">
          <Tooltip content="Failing linked controls will flag this risk for review">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-sunken px-2.5 py-1 text-caption text-text-subtle">
              <Icon name="pulse" className="size-3.5" />
              Continuous monitoring
              <span className="rounded-full bg-action-accent-tint px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-action-accent">
                Soon
              </span>
            </span>
          </Tooltip>
          {canManage && risk.status !== "closed" ? (
            <Button size="sm" variant="secondary" onClick={onAdd}>
              <Icon name="plus" className="size-4" />
              Link controls
            </Button>
          ) : null}
        </div>
      }
    >
      {risk.controls.length === 0 ? (
        <EmptyState
          icon="controls"
          title="No linked control"
          description="A risk with no control is flagged until one is linked."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {risk.controls.map((c) => (
            <li key={c.id} className="flex items-center gap-3 px-3.5 py-3">
              <span className="tabular w-16 shrink-0 text-caption font-semibold text-text-subtle">{c.code}</span>
              <Link to={`/controls/${c.id}`} className="min-w-0 flex-1">
                <span className="block truncate text-body-sm font-semibold text-text-primary hover:underline">{c.name}</span>
                <span className="block truncate text-caption text-text-subtle">{c.category}</span>
              </Link>
              {c.disabled ? <Badge variant="neutral">Retired</Badge> : null}
              <StatusPill
                status={c.status === "implemented" || c.status === "passing" ? "success" : c.status === "failing" ? "danger" : "pending"}
                label={humanise(c.status)}
                kind="inline"
              />
              {canManage ? (
                <Button size="icon-sm" variant="ghost" aria-label={`Unlink ${c.code}`} onClick={() => onRemove(c.id)}>
                  <Icon name="x" className="size-4" />
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function LinksTab({
  risk,
  canManage,
  onAdd,
  onRemove,
}: {
  risk: RiskDetail;
  canManage: boolean;
  onAdd: (type: LinkType) => void;
  onRemove: (linkId: string) => void;
}) {
  const types = Object.keys(LINK_META) as LinkType[];
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {types.map((type) => {
        const rows = risk.links.filter((l) => l.target_type === type);
        const meta = LINK_META[type];
        return (
          <section key={type} className="rounded-lg border border-border bg-surface-primary p-4">
            <div className="mb-2.5 flex items-center justify-between gap-2">
              <h3 className="flex items-center gap-2 text-label-md text-text-primary">
                <span className="grid size-7 place-items-center rounded-md bg-surface-sunken">
                  <Icon name={meta.icon} className="size-3.5 text-text-subtle" />
                </span>
                {meta.plural}
                <span className="tabular text-caption text-text-subtle">{rows.length}</span>
              </h3>
              {canManage && risk.status !== "closed" ? (
                <Button size="icon-sm" variant="ghost" aria-label={`Link ${meta.label}`} onClick={() => onAdd(type)}>
                  <Icon name="plus" className="size-4" />
                </Button>
              ) : null}
            </div>
            {rows.length === 0 ? (
              <p className="py-2 text-caption text-text-faint">None linked</p>
            ) : (
              <ul className="space-y-1">
                {rows.map((l) => (
                  <li key={l.link_id} className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-surface-hover">
                    <Link to={meta.href(l.target_id)} className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm text-text-primary">
                        {l.code ? <span className="mr-1.5 text-caption font-semibold text-text-subtle">{l.code}</span> : null}
                        {l.title}
                      </span>
                      <span className="block truncate text-caption capitalize text-text-subtle">
                        {[l.detail, l.status].filter(Boolean).join(" · ").replace(/_/g, " ")}
                      </span>
                    </Link>
                    {canManage ? (
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        className="opacity-0 group-hover:opacity-100"
                        aria-label={`Remove ${l.title}`}
                        onClick={() => onRemove(l.link_id)}
                      >
                        <Icon name="x" className="size-3.5" />
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}

function AcceptanceTab({
  risk,
  me,
  canManage,
  canApprove,
  onRequest,
  onDecide,
  onRevoke,
  onWithdraw,
}: {
  risk: RiskDetail;
  me: string | null;
  canManage: boolean;
  canApprove: boolean;
  onRequest: () => void;
  onDecide: (a: Acceptance) => void;
  onRevoke: (a: Acceptance) => void;
  onWithdraw: (a: Acceptance) => void;
}) {
  const open = risk.acceptances.find((a) => a.status === "pending" || a.status === "active");
  return (
    <>
      <Panel
        title="Risk acceptance"
        action={
          canManage && !open && risk.status !== "closed" ? (
            <Button size="sm" variant="secondary" onClick={onRequest}>
              <Icon name="scales" className="size-4" />
              Request acceptance
            </Button>
          ) : null
        }
      >
        {risk.acceptances.length === 0 ? (
          <EmptyState
            icon="scales"
            title="Not accepted"
            description="Accepting a risk needs an approver, a reason and an expiry. It reopens when the expiry passes."
          />
        ) : (
          <ol className="space-y-3">
            {risk.acceptances.map((a) => {
              const left = daysUntil(a.expires_on);
              return (
                <li key={a.id} className="rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AcceptanceStatus acceptance={a} />
                      <span className="text-caption text-text-subtle">
                        Until {fmtDate(a.expires_on)}
                        {a.status === "active" && left !== null ? ` · ${left} days left` : ""}
                      </span>
                    </div>
                    <div className="flex gap-1.5">
                      {a.status === "pending" && canApprove && a.approver?.membership_id === me ? (
                        <Button size="sm" variant="success-2" onClick={() => onDecide(a)}>
                          Decide
                        </Button>
                      ) : null}
                      {a.status === "pending" && a.requested_by?.membership_id === me ? (
                        <Button size="sm" variant="ghost" onClick={() => onWithdraw(a)}>
                          Withdraw
                        </Button>
                      ) : null}
                      {a.status === "active" && canApprove ? (
                        <Button size="sm" variant="ghost" onClick={() => onRevoke(a)}>
                          Revoke
                        </Button>
                      ) : null}
                    </div>
                  </div>
                  <p className="mt-2.5 whitespace-pre-line text-body-sm text-text-primary">{a.rationale}</p>
                  <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-caption text-text-subtle">
                    <span className="inline-flex items-center gap-1.5">
                      <Avatar name={a.requested_by?.name ?? "?"} seed={a.requested_by?.membership_id ?? "x"} size="sm" />
                      Requested by {a.requested_by?.name ?? "former member"}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <Avatar name={a.approver?.name ?? "?"} seed={a.approver?.membership_id ?? "y"} size="sm" />
                      Approver {a.approver?.name ?? "former member"}
                    </span>
                    {a.residual_score_at_request !== null ? <span>Score at request {a.residual_score_at_request}</span> : null}
                  </div>
                  {a.decision_note || a.revoke_reason ? (
                    <p className="mt-2.5 rounded-md bg-surface-sunken px-3 py-2 text-body-sm text-text-secondary">
                      {a.revoke_reason ?? a.decision_note}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ol>
        )}
      </Panel>
      <div className="flex items-center justify-between rounded-lg border border-border bg-surface-primary px-4 py-3">
        <span className="flex items-center gap-2 text-label-sm text-text-secondary">
          <Icon name="workflow" className="size-4 text-text-subtle" />
          Multi step approval workflows
        </span>
        <span className="rounded-full bg-action-accent-tint px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-action-accent">
          Soon
        </span>
      </div>
    </>
  );
}

function HistoryTab({ risk }: { risk: RiskDetail }) {
  return (
    <Panel title="History">
      {risk.history.length === 0 ? (
        <p className="text-body-sm text-text-subtle">Nothing recorded yet.</p>
      ) : (
        <ol className="relative space-y-4 pl-6 before:absolute before:bottom-2 before:left-[11px] before:top-2 before:w-px before:bg-border">
          {risk.history.map((e) => (
            <li key={e.id} className="relative">
              <span className="absolute -left-6 grid size-6 place-items-center rounded-full border border-border bg-surface-primary">
                <Icon name={EVENT_ICON[e.kind] ?? "activity"} className="size-3 text-text-subtle" />
              </span>
              <p className="text-body-sm text-text-primary">
                <span className="font-semibold">{EVENT_LABEL[e.kind] ?? humanise(e.kind)}</span>
                {e.from_value || e.to_value ? (
                  <span className="text-text-secondary">
                    {" "}
                    {e.from_value ? `${humanise(e.from_value)} to ` : ""}
                    {humanise(e.to_value)}
                  </span>
                ) : null}
              </p>
              {e.note ? <p className="mt-0.5 text-body-sm text-text-secondary">{e.note}</p> : null}
              <p className="mt-0.5 text-caption text-text-subtle">
                {e.actor_name ?? "Verity"} · {new Date(e.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

// -- side rail ------------------------------------------------------------------------------

function ScoreCard({ risk, register }: { risk: RiskDetail; register: Register }) {
  const bands = register.severity_bands;
  const rows = [
    { label: "Inherent", l: risk.inherent_likelihood, i: risk.inherent_impact, score: risk.inherent_score, band: risk.inherent_band },
    { label: "Residual", l: risk.residual_likelihood, i: risk.residual_impact, score: risk.residual_score, band: risk.residual_band },
  ];
  const drop =
    risk.inherent_score !== null && risk.residual_score !== null ? risk.inherent_score - risk.residual_score : null;
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-4">
      <h2 className="mb-3 text-label-md text-text-primary">Score</h2>
      <div className="space-y-2.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-3">
            {r.score !== null ? (
              <ScoreChip score={r.score} bands={bands} size="lg" />
            ) : (
              <span className="grid size-11 shrink-0 place-items-center rounded-md border border-border bg-surface-sunken text-text-faint">
                <Icon name="gauge" className="size-4" />
              </span>
            )}
            <div className="min-w-0">
              <p className="text-label-sm text-text-secondary">{r.label}</p>
              {r.l && r.i ? (
                <p className="truncate text-caption text-text-subtle">
                  {register.likelihood_scale[r.l - 1]?.label} × {register.impact_scale[r.i - 1]?.label}
                </p>
              ) : (
                <p className="text-caption text-text-faint">Not assessed</p>
              )}
            </div>
            {r.band ? (
              <span className={cn("ml-auto text-label-sm", BAND_TONE[r.band].text)}>
                {bands.find((b) => b.key === r.band)?.label}
              </span>
            ) : null}
          </div>
        ))}
      </div>
      {drop !== null && drop > 0 ? (
        <p className="mt-3 flex items-center gap-1.5 rounded-md bg-status-success-bg px-2.5 py-1.5 text-caption font-semibold text-status-success-text">
          <Icon name="arrowdown" className="size-3.5" />
          Controls reduce the score by {drop}
        </p>
      ) : null}
    </section>
  );
}

function DetailsCard({ risk, register }: { risk: RiskDetail; register: Register }) {
  const review = daysUntil(risk.next_review_on);
  const rows: [string, ReactNode][] = [
    ["Register", `${register.name} · ${REGISTER_TYPE_LABEL[register.register_type]}`],
    ["Category", [risk.category_name, risk.sub_category_name].filter(Boolean).join(" · ")],
    [
      "Business owner",
      risk.owner ? (
        <span className="inline-flex items-center gap-1.5">
          <Avatar name={risk.owner.name} seed={risk.owner.membership_id} size="sm" />
          {risk.owner.name}
        </span>
      ) : (
        <span className="text-text-faint">No owner</span>
      ),
    ],
    ["Business unit", risk.department_name ?? <span className="text-text-faint">Not set</span>],
    [
      "Next review",
      <span className={cn(review !== null && review < 0 && risk.status !== "closed" && "font-semibold text-status-danger-text")}>
        {fmtDate(risk.next_review_on)}
      </span>,
    ],
    ["Last reviewed", risk.last_reviewed_at ? fmtDate(risk.last_reviewed_at) : <span className="text-text-faint">Never</span>],
    [
      "Source",
      risk.template_code ? `${ORIGIN_LABEL[risk.origin]} · ${risk.template_code}` : ORIGIN_LABEL[risk.origin] ?? risk.origin,
    ],
    ["Created", `${fmtDate(risk.created_at)}${risk.created_by_name ? ` by ${risk.created_by_name}` : ""}`],
  ];
  if (risk.status === "closed" && risk.closure_justification) {
    rows.push(["Closed because", risk.closure_justification]);
  }
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-4">
      <h2 className="mb-3 text-label-md text-text-primary">Details</h2>
      <dl className="space-y-2.5">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-caption text-text-subtle">{label}</dt>
            <dd className="mt-0.5 text-body-sm text-text-primary">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
