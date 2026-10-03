import type {
  DocumentKpis,
  DocumentRow,
  EvidenceGap,
  EvidenceRow,
  FrameworkSummary,
  OwnedControl,
  PendingApproval,
  PendingCampaign,
  PolicySummary,
  RiskBand,
  TaskRow,
} from "./types";

/**
 * The dashboard's arithmetic, kept apart from React so it reads (and can be
 * checked) on its own. Nothing here fetches or renders.
 */

export function pct(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((part / whole) * 100);
}

export type RingTone = "success" | "warning" | "danger";

/** The same bands the posture page colours coverage with. */
export function ringToneFor(percent: number): RingTone {
  if (percent >= 80) return "success";
  if (percent >= 40) return "warning";
  return "danger";
}

const capitalise = (word: string) => word.charAt(0).toUpperCase() + word.slice(1);

// -- frameworks and policies --------------------------------------------------

/**
 * The frameworks the workspace has adopted, read off its live controls: a
 * framework appears only when at least one live control answers to it, so a
 * workspace never shows a framework it has not taken on. A control mapped to
 * two frameworks counts toward both.
 */
export function summarizeFrameworks(
  rows: { status: string; frameworks: string[] }[],
): FrameworkSummary[] {
  const byName = new Map<string, FrameworkSummary>();
  for (const row of rows) {
    if (row.status === "disabled") continue;
    for (const name of row.frameworks) {
      const framework = byName.get(name) ?? { name, controls: 0, implemented: 0, inProgress: 0 };
      framework.controls += 1;
      if (row.status === "implemented") framework.implemented += 1;
      else if (row.status === "in_progress") framework.inProgress += 1;
      byName.set(name, framework);
    }
  }
  return [...byName.values()].sort((a, b) => b.controls - a.controls || a.name.localeCompare(b.name));
}

export function summarizePolicies(rows: DocumentRow[], kpis: DocumentKpis): PolicySummary {
  const live = rows.filter((row) => row.lifecycle !== "archived");
  const rates = live.map((row) => row.attestation_pct).filter((rate): rate is number => rate !== null);
  return {
    total: live.length,
    published: live.filter((row) => row.lifecycle === "published").length,
    renewalOverdue: kpis.renewal_past_due,
    needsApproval: kpis.needs_approval,
    acknowledged: rates.length ? Math.round(rates.reduce((sum, rate) => sum + rate, 0) / rates.length) : null,
  };
}

// -- risk heatmap -------------------------------------------------------------

/** The highest band a score reaches. Bands arrive in ascending order. */
export function bandFor(bands: RiskBand[], score: number): RiskBand | null {
  let hit: RiskBand | null = null;
  for (const band of bands) if (band.min_score <= score) hit = band;
  return hit;
}

export type HeatCell = { key: string; count: number; band: string };

/**
 * A register's counts laid out for drawing: highest likelihood on the top row,
 * highest impact on the right, each cell carrying the band its score falls in
 * (likelihood times impact, as the risk module scores it).
 */
export function heatCells(grid: number[][], bands: RiskBand[]): { cols: number; cells: HeatCell[] } {
  const cols = grid[0]?.length ?? 0;
  const cells: HeatCell[] = [];
  for (let likelihood = grid.length - 1; likelihood >= 0; likelihood--) {
    for (let impact = 0; impact < cols; impact++) {
      cells.push({
        key: `${likelihood}-${impact}`,
        count: grid[likelihood]?.[impact] ?? 0,
        band: bandFor(bands, (likelihood + 1) * (impact + 1))?.key ?? "low",
      });
    }
  }
  return { cols, cells };
}

// -- days ---------------------------------------------------------------------

const DAY_MS = 86_400_000;

/** Today as a calendar date in the reader's time zone, "2026-10-03". */
export function localDay(now: Date): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/**
 * Whole days from today to a due date: negative is overdue. A due date is a
 * calendar date (the task form stores midnight UTC of the day picked), so both
 * sides are compared as dates and the clock never makes a task due "yesterday".
 */
export function dayDelta(iso: string, today: string): number {
  return Math.round((Date.parse(iso.slice(0, 10)) - Date.parse(today)) / DAY_MS);
}

export type DueTone = "overdue" | "today" | "later";

function dueOf(delta: number): { label: string; tone: DueTone } {
  if (delta < 0) return { label: `Overdue ${-delta}d`, tone: "overdue" };
  if (delta === 0) return { label: "Due today", tone: "today" };
  return { label: delta === 1 ? "Tomorrow" : `in ${delta}d`, tone: "later" };
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

// -- my day -------------------------------------------------------------------

export type QueueKind = "task" | "approval" | "acknowledge" | "evidence";

export type QueueItem = {
  key: string;
  kind: QueueKind;
  title: string;
  detail: string;
  due: { label: string; tone: DueTone } | null;
  /** The record this row opens. */
  to: string;
  action: string;
  rank: number;
  sortDay: string;
};

/** Sorts after every real date. */
const NO_DAY = "9999-12-31";

/**
 * Overdue first, then due today, then what is waiting on the person (approvals
 * and acknowledgements block somebody else), then dated work still ahead, then
 * assigned work with no date, and last the controls missing evidence (a standing
 * gap rather than an assignment).
 */
const RANK = { overdue: 0, today: 1, waiting: 2, ahead: 3, undated: 4, gap: 5 } as const;

/** Overdue and due today outrank everything; otherwise the item's own rank applies. */
function rankOf(delta: number | null, otherwise: number): number {
  if (delta !== null && delta < 0) return RANK.overdue;
  if (delta === 0) return RANK.today;
  return otherwise;
}

export function buildQueue(input: {
  tasks?: TaskRow[];
  approvals?: PendingApproval[];
  campaigns?: PendingCampaign[];
  gaps?: EvidenceGap[];
  today: string;
}): QueueItem[] {
  const { today } = input;
  const items: QueueItem[] = [];

  for (const task of input.tasks ?? []) {
    const delta = task.due_at ? dayDelta(task.due_at, today) : null;
    items.push({
      key: `task:${task.id}`,
      kind: "task",
      title: task.title,
      detail: `${task.code} · ${capitalise(task.priority)} priority`,
      due: delta === null ? null : dueOf(delta),
      to: `/tasks/${task.id}`,
      action: "Open",
      rank: rankOf(delta, delta === null ? RANK.undated : RANK.ahead),
      sortDay: task.due_at?.slice(0, 10) ?? NO_DAY,
    });
  }

  for (const approval of input.approvals ?? []) {
    items.push({
      key: `approval:${approval.document_id}:${approval.tier}`,
      kind: "approval",
      title: approval.document_title,
      detail: `${approval.document_code} · Tier ${approval.tier} review`,
      due: null,
      to: `/documents/${approval.document_id}/approvals/${approval.tier}`,
      action: "Review",
      rank: RANK.waiting,
      sortDay: NO_DAY,
    });
  }

  for (const campaign of input.campaigns ?? []) {
    const delta = campaign.due_at ? dayDelta(campaign.due_at, today) : null;
    items.push({
      key: `campaign:${campaign.id}`,
      kind: "acknowledge",
      title: campaign.title,
      detail: `${campaign.document_code} · Asked by ${campaign.created_by_name}`,
      due: delta === null ? null : dueOf(delta),
      to: `/documents/campaigns/${campaign.id}`,
      action: "Read and sign",
      rank: rankOf(delta, RANK.waiting),
      sortDay: campaign.due_at?.slice(0, 10) ?? NO_DAY,
    });
  }

  for (const gap of input.gaps ?? []) {
    items.push({
      key: `evidence:${gap.id}`,
      kind: "evidence",
      title: gap.name,
      detail: `${gap.code} · ${gap.reason}`,
      due: null,
      to: `/controls/${gap.id}`,
      action: "Add evidence",
      rank: RANK.gap,
      sortDay: NO_DAY,
    });
  }

  return items.sort(
    (a, b) => a.rank - b.rank || a.sortDay.localeCompare(b.sortDay) || a.title.localeCompare(b.title),
  );
}

export function countTasks(tasks: TaskRow[], today: string): { overdue: number; dueToday: number } {
  let overdue = 0;
  let dueToday = 0;
  for (const task of tasks) {
    if (!task.due_at) continue;
    const delta = dayDelta(task.due_at, today);
    if (delta < 0) overdue += 1;
    else if (delta === 0) dueToday += 1;
  }
  return { overdue, dueToday };
}

/**
 * Owned controls with no evidence that still counts. The test is the readiness
 * rule the backend applies: an item counts unless it was rejected or its
 * renewal date has passed. A control not applicable to the workspace needs none.
 */
export function evidenceGaps(controls: OwnedControl[], evidence: EvidenceRow[]): EvidenceGap[] {
  const counting = new Set<string>();
  const attached = new Set<string>();
  for (const item of evidence) {
    for (const controlId of item.control_ids) {
      attached.add(controlId);
      if (item.review_status !== "rejected" && item.freshness !== "stale") counting.add(controlId);
    }
  }
  return controls
    .filter((control) => control.status !== "not_applicable" && !counting.has(control.id))
    .map((control) => ({
      ...control,
      reason: attached.has(control.id) ? "Evidence expired or rejected" : "No evidence yet",
    }));
}

export type Deadline = {
  key: string;
  day: string;
  month: string;
  title: string;
  detail: string;
  delta: number;
  to: string;
};

/** The next dated things on the person's plate: task due dates and the
 *  acknowledgements that carry one. */
export function upcomingDeadlines(
  tasks: TaskRow[],
  campaigns: PendingCampaign[],
  today: string,
  limit = 5,
): Deadline[] {
  const dated: { sortDay: string; deadline: Deadline }[] = [];
  const add = (key: string, iso: string, title: string, label: string, to: string) => {
    const delta = dayDelta(iso, today);
    if (delta < 0) return;
    const sortDay = iso.slice(0, 10);
    const [, month, day] = sortDay.split("-");
    dated.push({
      sortDay,
      deadline: {
        key,
        day,
        month: MONTHS[Number(month) - 1] ?? "",
        title,
        detail: `${label} · ${dueOf(delta).label}`,
        delta,
        to,
      },
    });
  };
  for (const task of tasks) {
    if (task.due_at) add(`task:${task.id}`, task.due_at, task.title, task.code, `/tasks/${task.id}`);
  }
  for (const campaign of campaigns) {
    if (campaign.due_at) {
      add(`campaign:${campaign.id}`, campaign.due_at, campaign.title, "Acknowledge", `/documents/campaigns/${campaign.id}`);
    }
  }
  return dated
    .sort((a, b) => a.sortDay.localeCompare(b.sortDay) || a.deadline.title.localeCompare(b.deadline.title))
    .slice(0, limit)
    .map((entry) => entry.deadline);
}

export type SlaClock = {
  key: string;
  code: string;
  label: string;
  /** How much of the window has been used, 0 to 1. */
  share: number;
  tone: "danger" | "warning" | "success";
  overdue: boolean;
  to: string;
};

function spanLabel(ms: number): string {
  const hours = Math.floor(Math.abs(ms) / 3_600_000);
  if (hours < 1) return "under 1h";
  return hours < 48 ? `${hours}h` : `${Math.floor(hours / 24)}d`;
}

/**
 * The person's running SLA clocks, nearest deadline first. A clock is shown
 * with how much of its window is spent, measured from the same start the
 * backend counts from (detected, else created). Paused (blocked) tasks have no
 * clock running and are left out.
 */
export function slaClocks(tasks: TaskRow[], now: number, limit = 6): SlaClock[] {
  const running: { due: number; clock: SlaClock }[] = [];
  for (const task of tasks) {
    if (task.sla_due_at === null || task.sla_state === "paused" || task.sla_state === "none") continue;
    const due = Date.parse(task.sla_due_at);
    const start = Date.parse(task.detected_at ?? task.created_at);
    const share = due > start ? Math.min(1, Math.max(0, (now - start) / (due - start))) : 1;
    const overdue = due < now;
    running.push({
      due,
      clock: {
        key: `sla:${task.id}`,
        code: task.code,
        label: overdue ? `${spanLabel(now - due)} overdue` : `${spanLabel(due - now)} left`,
        share,
        tone: overdue ? "danger" : share >= 0.75 ? "warning" : "success",
        overdue,
        to: `/tasks/${task.id}`,
      },
    });
  }
  return running
    .sort((a, b) => a.due - b.due)
    .slice(0, limit)
    .map((entry) => entry.clock);
}
