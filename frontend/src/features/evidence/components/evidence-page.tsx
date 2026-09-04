import { useMemo, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  ColumnPicker,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PageHeader,
  SearchInput,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TextField,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
  useToast,
  type ColumnDef,
} from "@/components/ui";
import { Donut } from "@/features/dashboard/donut";
import { complianceApi, controlsApi, evidenceApi, iamApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { getAccessToken } from "@/lib/auth/session";
import type {
  Control,
  Evidence,
  EvidenceFreshness,
  ReviewStatus,
} from "@/lib/api/types";
import { ControlPicker, type ControlGroup } from "./control-picker";

/** DS §6.1 — freshness maps to a status family once, here, so every surface
 *  renders the same word the same way. */
const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
};

const FRESHNESS_ORDER: EvidenceFreshness[] = [
  "current",
  "aging",
  "stale",
  "no_expiry",
];

/** Review status → a status family + word, mapped once so every surface agrees.
 *  Pending gets its own family (an action item), approved reads as good, and a
 *  rejection reads as a problem to fix. */
const REVIEW_META: Record<
  ReviewStatus,
  { label: string; family: "success" | "danger" | "pending" }
> = {
  pending: { label: "Pending review", family: "pending" },
  approved: { label: "Approved", family: "success" },
  rejected: { label: "Rejected", family: "danger" },
};

const REVIEW_ORDER: ReviewStatus[] = ["pending", "approved", "rejected"];

/** The optional register columns. Evidence (identity) and the row-actions cell
 *  are not here: a row you cannot name or act on is not a row. Labels match the
 *  TH text exactly so the picker and the header cannot drift. */
const EVIDENCE_COLUMNS = [
  { key: "type", label: "Type" },
  { key: "controls", label: "Controls" },
  { key: "owner", label: "Owner" },
  { key: "renewal", label: "Renewal" },
  { key: "freshness", label: "Freshness" },
  { key: "review", label: "Review" },
] as const satisfies readonly ColumnDef<string>[];

/** The freshness families as solid fills, for the overview bar and dots.
 *  Colour here is status (fresh / expiring / expired), which the DS allows. */
const FRESHNESS_FILL: Record<EvidenceFreshness, string> = {
  current: "rgb(var(--color-status-success-base))",
  aging: "rgb(var(--color-status-warning-base))",
  stale: "rgb(var(--color-status-danger-base))",
  no_expiry: "rgb(var(--color-status-neutral-base))",
};

/** Whole days from today to a yyyy-mm-dd date; negative means overdue. Parsed
 *  from the parts so a timezone never shifts the day across a boundary. */
function daysSince(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const then = Date.UTC(y, m - 1, d);
  const now = new Date();
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.max(0, Math.round((today - then) / 86_400_000));
}


/** A compact ring for the coverage snapshot. */
function MiniRing({
  value,
  total,
  color,
  label,
}: {
  value: number;
  total: number;
  color: string;
  label: string;
}) {
  const percent = total === 0 ? 0 : Math.round((value / total) * 100);
  return (
    <div className="flex flex-col items-center gap-1.5 text-center">
      <Donut
        size={72}
        stroke={9}
        segments={[
          { value, color },
          { value: Math.max(total - value, 0), color: "transparent" },
        ]}
      >
        <span className="font-display text-body-lg tabular font-bold text-text-primary">
          {percent}%
        </span>
      </Donut>
      <span className="text-caption text-text-subtle">{label}</span>
    </div>
  );
}

/**
 * The evidence dashboard: one compact row — how fresh the library is, what kinds
 * of artefact it holds, and how much of the control set it covers. All computed
 * from the already-loaded list, so there is no second request. The freshness
 * legend and the type bars filter the table below.
 */
function EvidenceOverview({
  items,
  controlsTotal,
  onPickFreshness,
}: {
  items: Evidence[];
  /** null when the control list could not be loaded. */
  controlsTotal: number | null;
  onPickFreshness: (state: EvidenceFreshness) => void;
}) {
  const total = items.length;
  const counts = FRESHNESS_ORDER.reduce<Record<string, number>>((acc, state) => {
    acc[state] = items.filter((i) => i.freshness === state).length;
    return acc;
  }, {});
  const percentOf = (n: number) =>
    total === 0 ? 0 : Math.round((n / total) * 100);

  // Group by owner; the unassigned bucket sorts last, since it is context, not
  // a person. Membership id is the key so two people who share a name stay apart.
  const ownerMap = new Map<
    string,
    { key: string; name: string; count: number; unassigned: boolean }
  >();
  for (const item of items) {
    const key = item.owner_membership_id ?? "__unassigned__";
    const existing = ownerMap.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      ownerMap.set(key, {
        key,
        name: item.owner_name ?? "Unassigned",
        count: 1,
        unassigned: !item.owner_membership_id,
      });
    }
  }
  const owners = [...ownerMap.values()].sort((a, b) =>
    a.unassigned === b.unassigned ? b.count - a.count : a.unassigned ? 1 : -1,
  );
  const ownerMax = Math.max(1, ...owners.map((o) => o.count));

  const controlsWithEvidence = new Set(
    items.flatMap((i) => i.control_ids),
  ).size;
  const owned = items.filter((i) => i.owner_membership_id).length;
  const fresh = counts.current ?? 0;
  const avgAge =
    total === 0
      ? 0
      : Math.round(items.reduce((s, i) => s + daysSince(i.collected_at), 0) / total);

  return (
    <div className="mt-5 grid gap-3 lg:grid-cols-3">
      {/* Evidence freshness */}
      <div className="rounded-lg border border-border bg-surface-primary p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <p className="type-overline">Evidence freshness</p>
          <p className="text-body-sm tabular text-text-subtle">{total} total</p>
        </div>
        <div className="flex items-center gap-4">
          <Donut
            size={104}
            stroke={13}
            segments={FRESHNESS_ORDER.map((state) => ({
              value: counts[state],
              color: FRESHNESS_FILL[state],
            }))}
          >
            <span className="font-display text-numeral-sm tabular text-text-primary">
              {total}
            </span>
            <span className="type-overline">Artifacts</span>
          </Donut>
          <ul className="min-w-0 flex-1 space-y-1">
            {FRESHNESS_ORDER.map((state) => (
              <li key={state}>
                <button
                  type="button"
                  onClick={() => onPickFreshness(state)}
                  className="flex w-full items-center gap-2 rounded-sm px-1 py-0.5 text-left hover:bg-surface-hover"
                >
                  <span
                    className="size-2.5 shrink-0 rounded-[3px]"
                    style={{ backgroundColor: FRESHNESS_FILL[state] }}
                  />
                  <span className="min-w-0 flex-1 truncate text-body-sm text-text-secondary">
                    {FRESHNESS[state].label}
                  </span>
                  <span className="w-6 text-right font-display text-body-md tabular font-semibold text-text-primary">
                    {counts[state]}
                  </span>
                  <span className="w-9 text-right text-caption tabular text-text-subtle">
                    {percentOf(counts[state])}%
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Evidence by owner */}
      <div className="rounded-lg border border-border bg-surface-primary p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <p className="type-overline">Evidence by owner</p>
          <p className="text-body-sm tabular text-text-subtle">{total} items</p>
        </div>
        {owners.length === 0 ? (
          <p className="text-body-sm text-text-subtle">No evidence yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {owners.map((owner) => (
              <li
                key={owner.key}
                className="flex items-center gap-3 px-1 py-0.5"
              >
                {owner.unassigned ? (
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-[10px] font-bold text-text-subtle">
                    ?
                  </span>
                ) : (
                  <Avatar name={owner.name} size="sm" />
                )}
                <span
                  className={cn(
                    "w-24 shrink-0 truncate text-body-sm",
                    owner.unassigned
                      ? "text-status-warning-text"
                      : "text-text-secondary",
                  )}
                >
                  {owner.name}
                </span>
                <span className="h-[7px] flex-1 overflow-hidden rounded-full bg-surface-sunken">
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${(owner.count / ownerMax) * 100}%`,
                      backgroundColor: owner.unassigned
                        ? "rgb(var(--color-status-neutral-base))"
                        : "rgb(var(--color-action-accent))",
                    }}
                  />
                </span>
                <span className="w-6 shrink-0 text-right font-display text-body-md tabular font-semibold text-text-primary">
                  {owner.count}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Coverage snapshot */}
      <div className="rounded-lg border border-border bg-surface-primary p-4">
        <p className="type-overline mb-3">Coverage snapshot</p>
        <div className="flex justify-around">
          <MiniRing
            value={controlsWithEvidence}
            total={controlsTotal ?? 0}
            color="rgb(var(--color-action-accent))"
            label="Controls"
          />
          <MiniRing
            value={fresh}
            total={total}
            color="rgb(var(--color-status-success-base))"
            label="Fresh"
          />
          <MiniRing
            value={owned}
            total={total}
            color="rgb(var(--color-status-pending-base))"
            label="Owned"
          />
        </div>
        <ul className="mt-4 border-t border-border pt-3">
          {[
            [
              "Controls with evidence",
              // null = the control list failed to load. "/ 0" would read as a
              // real denominator and make the ratio a lie.
              `${controlsWithEvidence} / ${controlsTotal ?? "?"}`,
            ],
            ["Evidence with an owner", `${owned} / ${total}`],
            ["Avg. evidence age", `${avgAge} days`],
          ].map(([label, value]) => (
            <li
              key={label}
              className="flex items-center justify-between py-1 text-body-sm"
            >
              <span className="text-text-secondary">{label}</span>
              <span className="tabular font-semibold text-text-primary">
                {value}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
      new Date(`${iso}T00:00:00`),
    );
  } catch {
    return iso;
  }
}


const today = () => new Date().toISOString().slice(0, 10);

/** Download goes through fetch, not a bare href: the API is behind a bearer
 *  token, so an anchor would 401. The object URL is revoked straight after the
 *  click so it does not leak. */
async function downloadEvidence(item: Evidence): Promise<void> {
  const response = await fetch(evidenceApi.downloadUrl(item.id), {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = item.filename ?? item.title;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

// Validity presets → a renewal date computed off the collection date. "Type
// default" stays null so the server fills in the type's own period (D13).
const VALIDITY_OPTIONS = [
  { value: "default", label: "Type default" },
  { value: "30", label: "1 month" },
  { value: "90", label: "Quarterly · 3 months" },
  { value: "180", label: "6 months" },
  { value: "365", label: "1 year" },
  { value: "custom", label: "Custom date…" },
];

// UTC throughout: a YYYY-MM-DD is a civil date, so parsing it as local midnight
// then serialising via toISOString() (UTC) would shift the result back a day on
// any positive-offset timezone. Parse and add in UTC so the date is exact.
function addDays(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

// Picker hint only — the store's magic-byte allow-list is the real gate, so this
// stays in step with what the server will actually keep.
const FILE_ACCEPT =
  ".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.xlsx,.pptx,.txt,.csv,.log,.md,.json";

// Immediate feedback for the obvious-dangerous cases; the server allow-list
// refuses everything off-list regardless, this just fails faster and clearer.
const DANGEROUS_EXT =
  /\.(exe|msi|bat|cmd|com|scr|pif|cpl|dll|sys|drv|vbs|vbe|jse?|mjs|wsf|wsh|ps1|psm1|sh|bash|zsh|jar|apk|app|dmg|pkg|deb|rpm|bin|hta|reg|gadget|lnk)$/i;

export function AddEvidenceDialog({
  open,
  onOpenChange,
  /** Controls to pre-attach. The control detail page passes its own id so the
   *  item is linked where the user started, while still offering the full
   *  picker — this is the same dialog, not a copy of it. */
  presetControlIds,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  presetControlIds?: string[];
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const selfId = principal?.membership_id ?? "";

  const [kind, setKind] = useState<"file" | "link">("file");
  const [title, setTitle] = useState("");
  const [evidenceType, setEvidenceType] = useState("screenshot");
  const [ownerId, setOwnerId] = useState(selfId);
  const [collectedAt, setCollectedAt] = useState(today());
  const [validity, setValidity] = useState("default");
  const [customRenewal, setCustomRenewal] = useState("");
  const [sourceLabel, setSourceLabel] = useState("");
  const [description, setDescription] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [frameworkId, setFrameworkId] = useState("");
  const [controlIds, setControlIds] = useState<string[]>(presetControlIds ?? []);

  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));

  const vocabularyQuery = useQuery({
    queryKey: ["evidence-vocabulary"],
    queryFn: () => evidenceApi.vocabulary(),
  });
  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: open && canReadMembers,
  });
  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
    enabled: open,
  });
  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
    enabled: open,
  });

  const types = vocabularyQuery.data?.types ?? [];

  // No members:read → the owner picker still works, offering just the signed-in
  // user rather than 403-ing on a list they cannot see.
  const members = canReadMembers
    ? (membersQuery.data ?? [])
    : principal
      ? [{ membership_id: selfId, full_name: principal.user.full_name }]
      : [];

  const frameworks = frameworksQuery.data ?? [];
  const activeFrameworkId =
    frameworkId ||
    frameworks.find((framework) => framework.code.toUpperCase().startsWith("SOC"))?.id ||
    frameworks[0]?.id ||
    "";
  const frameworkCode =
    frameworks.find((framework) => framework.id === activeFrameworkId)?.code ?? "SOC2";

  const requirementsQuery = useQuery({
    queryKey: ["requirements", activeFrameworkId],
    queryFn: () => complianceApi.listRequirements(activeFrameworkId),
    enabled: open && Boolean(activeFrameworkId),
  });

  // Criteria-wise hierarchy: controls grouped by the criterion they satisfy
  // (requirement_keys look like "SOC2:CC6.2"), each group labelled with the
  // criterion name. A control mapped to two criteria shows under both — that is
  // its coverage, not a duplicate.
  const groups = useMemo<ControlGroup[]>(() => {
    const controls = controlsQuery.data ?? [];
    const nameFor = new Map(
      (requirementsQuery.data ?? []).map((req) => [req.code, `${req.code} · ${req.name}`]),
    );
    const byCriterion = new Map<string, Control[]>();
    for (const control of controls) {
      const criteria = control.requirement_keys
        .filter((key) => key.startsWith(`${frameworkCode}:`))
        .map((key) => key.slice(frameworkCode.length + 1));
      for (const criterion of criteria.length ? criteria : ["Unmapped"]) {
        const bucket = byCriterion.get(criterion) ?? [];
        bucket.push(control);
        byCriterion.set(criterion, bucket);
      }
    }
    return [...byCriterion.entries()]
      .sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }))
      .map(([criterion, cs]) => ({
        criterion,
        label: nameFor.get(criterion) ?? criterion,
        controls: cs,
      }));
  }, [controlsQuery.data, requirementsQuery.data, frameworkCode]);

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0] ?? null;
    if (picked && DANGEROUS_EXT.test(picked.name)) {
      setFile(null);
      setFileError(
        "That file type can’t be uploaded as evidence. Executables and scripts are blocked.",
      );
      event.target.value = "";
      return;
    }
    setFileError(null);
    setFile(picked);
  }

  function renewalDate(): string | null {
    if (validity === "default") return null;
    if (validity === "custom") return customRenewal || null;
    return addDays(collectedAt, Number(validity));
  }

  function reset() {
    setKind("file");
    setTitle("");
    setEvidenceType("screenshot");
    setOwnerId(selfId);
    setCollectedAt(today());
    setValidity("default");
    setCustomRenewal("");
    setSourceLabel("");
    setDescription("");
    setLinkUrl("");
    setFile(null);
    setFileError(null);
    setFrameworkId("");
    setControlIds(presetControlIds ?? []);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const renewal = renewalDate();
      if (kind === "link") {
        return evidenceApi.addLink({
          title,
          link_url: linkUrl,
          evidence_type: evidenceType,
          collected_at: collectedAt,
          description: description || null,
          source_label: sourceLabel || null,
          owner_membership_id: ownerId || null,
          renewal_date: renewal,
          control_ids: controlIds,
        });
      }
      const form = new FormData();
      form.append("file", file as File);
      form.append("title", title);
      form.append("evidence_type", evidenceType);
      form.append("collected_at", collectedAt);
      if (description) form.append("description", description);
      if (sourceLabel) form.append("source_label", sourceLabel);
      if (ownerId) form.append("owner_membership_id", ownerId);
      if (renewal) form.append("renewal_date", renewal);
      for (const id of controlIds) form.append("control_ids", id);
      return evidenceApi.uploadFile(form);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
      // Attaching evidence writes audit rows against each control it links to,
      // so any open control History must refetch. Prefix-invalidated because
      // this dialog does not know which control the user came from.
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      toast({ title: "Evidence added", tone: "success" });
      reset();
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "evidence item"), tone: "danger" }),
  });

  const canSubmit =
    title.trim() !== "" &&
    ownerId !== "" &&
    !fileError &&
    (kind === "link" ? linkUrl.trim() !== "" : file !== null);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent size="lg" className="max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>Add evidence</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="inline-flex w-fit rounded-md border border-border p-0.5">
            {(["file", "link"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setKind(option)}
                className={cn(
                  "rounded-sm px-5 py-1 text-label-sm capitalize transition-colors duration-80 ease-state",
                  kind === option
                    ? "bg-action-accent-tint text-action-accent"
                    : "text-text-secondary hover:text-text-primary",
                )}
              >
                {option}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {kind === "file" ? (
              <div className="col-span-2">
                <label
                  htmlFor="evidence-file"
                  className="mb-1.5 block font-sans text-label-sm text-text-secondary"
                >
                  File
                </label>
                <input
                  id="evidence-file"
                  type="file"
                  accept={FILE_ACCEPT}
                  onChange={pickFile}
                  className="block w-full rounded-sm border border-border bg-surface-primary py-2 pr-3 text-body-sm text-text-secondary file:mr-3 file:h-9 file:border-0 file:border-r file:border-border file:bg-surface-sunken file:px-3 file:text-label-sm file:text-text-primary"
                />
                {fileError ? (
                  <p className="mt-1.5 text-caption text-status-danger-text">{fileError}</p>
                ) : null}
              </div>
            ) : (
              <div className="col-span-2">
                <TextField
                  label="Link URL"
                  value={linkUrl}
                  onChange={(event) => setLinkUrl(event.target.value)}
                  placeholder="https://…"
                />
              </div>
            )}

            <div className="col-span-2">
              <TextField
                label="Title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Q1 access review export"
              />
            </div>

            <div className="col-span-2">
              <TextField
                label="Description"
                optional
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>

            <SelectField label="Evidence type">
              <Select value={evidenceType} onValueChange={setEvidenceType}>
                <SelectTrigger aria-label="Evidence type" />
                <SelectContent>
                  {types.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* An empty dropdown reads as "there are no types". Say why. */}
              {vocabularyQuery.isError ? (
                <p className="mt-1 text-body-sm text-status-danger-text">
                  {describeError(vocabularyQuery.error, "evidence type list").message}
                </p>
              ) : null}
            </SelectField>

            <SelectField label="Owner">
              <Select value={ownerId} onValueChange={setOwnerId}>
                <SelectTrigger aria-label="Owner" />
                <SelectContent>
                  {members.map((member) => (
                    <SelectItem key={member.membership_id} value={member.membership_id}>
                      {member.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>

            <TextField
              label="Collection date"
              type="date"
              value={collectedAt}
              onChange={(event) => setCollectedAt(event.target.value)}
            />
            <SelectField label="Validity period">
              <Select value={validity} onValueChange={setValidity}>
                <SelectTrigger aria-label="Validity period" />
                <SelectContent>
                  {VALIDITY_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>

            {validity === "custom" ? (
              <div className="col-span-2">
                <TextField
                  label="Valid until"
                  type="date"
                  value={customRenewal}
                  onChange={(event) => setCustomRenewal(event.target.value)}
                />
              </div>
            ) : null}

            <TextField
              label="Source system"
              optional
              value={sourceLabel}
              onChange={(event) => setSourceLabel(event.target.value)}
              placeholder="Okta admin console"
            />

            <div>
              <span className="mb-1.5 block font-sans text-label-sm text-text-secondary">
                Linked assets
                <span className="ml-1 font-normal text-text-faint">(optional)</span>
              </span>
              <div className="flex h-9 items-center justify-between rounded-sm border border-border bg-surface-sunken px-3 text-body-md text-text-faint">
                Coming soon
                <Icon name="chev" className="size-4" />
              </div>
            </div>

            <div className="col-span-2">
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <span className="font-sans text-label-sm text-text-secondary">Controls</span>
                <div className="w-44">
                  <Select
                    value={activeFrameworkId}
                    onValueChange={(value) => {
                      setFrameworkId(value);
                      setControlIds([]);
                    }}
                  >
                    <SelectTrigger aria-label="Framework" className="h-8" />
                    <SelectContent>
                      {frameworks.map((framework) => (
                        <SelectItem key={framework.id} value={framework.id}>
                          {framework.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {controlsQuery.isError ? (
                <p className="text-body-sm text-status-danger-text">
                  {describeError(controlsQuery.error, "control list").message}
                </p>
              ) : (
                <ControlPicker
                  groups={groups}
                  value={controlIds}
                  onChange={setControlIds}
                  loading={controlsQuery.isLoading}
                />
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={saveMutation.isPending}
            disabled={!canSubmit}
            onClick={() => saveMutation.mutate()}
          >
            Add evidence
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
export function EvidencePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { principal } = useAuth();
  const canManage = Boolean(principal?.permissions.includes("evidence:manage"));

  const [search, setSearch] = useState("");
  const [freshnessFilter, setFreshnessFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [reviewFilter, setReviewFilter] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const cols = useColumnPrefs("verity.evidence.columns", EVIDENCE_COLUMNS);

  const evidenceQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => evidenceApi.list(),
  });
  const vocabularyQuery = useQuery({
    queryKey: ["evidence-vocabulary"],
    queryFn: () => evidenceApi.vocabulary(),
  });
  // Only for the coverage-snapshot denominator (controls with evidence / total).
  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
  });

  const items = useMemo(() => evidenceQuery.data ?? [], [evidenceQuery.data]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter(
      (item) =>
        (freshnessFilter.length === 0 ||
          freshnessFilter.includes(item.freshness)) &&
        (typeFilter.length === 0 || typeFilter.includes(item.evidence_type)) &&
        (reviewFilter.length === 0 ||
          reviewFilter.includes(item.review_status)) &&
        (query === "" ||
          item.title.toLowerCase().includes(query) ||
          (item.source_label ?? "").toLowerCase().includes(query) ||
          item.control_codes.some((code) => code.toLowerCase().includes(query))),
    );
  }, [items, search, freshnessFilter, typeFilter, reviewFilter]);

  // Freshness and review sort by their own severity order, not alphabetically,
  // so "stale first" is one click rather than a reading exercise.
  const { thProps, sortRows } = useTableSort<Evidence, string>(null, {
    title: (item) => item.title,
    type: (item) => item.evidence_type,
    owner: (item) => item.owner_name,
    renewal: (item) => item.renewal_date,
    freshness: (item) => FRESHNESS_ORDER.indexOf(item.freshness),
    review: (item) => REVIEW_ORDER.indexOf(item.review_status),
  });

  const activeFilters = [
    ...reviewFilter.map(
      (state) => `Review: ${REVIEW_META[state as ReviewStatus].label}`,
    ),
    ...freshnessFilter.map(
      (state) => `Freshness: ${FRESHNESS[state as EvidenceFreshness].label}`,
    ),
    ...typeFilter.map((type) => `Type: ${type.replace(/_/g, " ")}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];

  function clearFilters() {
    setSearch("");
    setFreshnessFilter([]);
    setTypeFilter([]);
    setReviewFilter([]);
  }

  if (evidenceQuery.isError) {
    const failure = describeError(evidenceQuery.error, "evidence library");
    return (
      <div className="w-full">
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          onRetry={failure.retryable ? () => void evidenceQuery.refetch() : undefined}
        />
      </div>
    );
  }

  return (
    <div className="w-full">
      <PageHeader eyebrow="Compliance" title="Evidence" />

      {items.length > 0 ? (
        <EvidenceOverview
          items={items}
          controlsTotal={controlsQuery.isError ? null : (controlsQuery.data?.length ?? 0)}
          onPickFreshness={(state) => setFreshnessFilter([state])}
        />
      ) : null}

      <Toolbar
        searchLabel="Filter evidence"
        search={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by title, source or control…"
            aria-label="Search evidence"
          />
        }
        actions={
          <>
            <p aria-live="polite" className="text-caption text-text-subtle">
              Showing <span className="tabular">{visible.length}</span> of{" "}
              <span className="tabular">{items.length}</span> items
            </p>
            {canManage ? (
              <Button onClick={() => setAdding(true)}>
                <Icon name="plus" className="size-4" />
                Add evidence
              </Button>
            ) : null}
          </>
        }
      >
        <FilterFacet
          label="Review"
          options={REVIEW_ORDER.map((state) => ({
            value: state,
            label: REVIEW_META[state].label,
          }))}
          values={reviewFilter}
          onChange={setReviewFilter}
        />
        <FilterFacet
          label="Freshness"
          options={FRESHNESS_ORDER.map((state) => ({
            value: state,
            label: FRESHNESS[state].label,
          }))}
          values={freshnessFilter}
          onChange={setFreshnessFilter}
        />
        {vocabularyQuery.data ? (
          <FilterFacet
            label="Type"
            options={vocabularyQuery.data.types.map((type) => ({
              value: type.value,
              label: type.label,
            }))}
            values={typeFilter}
            onChange={setTypeFilter}
          />
        ) : null}
        {activeFilters.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      {evidenceQuery.isLoading ? (
        <TableSkeleton rows={6} density="comfortable" />
      ) : items.length === 0 ? (
        <EmptyState
          icon="doc"
          title="No evidence yet"
          description="Upload a file or record a link to start proving your controls operate."
          action={
            canManage ? (
              <Button onClick={() => setAdding(true)}>Add evidence</Button>
            ) : undefined
          }
        />
      ) : visible.length === 0 ? (
        <EmptyState
          variant="no-match"
          title="No evidence matches your filters"
          description={`Try removing ${activeFilters
            .map((name) => `'${name}'`)
            .join(" or ")}.`}
          onClearFilters={clearFilters}
        />
      ) : (
        <Table density="comfortable" actions={<ColumnPicker {...cols} />}>
          <THead>
            <TR>
              <TH {...thProps("title")}>Evidence</TH>
              {cols.isVisible("type") ? <TH {...thProps("type")}>Type</TH> : null}
              {cols.isVisible("controls") ? <TH>Controls</TH> : null}
              {cols.isVisible("owner") ? <TH {...thProps("owner")}>Owner</TH> : null}
              {cols.isVisible("renewal") ? (
                <TH {...thProps("renewal")}>Renewal</TH>
              ) : null}
              {cols.isVisible("freshness") ? (
                <TH {...thProps("freshness")}>Freshness</TH>
              ) : null}
              {cols.isVisible("review") ? (
                <TH {...thProps("review")}>Review</TH>
              ) : null}
              <TH>
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {sortRows(visible).map((item) => (
              <TR
                key={item.id}
                onClick={() => navigate(`/evidence/${item.id}`)}
                className="cursor-pointer"
              >
                <TD>
                  <span className="block min-w-0">
                    <span className="block text-body-md text-text-primary">
                      {item.title}
                    </span>
                    {item.source_label ? (
                      <span className="block truncate text-body-sm text-text-subtle">
                        {item.source_label}
                      </span>
                    ) : null}
                  </span>
                </TD>
                {cols.isVisible("type") ? (
                  <TD>
                    <Badge variant="neutral">
                      {item.evidence_type.replace(/_/g, " ")}
                    </Badge>
                  </TD>
                ) : null}
                {cols.isVisible("controls") ? (
                  <TD>
                    <div className="flex flex-wrap gap-1">
                      {item.control_links.length ? (
                        item.control_links.map((link) => (
                          <span
                            key={link.code}
                            className="inline-flex flex-col rounded-xs bg-surface-sunken px-1.5 py-0.5 leading-tight"
                          >
                            <span className="text-caption font-medium text-text-secondary">
                              {link.code}
                            </span>
                            {link.criteria.length ? (
                              <span className="text-[10px] text-text-subtle">
                                {link.criteria.join(" · ")}
                              </span>
                            ) : null}
                          </span>
                        ))
                      ) : (
                        <span className="text-caption text-status-warning-text">
                          None
                        </span>
                      )}
                    </div>
                  </TD>
                ) : null}
                {cols.isVisible("owner") ? (
                  <TD>
                    {item.owner_name ? (
                      <span className="flex items-center gap-2">
                        <Avatar name={item.owner_name} size="sm" />
                        <span className="truncate text-body-sm text-text-primary">
                          {item.owner_name}
                        </span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-[10px] font-bold text-text-subtle">
                          ?
                        </span>
                        <span className="text-body-sm text-text-subtle">
                          Unassigned
                        </span>
                      </span>
                    )}
                  </TD>
                ) : null}
                {cols.isVisible("renewal") ? (
                  <TD>
                    <span className="tabular text-body-sm text-text-secondary">
                      {formatDate(item.renewal_date)}
                    </span>
                  </TD>
                ) : null}
                {cols.isVisible("freshness") ? (
                  <TD>
                    <StatusPill
                      kind="inline"
                      status={FRESHNESS[item.freshness].family}
                      label={FRESHNESS[item.freshness].label}
                    />
                  </TD>
                ) : null}
                {cols.isVisible("review") ? (
                  <TD>
                    <StatusPill
                      kind="inline"
                      status={REVIEW_META[item.review_status].family}
                      label={REVIEW_META[item.review_status].label}
                    />
                  </TD>
                ) : null}
                {/* Row actions. The cell stops propagation so opening the menu
                    does not also navigate to the detail page. */}
                <TD
                  className="text-right"
                  onClick={(event) => event.stopPropagation()}
                >
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Actions for ${item.title}`}
                      >
                        <Icon name="more" className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onSelect={() =>
                          window.setTimeout(() => navigate(`/evidence/${item.id}`), 0)
                        }
                      >
                        View details
                      </DropdownMenuItem>
                      {item.kind === "file" ? (
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(
                              () =>
                                void downloadEvidence(item).catch(() =>
                                  toast({
                                    title: "Couldn't download the file.",
                                    tone: "danger",
                                  }),
                                ),
                              0,
                            )
                          }
                        >
                          Download
                        </DropdownMenuItem>
                      ) : item.link_url ? (
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(
                              () => window.open(item.link_url!, "_blank", "noopener"),
                              0,
                            )
                          }
                        >
                          Open link
                        </DropdownMenuItem>
                      ) : null}
                      {canManage ? (
                        <DropdownMenuItem
                          onSelect={() =>
                            window.setTimeout(() => navigate(`/evidence/${item.id}`), 0)
                          }
                        >
                          Edit details
                        </DropdownMenuItem>
                      ) : null}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <AddEvidenceDialog open={adding} onOpenChange={setAdding} />
    </div>
  );
}
