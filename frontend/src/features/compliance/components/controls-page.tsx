import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  Checkbox,
  ColumnPicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PageHeader,
  Pagination,
  SearchInput,
  SegmentedControl,
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
  type SegmentedItem,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { complianceApi, controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { Control, ControlStatus } from "@/lib/api/types";
import { OwnerSelect } from "@/features/iam/components/owner-select";
import type { ComposeMode } from "@/features/connectors/api";
import { useControlComposition } from "@/features/connectors/hooks";
import {
  MODE,
  systemOptions,
} from "@/features/connectors/components/composition-meta";
import {
  EvidencedBy,
  MonitoringWord,
} from "@/features/connectors/components/composition-ui";
import { ControlFormDialog } from "./control-form-dialog";
import { ControlsBulkBar } from "./controls-bulk-bar";
import { FrameworkChip, TrustServiceChip } from "./trust-services";
import {
  TRUST_SERVICES,
  frameworksFor,
  trustServicesFor,
  type TrustService,
} from "@/features/compliance/trust-services";
import {
  downloadControlReport,
  printControlReport,
} from "@/features/compliance/control-report-export";

/** A facet option that also states how many rows it would leave. */
const withCount = (label: string, n: number) => (n ? `${label} (${n})` : label);

/** How a control can be evidenced, in the order the facet lists them. */
const COMPOSE_MODES: ComposeMode[] = ["automated", "hybrid", "manual"];

/** DS §6.1 — a control's implementation state, mapped once so every screen
 *  renders the same word the same way. */
const STATUS_LABEL: Record<ControlStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  implemented: "Implemented",
  not_applicable: "Not applicable",
};

const STATUS_FAMILY: Record<
  ControlStatus,
  "success" | "progress" | "pending" | "neutral"
> = {
  not_started: "pending",
  in_progress: "progress",
  implemented: "success",
  not_applicable: "neutral",
};

type StatusFamily = "success" | "progress" | "pending" | "neutral" | "danger";

/** A disabled control reads as "Disabled" everywhere, over its old status —
 *  it is retired, not deleted, so it stays visible but inactive. */
function displayStatus(control: Control): {
  label: string;
  family: StatusFamily;
} {
  if (control.disabled_at) return { label: "Disabled", family: "neutral" };
  return {
    label: STATUS_LABEL[control.status],
    family: STATUS_FAMILY[control.status],
  };
}

/** Where a control came from: authored internally, or the SOC 2 library. */
function SourceBadge({ origin }: { origin: Control["origin"] }) {
  return origin === "custom" ? (
    <Badge variant="role">Internal</Badge>
  ) : (
    <Badge variant="neutral">SOC 2</Badge>
  );
}

/** A disabled-looking field for a capability that is not built yet. */
function ComingSoonField({ label }: { label: string }) {
  return (
    <div>
      <p className="type-overline mb-1.5">{label}</p>
      <div className="flex h-9 items-center justify-between rounded-sm border border-border bg-surface-sunken px-3 text-body-md text-text-faint">
        Coming soon
        <Icon name="chev" className="size-4" />
      </div>
    </div>
  );
}

/** Design (Preventive, Detective…) is a taxonomy, not a status — neutral chips
 *  (DS §1, F12). The spec's Type and Sub-type are the domain columns, so this
 *  axis took the word Design. */
function DesignChip({ label }: { label: string }) {
  return <Badge variant="neutral">{label}</Badge>;
}

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZES = [10, 20, 50, 100];

type GroupBy = "none" | "type" | "subtype";

const GROUP_ITEMS: readonly SegmentedItem<GroupBy>[] = [
  { id: "none", label: "None" },
  { id: "type", label: "Type" },
  { id: "subtype", label: "Sub-type" },
];

/** Where a control with no Sub-type sits when grouping by Sub-type. */
const NO_SUB_TYPE = "No sub-type";

/** The Sub-types in use under the chosen Types (all of them when none is
 *  chosen), so the facet never offers one that would return nothing. */
function subTypesWithin(
  controls: readonly Control[],
  types: readonly string[],
): string[] {
  const found = new Set<string>();
  for (const control of controls) {
    if (
      control.sub_category &&
      (types.length === 0 || types.includes(control.category))
    ) {
      found.add(control.sub_category);
    }
  }
  return [...found].sort((a, b) => a.localeCompare(b));
}

function ControlDetailDialog({
  control,
  onClose,
  onEdit,
  canManage,
  autoConfirm = false,
}: {
  control: Control | null;
  onClose: () => void;
  onEdit: (control: Control) => void;
  canManage: boolean;
  autoConfirm?: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);

  // Open straight into the disable-confirm step when the kebab "Disable" asked.
  // Keyed on the id, not the object: a refetch hands back a new Control every
  // time, and depending on it would reset the reason mid-typing.
  const controlId = control?.id ?? null;
  useEffect(() => {
    setConfirming(controlId !== null && autoConfirm);
    setReason("");
  }, [controlId, autoConfirm]);

  const evidenceQuery = useQuery({
    queryKey: ["evidence", "control", control?.id],
    queryFn: () => evidenceApi.list({ control_id: control!.id }),
    enabled: control !== null,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["controls"] });

  const statusMutation = useMutation({
    mutationFn: (status: ControlStatus) =>
      controlsApi.update(control!.id, { status }),
    onSuccess: async () => {
      await invalidate();
      toast({ title: "Status updated", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  const disableMutation = useMutation({
    mutationFn: () => controlsApi.disable(control!.id, reason),
    onSuccess: async () => {
      await invalidate();
      setReason("");
      setConfirming(false);
      onClose();
      toast({ title: "Control disabled", tone: "neutral" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  const enableMutation = useMutation({
    mutationFn: () => controlsApi.enable(control!.id),
    onSuccess: async () => {
      await invalidate();
      toast({ title: "Control re-enabled", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  // `clear_owner` wins over `owner_membership_id` server-side, so unassigning
  // must send the flag alone and assigning must not send the flag at all.
  const ownerMutation = useMutation({
    mutationFn: (membershipId: string | null) =>
      controlsApi.update(
        control!.id,
        membershipId === null
          ? { clear_owner: true }
          : { owner_membership_id: membershipId },
      ),
    onSuccess: async () => {
      await invalidate();
      toast({ title: "Owner updated", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  return (
    <Dialog
      open={control !== null}
      onOpenChange={(open) => {
        if (!open) {
          setConfirming(false);
          setReason("");
          onClose();
        }
      }}
    >
      <DialogContent size="lg" className="max-h-[90vh]">
        {control ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex flex-wrap items-baseline gap-2 pr-6">
                <span className="font-mono text-body-sm font-normal text-text-subtle">
                  {control.code}
                </span>
                {control.name}
              </DialogTitle>
              <DialogDescription>{control.description}</DialogDescription>
            </DialogHeader>

            <div className="mt-4 space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <SourceBadge origin={control.origin} />
                <StatusPill
                  kind="inline"
                  status={displayStatus(control).family}
                  label={displayStatus(control).label}
                />
              </div>

              {control.disabled_at ? (
                <div className="rounded-md border border-status-neutral-border bg-status-neutral-bg px-3.5 py-3">
                  <p className="text-label-md text-status-neutral-text">
                    Disabled · {control.disabled_reason}
                  </p>
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="type-overline mb-1.5">Trust Services</p>
                  {trustServicesFor(control).length ? (
                    <div className="flex flex-wrap gap-1">
                      {trustServicesFor(control).map((tsc) => (
                        <TrustServiceChip key={tsc} tsc={tsc} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-body-sm text-text-subtle">None</span>
                  )}
                </div>
                <div>
                  <p className="type-overline mb-1.5">Frameworks</p>
                  {frameworksFor(control).length ? (
                    <div className="flex flex-wrap gap-1">
                      {frameworksFor(control).map((framework) => (
                        <FrameworkChip key={framework} label={framework} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-body-sm text-text-subtle">None</span>
                  )}
                </div>
                <div>
                  <p className="type-overline mb-1.5">Type</p>
                  <p className="text-body-sm text-text-secondary">
                    {control.category}
                  </p>
                </div>
                <div>
                  <p className="type-overline mb-1.5">Sub-type</p>
                  <p className="text-body-sm text-text-secondary">
                    {control.sub_category || "Not set"}
                  </p>
                </div>
                {control.origin === "custom" && control.control_type ? (
                  <div>
                    <p className="type-overline mb-1.5">Design</p>
                    <DesignChip label={control.control_type} />
                  </div>
                ) : null}
              </div>

              {/* Owner is assignable in place — a control without a named owner
                  is the single most common audit finding. */}
              <div>
                <p className="type-overline mb-1.5">Owner</p>
                {canManage && !control.disabled_at ? (
                  <OwnerSelect
                    value={control.owner_membership_id}
                    valueLabel={control.owner_name}
                    onChange={(membershipId) =>
                      ownerMutation.mutate(membershipId)
                    }
                    disabled={ownerMutation.isPending}
                  />
                ) : (
                  <p className="flex items-center gap-2 text-body-sm text-text-secondary">
                    {control.owner_name ? (
                      <>
                        <Avatar name={control.owner_name} size="sm" />
                        {control.owner_name}
                      </>
                    ) : (
                      "Unassigned"
                    )}
                  </p>
                )}
              </div>

              <div>
                <p className="type-overline mb-1.5">Mapped criteria</p>
                {control.requirement_keys.length ? (
                  <div className="flex flex-wrap gap-1">
                    {control.requirement_keys.map((key) => (
                      <span
                        key={key}
                        className="rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link"
                      >
                        {key.replace("SOC2:", "")}
                      </span>
                    ))}
                  </div>
                ) : (
                  // A control satisfying no criterion is a real gap, not a blank.
                  <p className="text-body-sm text-status-warning-text">
                    Not mapped to any criterion
                  </p>
                )}
              </div>

              {control.implementation_guidance ? (
                <div>
                  <p className="type-overline mb-1.5">
                    Implementation guidance
                  </p>
                  <p className="whitespace-pre-line text-body-sm leading-relaxed text-text-secondary">
                    {control.implementation_guidance}
                  </p>
                </div>
              ) : null}

              <div>
                <p className="type-overline mb-1.5">Linked evidence</p>
                {evidenceQuery.data && evidenceQuery.data.length > 0 ? (
                  <ul className="space-y-1.5">
                    {evidenceQuery.data.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-center gap-2 text-body-sm"
                      >
                        <Icon
                          name={item.kind === "file" ? "doc" : "globe"}
                          className="size-4 shrink-0 text-text-subtle"
                        />
                        <span className="min-w-0 flex-1 truncate text-text-secondary">
                          {item.title}
                        </span>
                        <Badge variant="neutral">
                          {item.evidence_type.replace(/_/g, " ")}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : evidenceQuery.isError ? (
                  // "No evidence linked yet" on a failed read is a fabricated
                  // compliance finding, so say what actually happened.
                  <p className="text-body-sm text-status-danger-text">
                    {
                      describeError(evidenceQuery.error, "evidence list")
                        .message
                    }
                  </p>
                ) : (
                  <p className="text-body-sm text-status-warning-text">
                    No evidence linked yet
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <ComingSoonField label="Link to asset" />
                <ComingSoonField label="Link to risk" />
              </div>

              {canManage && !control.disabled_at ? (
                <div>
                  <SelectField label="Status">
                    <Select
                      value={control.status}
                      onValueChange={(value) =>
                        statusMutation.mutate(value as ControlStatus)
                      }
                    >
                      <SelectTrigger aria-label="Control status" />
                      <SelectContent>
                        {(Object.keys(STATUS_LABEL) as ControlStatus[]).map(
                          (status) => (
                            <SelectItem key={status} value={status}>
                              {STATUS_LABEL[status]}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                  </SelectField>
                </div>
              ) : null}

              {canManage && confirming ? (
                <div className="rounded-md border border-status-danger-border bg-status-danger-bg p-3.5">
                  <p className="mb-2 text-label-md text-status-danger-text">
                    Disabling records a justification on the audit trail. The
                    control is retired, never deleted.
                  </p>
                  <TextField
                    label="Reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Why is this control no longer applicable?"
                  />
                </div>
              ) : null}
            </div>

            <DialogFooter>
              {canManage && confirming ? (
                <>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setConfirming(false);
                      setReason("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={!reason.trim()}
                    loading={disableMutation.isPending}
                    onClick={() => disableMutation.mutate()}
                  >
                    Disable control
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="secondary" onClick={onClose}>
                    Close
                  </Button>
                  {canManage ? (
                    <>
                      {control.disabled_at ? null : (
                        <Button
                          variant="secondary"
                          onClick={() => onEdit(control)}
                        >
                          Edit
                        </Button>
                      )}
                      {control.disabled_at ? (
                        <Button
                          variant="secondary"
                          loading={enableMutation.isPending}
                          onClick={() => enableMutation.mutate()}
                        >
                          Re-enable control
                        </Button>
                      ) : (
                        <Button
                          variant="destructive-2"
                          onClick={() => setConfirming(true)}
                        >
                          Disable control
                        </Button>
                      )}
                    </>
                  ) : null}
                </>
              )}
            </DialogFooter>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

/** Columns the reader can hide. "Control" (identity) and the action/selection
 *  columns are structural and always shown. Choice persists per browser. */
const TOGGLEABLE_COLUMNS = [
  { key: "type", label: "Type" },
  { key: "subtype", label: "Sub-type" },
  { key: "description", label: "Description" },
  { key: "trust", label: "Trust services" },
  { key: "criteria", label: "Criteria" },
  { key: "frameworks", label: "Frameworks" },
  { key: "owner", label: "Owner" },
  { key: "evidencedBy", label: "Evidenced by" },
  { key: "evidence", label: "Evidence" },
  { key: "status", label: "Status" },
] as const satisfies readonly ColumnDef<string>[];

/** Controls — the tenant's working library, instantiated from the shipped
 *  templates. Code, Type and Sub-type (the spec's two domain columns),
 *  description, Trust Services, mapped criteria, owner and status per row, with
 *  a facet for each and Group by Type or Sub-type. Design (Preventive,
 *  Detective…) is a facet and shows on internal controls only. */
export function ControlsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));
  const canExport = Boolean(principal?.permissions.includes("frameworks:read"));
  const [exporting, setExporting] = useState<null | "csv" | "xlsx" | "pdf">(
    null,
  );

  // Description starts hidden: with Type and Sub-type on, the table is as wide as
  // a 1440px screen allows with it off, and it is the one column whose full text
  // sits a click away on the detail page. The key carries a version so a browser
  // that saved the old layout (every column on) moves to this one.
  const cols = useColumnPrefs("verity.controls.columns.v2", TOGGLEABLE_COLUMNS, [
    "description",
  ]);
  const composition = useControlComposition();
  const compositionById = useMemo(
    () => new Map((composition.data ?? []).map((item) => [item.control_id, item])),
    [composition.data],
  );

  async function handleExport(format: "csv" | "xlsx" | "pdf") {
    if (exporting) return;
    setExporting(format);
    try {
      if (format === "pdf") {
        const report = await controlsApi.report();
        printControlReport(report, principal?.tenant_name ?? "Workspace");
      } else {
        await downloadControlReport(format);
      }
    } catch {
      toast({
        title: "Export failed. Please try again.",
        tone: "danger",
      });
    } finally {
      setExporting(null);
    }
  }

  // The dashboard deep-links here with filters pre-applied (e.g.
  // ?status=not_started, ?owner=unassigned, ?evidence=none). Read once as the
  // initial value so a click on a chart lands on exactly that slice; the facets
  // stay the owner of the filter afterwards, and Clear still clears it.
  const [params] = useSearchParams();
  const [search, setSearch] = useState("");
  /** Type is the domain (`category`); Design is Preventive, Detective… */
  const [types, setTypes] = useState<string[]>(() => params.getAll("type"));
  const [subTypes, setSubTypes] = useState<string[]>(() =>
    params.getAll("subtype"),
  );
  const [designs, setDesigns] = useState<string[]>(() =>
    params.getAll("design"),
  );
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [trustServices, setTrustServices] = useState<string[]>(() =>
    params.getAll("trust"),
  );
  const [statuses, setStatuses] = useState<string[]>(() =>
    params.getAll("status"),
  );
  const [owners, setOwners] = useState<string[]>(() => params.getAll("owner"));
  const [evidence, setEvidence] = useState<string[]>(() =>
    params.getAll("evidence"),
  );
  const [frameworkFilter, setFrameworkFilter] = useState<string[]>(() =>
    params.getAll("framework"),
  );
  /** How a control is evidenced (`?evidenced=automated`) and which system checks
   *  it (`?system=github`, where the connections page links). Both come from the
   *  composition, so they apply once it has loaded. */
  const [modes, setModes] = useState<ComposeMode[]>(() =>
    params
      .getAll("evidenced")
      .filter((mode): mode is ComposeMode =>
        (COMPOSE_MODES as string[]).includes(mode),
      ),
  );
  const [systems, setSystems] = useState<string[]>(() =>
    params.getAll("system"),
  );
  /** The open row, held by id — a snapshot would go stale the moment an edit
   *  inside the dialog refetched the list, leaving the dialog showing the old
   *  owner while the table behind it showed the new one. */
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirmDisable, setConfirmDisable] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Control | null>(null);
  /** Row selection for bulk actions — distinct from `selected`, the open row. */
  const [checkedIds, setCheckedIds] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [customSize, setCustomSize] = useState(false);

  const navigate = useNavigate();

  function view(control: Control) {
    navigate(`/controls/${control.id}`);
  }

  // Disabled controls stay in the library (retired, not deleted), so this view
  // asks for them; the evidence picker's ["controls"] query keeps its own
  // active-only list. Both are refreshed by a prefix invalidate of ["controls"].
  const controlsQuery = useQuery({
    queryKey: ["controls", "all"],
    queryFn: () => controlsApi.list({ include_disabled: true }),
  });
  const vocabularyQuery = useQuery({
    queryKey: ["control-vocabulary"],
    queryFn: () => controlsApi.vocabulary(),
  });
  // One list call, counted client-side. The evidence service loads every
  // mapping row on any read, so `?control_id=` per row would be N full scans
  // to learn what a single request already carries.
  //
  // Reading evidence is a separate permission from reading controls, so this is
  // gated: without it the column reports "Unknown" rather than a confident 0, which
  // would otherwise read as "this control has no evidence" — a fabricated
  // compliance finding.
  const canReadEvidence = Boolean(
    principal?.permissions.includes("evidence:read"),
  );
  const evidenceQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => evidenceApi.list(),
    enabled: canReadEvidence,
  });
  const evidenceKnown = evidenceQuery.isSuccess;
  // The criterion → Trust Services Category mapping, straight from the shipped
  // requirements rather than inferred from the code's prefix.
  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
  });
  const soc2Id = frameworksQuery.data?.find((f) =>
    f.code.toUpperCase().startsWith("SOC"),
  )?.id;
  const requirementsQuery = useQuery({
    queryKey: ["requirements", soc2Id],
    queryFn: () => complianceApi.listRequirements(soc2Id!),
    enabled: Boolean(soc2Id),
  });

  const evidenceCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of evidenceQuery.data ?? []) {
      for (const controlId of item.control_ids) {
        counts.set(controlId, (counts.get(controlId) ?? 0) + 1);
      }
    }
    return counts;
  }, [evidenceQuery.data]);

  /** requirement_key → Trust Services Category, authoritative from the server. */
  const tscByKey = useMemo(() => {
    const map = new Map<string, TrustService>();
    for (const requirement of requirementsQuery.data ?? []) {
      map.set(
        requirement.requirement_key,
        requirement.trust_services_category as TrustService,
      );
    }
    return map;
  }, [requirementsQuery.data]);

  const tscFor = useMemo(
    () => (control: Control) => {
      if (tscByKey.size === 0) return trustServicesFor(control);
      const found = new Set<TrustService>();
      for (const key of control.requirement_keys) {
        const tsc = tscByKey.get(key);
        if (tsc) found.add(tsc);
      }
      // A key with no server row (a framework not loaded here) still resolves
      // through the prefix rule rather than silently vanishing from the column.
      return found.size
        ? TRUST_SERVICES.filter((t) => found.has(t))
        : trustServicesFor(control);
    },
    [tscByKey],
  );

  const adoptMutation = useMutation({
    mutationFn: () => controlsApi.adopt(),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      toast({
        title: `${result.created} controls added to your library`,
        tone: "success",
      });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control library"), tone: "danger" }),
  });

  const controls = useMemo(
    () => controlsQuery.data ?? [],
    [controlsQuery.data],
  );
  const vocabulary = vocabularyQuery.data;

  /** Whether a control fits the Evidenced by and System facets. Without a
   *  composition (loading, or it failed) the facets are hidden and there is
   *  nothing to match on, so every control fits. */
  const evidencedAs = useCallback(
    (controlId: string) => {
      if (!composition.data) return true;
      const item = compositionById.get(controlId);
      return (
        (modes.length === 0 ||
          (item !== undefined && modes.includes(item.composition.mode))) &&
        (systems.length === 0 ||
          (item?.composition.runs_on.some((key) => systems.includes(key)) ??
            false))
      );
    },
    [composition.data, compositionById, modes, systems],
  );

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return controls.filter(
      (control) =>
        evidencedAs(control.id) &&
        (types.length === 0 || types.includes(control.category)) &&
        (subTypes.length === 0 ||
          (control.sub_category != null &&
            subTypes.includes(control.sub_category))) &&
        (designs.length === 0 ||
          (control.control_type !== null &&
            designs.includes(control.control_type))) &&
        (trustServices.length === 0 ||
          tscFor(control).some((tsc) => trustServices.includes(tsc))) &&
        (frameworkFilter.length === 0 ||
          frameworksFor(control).some((f) => frameworkFilter.includes(f))) &&
        (owners.length === 0 ||
          owners.some((o) =>
            // "assigned"/"unassigned" describe the live library — the dashboard
            // counts it that way, and a click there must land on the same set.
            // A real owner id still matches regardless of disabled state.
            o === "assigned"
              ? control.owner_membership_id != null && !control.disabled_at
              : o === "unassigned"
                ? control.owner_membership_id == null && !control.disabled_at
                : o === control.owner_membership_id,
          )) &&
        (statuses.length === 0 ||
          statuses.includes(
            control.disabled_at ? "disabled" : control.status,
          )) &&
        // A retired control's evidence state is not a live gap, so an evidence
        // filter never matches a disabled control — this keeps the count behind
        // "112 with no evidence" identical whether read on the dashboard or here.
        (evidence.length === 0 ||
          (!control.disabled_at &&
            evidence.includes(
              (evidenceCounts.get(control.id) ?? 0) > 0 ? "with" : "none",
            ))) &&
        (query === "" ||
          control.name.toLowerCase().includes(query) ||
          control.code.toLowerCase().includes(query) ||
          (control.owner_name ?? "").toLowerCase().includes(query) ||
          control.requirement_keys.some((key) =>
            key.toLowerCase().includes(query),
          )),
    );
  }, [
    controls,
    search,
    types,
    subTypes,
    designs,
    trustServices,
    frameworkFilter,
    owners,
    statuses,
    evidence,
    evidenceCounts,
    tscFor,
    evidencedAs,
  ]);

  // Selection survives filtering. Pruning to the visible rows would wipe a
  // selection on every search keystroke — you pick five controls, type to find
  // a sixth, and the first five are gone. The count stays honest instead by
  // resolving against the whole library, so the bar never names a row that no
  // longer exists.
  const checkedControls = useMemo(
    () => controls.filter((control) => checkedIds.includes(control.id)),
    [controls, checkedIds],
  );

  // --- Sorting --------------------------------------------------------------
  // Sorts the whole filtered set, not the page, so page 2 is the continuation
  // of page 1 rather than its own little ordering.
  const { thProps, sortRows } = useTableSort<
    Control,
    "control" | "type" | "subtype" | "owner" | "evidence" | "status"
  >(null, {
    control: (control) => control.code,
    type: (control) => control.category,
    subtype: (control) => control.sub_category,
    owner: (control) => control.owner_name,
    evidence: (control) => evidenceCounts.get(control.id) ?? 0,
    status: (control) => displayStatus(control).label,
  });
  const sorted = useMemo(() => sortRows(visible), [sortRows, visible]);

  // --- Grouping -------------------------------------------------------------
  // Group first, then the chosen sort inside each group: Array.sort is stable, so
  // re-sorting by group rank leaves the chosen order within a group alone. Done
  // on the whole filtered set, before paging, so a group a page boundary splits
  // carries on at the top of the next page.
  const groupOf = useCallback(
    (control: Control) =>
      groupBy === "type"
        ? control.category
        : groupBy === "subtype"
          ? control.sub_category || NO_SUB_TYPE
          : "",
    [groupBy],
  );
  const ordered = useMemo(() => {
    if (groupBy === "none") return sorted;
    const domains = vocabulary?.categories ?? [];
    const domainRank = (label: string) => {
      const index = domains.indexOf(label);
      return index < 0 ? domains.length : index;
    };
    const labels = [...new Set(sorted.map(groupOf))].sort((a, b) => {
      // Controls with no Sub-type close the list. Types keep the library's own
      // domain order; Sub-types read alphabetically.
      if (a === NO_SUB_TYPE || b === NO_SUB_TYPE) {
        return a === NO_SUB_TYPE ? 1 : -1;
      }
      return groupBy === "type"
        ? domainRank(a) - domainRank(b) || a.localeCompare(b)
        : a.localeCompare(b);
    });
    const position = new Map(labels.map((label, index) => [label, index]));
    return [...sorted].sort(
      (a, b) =>
        (position.get(groupOf(a)) ?? 0) - (position.get(groupOf(b)) ?? 0),
    );
  }, [sorted, groupBy, groupOf, vocabulary]);
  /** How many controls each group holds across every page, for its header. */
  const groupCounts = useMemo(() => {
    const counts = new Map<string, number>();
    if (groupBy !== "none") {
      for (const control of ordered) {
        const label = groupOf(control);
        counts.set(label, (counts.get(label) ?? 0) + 1);
      }
    }
    return counts;
  }, [ordered, groupBy, groupOf]);

  // --- Paging ---------------------------------------------------------------
  const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
  // Clamp rather than reset: narrowing a filter while on page 9 should land on
  // the last page that still exists, not silently show an empty table.
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const paged = useMemo(
    () => ordered.slice(pageStart, pageStart + pageSize),
    [ordered, pageStart, pageSize],
  );

  // Select-all applies to the rows actually on screen, which is this page.
  const checkedVisibleCount = paged.filter((control) =>
    checkedIds.includes(control.id),
  ).length;
  /** Always the freshest copy, so an edit made in the dialog shows there too. */
  const selectedControl = useMemo(
    () => controls.find((control) => control.id === selectedId) ?? null,
    [controls, selectedId],
  );
  const allChecked = paged.length > 0 && checkedVisibleCount === paged.length;

  /** Owner facet options, built from who actually owns something. */
  const ownerOptions = useMemo(() => {
    const byId = new Map<string, string>();
    let unassigned = false;
    for (const control of controls) {
      if (control.owner_membership_id && control.owner_name) {
        byId.set(control.owner_membership_id, control.owner_name);
      } else {
        unassigned = true;
      }
    }
    const options = [...byId.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
    return unassigned
      ? [...options, { value: "unassigned", label: "Unassigned" }]
      : options;
  }, [controls]);

  const ownerLabel = (value: string) =>
    value === "assigned"
      ? "Assigned"
      : (ownerOptions.find((option) => option.value === value)?.label ?? value);

  /** Sub-type options cascade from the chosen Types. */
  const subTypeOptions = useMemo(
    () =>
      subTypesWithin(controls, types).map((value) => ({ value, label: value })),
    [controls, types],
  );

  /** Choosing other Types drops any Sub-type they no longer contain, so the
   *  active filter never names one the facet cannot show. */
  function changeTypes(next: string[]) {
    setTypes(next);
    const stillOffered = new Set(subTypesWithin(controls, next));
    setSubTypes((previous) =>
      previous.filter((subType) => stillOffered.has(subType)),
    );
  }

  /** Every framework the library actually maps to — the facet never offers one
   *  that would return nothing. */
  const frameworkOptions = useMemo(() => {
    const all = new Set<string>();
    for (const control of controls)
      for (const f of frameworksFor(control)) all.add(f);
    return [...all].sort().map((f) => ({ value: f, label: f }));
  }, [controls]);

  /** The systems that check any control, and how many controls each one checks. */
  const systemList = useMemo(
    () => systemOptions(composition.data ?? []),
    [composition.data],
  );
  const modeCounts = useMemo(() => {
    const counts: Record<ComposeMode, number> = {
      automated: 0,
      hybrid: 0,
      manual: 0,
    };
    for (const item of composition.data ?? []) counts[item.composition.mode] += 1;
    return counts;
  }, [composition.data]);
  /** People alone means no system checks the control, so a System choice would
   *  match nothing. It is dropped rather than left to empty the page. */
  const peopleOnly = modes.length > 0 && modes.every((mode) => mode === "manual");
  function changeModes(next: ComposeMode[]) {
    setModes(next);
    if (next.length > 0 && next.every((mode) => mode === "manual")) {
      setSystems([]);
    }
  }
  // A link in from the connections page lands on a filtered list, so the table
  // waits for the composition rather than flashing the whole library first.
  const waitingOnComposition =
    composition.isLoading && (modes.length > 0 || systems.length > 0);

  // The two numbers the deleted header summary carried. They now ride on the
  // facet option that filters to exactly that set.
  const unowned = controls.filter(
    (control) => !control.owner_membership_id && !control.disabled_at,
  ).length;
  const noEvidence = controls.filter(
    (control) =>
      !control.disabled_at && (evidenceCounts.get(control.id) ?? 0) === 0,
  ).length;

  // Top bar line, built only from what this page already loads. Nothing while
  // the library loads, and no evidence figure until evidence is actually known.
  const subtitle = controlsQuery.data
    ? [
        `${controls.length} ${controls.length === 1 ? "control" : "controls"}`,
        unowned ? `${unowned} without owner` : null,
        evidenceKnown && noEvidence ? `${noEvidence} without evidence` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  /** Columns on screen, for a group header to span. "Evidenced by" rides beside
   *  the code, so it is not one. */
  const columnCount =
    (canManage ? 1 : 0) +
    1 +
    TOGGLEABLE_COLUMNS.filter(
      ({ key }) => key !== "evidencedBy" && cols.isVisible(key),
    ).length +
    1;

  const activeFilters = [
    ...types.map((t) => `Type: ${t}`),
    ...subTypes.map((s) => `Sub-type: ${s}`),
    ...designs.map((d) => `Design: ${d}`),
    ...trustServices.map((t) => `Trust Services: ${t}`),
    ...frameworkFilter.map((f) => `Framework: ${f}`),
    ...owners.map((o) => `Owner: ${ownerLabel(o)}`),
    ...statuses.map((s) => `Status: ${STATUS_LABEL[s as ControlStatus] ?? s}`),
    ...evidence.map(
      (e) => `Evidence: ${e === "with" ? "Has evidence" : "None"}`,
    ),
    ...modes.map((m) => `Evidenced by: ${MODE[m].label}`),
    ...systems.map(
      (s) => `System: ${systemList.find((o) => o.value === s)?.label ?? s}`,
    ),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];

  function clearFilters() {
    setSearch("");
    setTypes([]);
    setSubTypes([]);
    setDesigns([]);
    setTrustServices([]);
    setFrameworkFilter([]);
    setOwners([]);
    setStatuses([]);
    setEvidence([]);
    setModes([]);
    setSystems([]);
  }

  if (controlsQuery.isError) {
    const failure = describeError(controlsQuery.error, "control library");
    return (
      <div className="w-full">
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          // No "Try again" on a 403 or a 404: retrying changes nothing.
          onRetry={
            failure.retryable ? () => void controlsQuery.refetch() : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Compliance"
        title="Controls library"
        icon="controls"
        subtitle={subtitle}
        actions={
          <>
            {canExport ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" loading={exporting !== null}>
                    <Icon name="export" className="size-4" />
                    Export
                    <Icon name="chev" className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onSelect={() => void handleExport("pdf")}>
                    PDF report
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => void handleExport("xlsx")}>
                    Excel workbook
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => void handleExport("csv")}>
                    CSV
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
            {canManage ? (
              <Button onClick={() => setCreating(true)}>
                <Icon name="plus" className="size-4" />
                New control
              </Button>
            ) : null}
          </>
        }
      />

      <Toolbar
        searchLabel="Filter controls"
        search={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by name, code or criterion…"
            aria-label="Search controls"
          />
        }
      >
        {vocabulary ? (
          <>
            <FilterFacet
              label="Framework"
              options={frameworkOptions}
              values={frameworkFilter}
              onChange={setFrameworkFilter}
            />
            <FilterFacet
              label="Trust Services"
              options={TRUST_SERVICES.map((v) => ({ value: v, label: v }))}
              values={trustServices}
              onChange={setTrustServices}
            />
            <FilterFacet
              label="Type"
              options={vocabulary.categories.map((v) => ({
                value: v,
                label: v,
              }))}
              values={types}
              onChange={changeTypes}
            />
            <FilterFacet
              label="Sub-type"
              options={subTypeOptions}
              values={subTypes}
              onChange={setSubTypes}
            />
            <FilterFacet
              label="Design"
              options={vocabulary.control_types.map((v) => ({
                value: v,
                label: v,
              }))}
              values={designs}
              onChange={setDesigns}
            />
            <FilterFacet
              label="Owner"
              options={ownerOptions.map((option) =>
                option.value === "unassigned"
                  ? { ...option, label: withCount(option.label, unowned) }
                  : option,
              )}
              values={owners}
              onChange={setOwners}
            />
            <FilterFacet
              label="Status"
              options={[
                ...vocabulary.statuses.map((v) => ({
                  value: v,
                  label: STATUS_LABEL[v],
                })),
                { value: "disabled", label: "Disabled" },
              ]}
              values={statuses}
              onChange={setStatuses}
            />
            <FilterFacet
              label="Evidence"
              options={[
                { value: "with", label: "Has evidence" },
                {
                  value: "none",
                  label: evidenceKnown
                    ? withCount("No evidence", noEvidence)
                    : "No evidence",
                },
              ]}
              values={evidence}
              onChange={setEvidence}
            />
          </>
        ) : null}
        {composition.data ? (
          <>
            <FilterFacet
              label="Evidenced by"
              options={COMPOSE_MODES.map((mode) => ({
                value: mode,
                label: withCount(MODE[mode].label, modeCounts[mode]),
              }))}
              values={modes}
              onChange={(next) => changeModes(next as ComposeMode[])}
            />
            {!peopleOnly && systemList.length > 0 ? (
              <FilterFacet
                label="System"
                options={systemList.map((option) => ({
                  value: option.value,
                  label: withCount(option.label, option.count),
                }))}
                values={systems}
                onChange={setSystems}
              />
            ) : null}
          </>
        ) : null}
        {activeFilters.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      <p aria-live="polite" className="mb-4 text-caption text-text-subtle">
        Showing <span className="tabular">{visible.length}</span> of{" "}
        <span className="tabular">{controls.length}</span> controls
      </p>

      {controlsQuery.isLoading || waitingOnComposition ? (
        <TableSkeleton rows={10} density="comfortable" />
      ) : controls.length === 0 ? (
        // First use: the library exists as templates but has not been adopted.
        <EmptyState
          icon="controls"
          title="Your control library is empty"
          description="Build it from the shipped SOC 2 template library, with every control already mapped to the criteria it satisfies."
          action={
            canManage ? (
              <Button
                loading={adoptMutation.isPending}
                onClick={() => adoptMutation.mutate()}
              >
                Build my control library
              </Button>
            ) : undefined
          }
        />
      ) : visible.length === 0 ? (
        <EmptyState
          variant="no-match"
          title="No controls match your filters"
          description={`Try removing ${activeFilters
            .map((name) => `'${name}'`)
            .join(" or ")}.`}
          onClearFilters={clearFilters}
        />
      ) : (
        <Table
          density="comfortable"
          // Tighter cells than the default 16px: Type and Sub-type join a table
          // that already filled a 1440px screen, and Status must stay on it.
          className="[&_td]:px-2 [&_th]:px-2"
          actions={
            <>
              <span className="text-body-sm text-text-subtle">Group by</span>
              <SegmentedControl
                label="Group controls by"
                items={GROUP_ITEMS}
                value={groupBy}
                onChange={(next) => {
                  setGroupBy(next);
                  setPage(1);
                }}
              />
              <ColumnPicker {...cols} />
            </>
          }
        >
          <THead>
            <TR>
              {/* Selection exists to drive bulk actions — without the
                  permission to act there is nothing to select for. */}
              {canManage ? (
                <TH className="w-8">
                  <Checkbox
                    checked={
                      allChecked
                        ? true
                        : checkedVisibleCount > 0
                          ? "indeterminate"
                          : false
                    }
                    onCheckedChange={(next) =>
                      setCheckedIds((previous) => {
                        const onPage = paged.map((control) => control.id);
                        // Adds/removes this page only, leaving a selection made
                        // on another page intact.
                        return next
                          ? [...new Set([...previous, ...onPage])]
                          : previous.filter((id) => !onPage.includes(id));
                      })
                    }
                    aria-label="Select all controls on this page"
                  />
                </TH>
              ) : null}
              <TH {...thProps("control")}>Control</TH>
              {cols.isVisible("type") ? (
                <TH {...thProps("type")}>Type</TH>
              ) : null}
              {cols.isVisible("subtype") ? (
                <TH {...thProps("subtype")}>Sub-type</TH>
              ) : null}
              {cols.isVisible("description") ? <TH>Description</TH> : null}
              {cols.isVisible("trust") ? <TH>Trust services</TH> : null}
              {cols.isVisible("criteria") ? <TH>Criteria</TH> : null}
              {cols.isVisible("frameworks") ? <TH>Frameworks</TH> : null}
              {cols.isVisible("owner") ? (
                <TH {...thProps("owner")}>Owner</TH>
              ) : null}
              {cols.isVisible("evidence") ? (
                <TH numeric {...thProps("evidence")}>
                  Evidence
                </TH>
              ) : null}
              {cols.isVisible("status") ? (
                <TH {...thProps("status")}>Status</TH>
              ) : null}
              <TH className="w-11">
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {paged.flatMap((control, index) => {
              const tsc = tscFor(control);
              const frameworks = frameworksFor(control);
              const evidenceCount = evidenceCounts.get(control.id) ?? 0;
              const isChecked = checkedIds.includes(control.id);
              // A header whenever the group changes between neighbouring rows,
              // the first row of every page included: a page boundary can cut a
              // group in two, and the second half must still say which group it is.
              const group = groupOf(control);
              const startsGroup =
                groupBy !== "none" &&
                (index === 0 || group !== groupOf(paged[index - 1]));
              const continuesFromPreviousPage =
                index === 0 &&
                pageStart > 0 &&
                groupOf(ordered[pageStart - 1]) === group;
              const row = (
                <TR
                  key={control.id}
                  onClick={() => navigate(`/controls/${control.id}`)}
                  selected={isChecked}
                  className="cursor-pointer"
                >
                  {/* The checkbox is inside the row's click target, so its cell
                      stops propagation — selecting must not also open the row. */}
                  {canManage ? (
                    <TD onClick={(event) => event.stopPropagation()}>
                      <Checkbox
                        checked={isChecked}
                        onCheckedChange={(next) =>
                          setCheckedIds((previous) =>
                            next
                              ? [...previous, control.id]
                              : previous.filter((id) => id !== control.id),
                          )
                        }
                        aria-label={`Select ${control.code}`}
                      />
                    </TD>
                  ) : null}
                  <TD>
                    <div className="max-w-48">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-caption text-text-subtle">
                          {control.code}
                        </span>
                        {/* What evidences the control, beside its code: a column of
                            its own would push Status off a 1440 screen. */}
                        {cols.isVisible("evidencedBy") &&
                        compositionById.get(control.id) ? (
                          <>
                            <EvidencedBy
                              composition={compositionById.get(control.id)!.composition}
                              size={16}
                            />
                            <MonitoringWord
                              status={compositionById.get(control.id)!.automation_status}
                            />
                          </>
                        ) : null}
                        {/* Design is authored on internal controls only. */}
                        {control.origin === "custom" ? (
                          <>
                            <Badge variant="role">Internal</Badge>
                            {control.control_type ? (
                              <DesignChip label={control.control_type} />
                            ) : null}
                          </>
                        ) : null}
                      </div>
                      <span
                        className="mt-0.5 block truncate text-body-md font-medium text-text-primary"
                        title={control.name}
                      >
                        {control.name}
                      </span>
                    </div>
                  </TD>
                  {cols.isVisible("type") ? (
                    <TD>
                      <p
                        className="line-clamp-3 text-body-sm text-text-secondary"
                        title={control.category}
                      >
                        {control.category}
                      </p>
                    </TD>
                  ) : null}
                  {cols.isVisible("subtype") ? (
                    <TD>
                      {control.sub_category ? (
                        <p
                          className="line-clamp-3 text-body-sm text-text-secondary"
                          title={control.sub_category}
                        >
                          {control.sub_category}
                        </p>
                      ) : (
                        <span className="text-body-sm text-text-subtle">
                          Not set
                        </span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("description") ? (
                    <TD>
                      <p
                        className="line-clamp-2 max-w-[360px] text-body-sm text-text-secondary"
                        title={control.description}
                      >
                        {control.description || (
                          <span className="text-text-subtle">
                            No description
                          </span>
                        )}
                      </p>
                    </TD>
                  ) : null}
                  {cols.isVisible("trust") ? (
                    <TD>
                      {tsc.length ? (
                        <div className="flex flex-wrap gap-1">
                          {tsc.map((t) => (
                            <TrustServiceChip key={t} tsc={t} />
                          ))}
                        </div>
                      ) : (
                        <span className="text-text-subtle">None</span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("criteria") ? (
                    <TD>
                      <div className="flex max-w-[140px] flex-wrap gap-1">
                        {control.requirement_keys.length ? (
                          control.requirement_keys.map((key) => (
                            <span
                              key={key}
                              className="rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption font-medium text-text-secondary"
                            >
                              {key.replace(/^[A-Z0-9]+:/, "")}
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
                  {cols.isVisible("frameworks") ? (
                    <TD>
                      {frameworks.length ? (
                        <div className="flex flex-wrap gap-1">
                          {frameworks.map((framework) => (
                            <FrameworkChip key={framework} label={framework} />
                          ))}
                        </div>
                      ) : (
                        <span className="text-text-subtle">None</span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("owner") ? (
                    <TD>
                      {control.owner_name ? (
                        <span className="flex items-center gap-2">
                          <Avatar name={control.owner_name} size="sm" />
                          <span className="max-w-[104px] truncate text-body-sm text-text-secondary">
                            {control.owner_name}
                          </span>
                        </span>
                      ) : (
                        <span className="text-body-sm text-text-subtle">
                          Unassigned
                        </span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("evidence") ? (
                    <TD numeric>
                      {evidenceKnown ? (
                        <span
                          className={cn(
                            "inline-flex items-center gap-1.5",
                            evidenceCount === 0
                              ? "text-text-subtle"
                              : "text-text-secondary",
                          )}
                        >
                          <Icon name="doc" className="size-3.5" />
                          {evidenceCount}
                        </span>
                      ) : (
                        <span className="text-text-subtle">Unknown</span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("status") ? (
                    <TD>
                      <StatusPill
                        status={displayStatus(control).family}
                        label={displayStatus(control).label}
                      />
                    </TD>
                  ) : null}
                  <TD
                    className="text-right"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Actions for ${control.code}`}
                        >
                          <Icon name="more" className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => view(control)}>
                          View
                        </DropdownMenuItem>
                        {canManage ? (
                          <>
                            {/* The API refuses to patch a disabled control, so
                                the form is not offered for one. */}
                            {control.disabled_at ? null : (
                              <DropdownMenuItem
                                onSelect={() => setEditing(control)}
                              >
                                Edit
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {control.disabled_at ? (
                              <DropdownMenuItem onSelect={() => view(control)}>
                                Re-enable
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                variant="danger"
                                onSelect={() => {
                                  setConfirmDisable(true);
                                  setSelectedId(control.id);
                                }}
                              >
                                Disable
                              </DropdownMenuItem>
                            )}
                          </>
                        ) : null}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TD>
                </TR>
              );
              return startsGroup
                ? [
                    <tr key={`${control.id}-group`} className="bg-surface-hover">
                      <th
                        scope="colgroup"
                        colSpan={columnCount}
                        className="h-9 text-left align-middle"
                      >
                        <span className="inline-flex items-center gap-2 font-sans text-label-sm font-semibold text-text-primary">
                          {group}
                          <Badge variant="neutral">
                            {groupCounts.get(group)}
                          </Badge>
                          {continuesFromPreviousPage ? (
                            <span className="font-normal text-text-subtle">
                              continued
                            </span>
                          ) : null}
                        </span>
                      </th>
                    </tr>,
                    row,
                  ]
                : [row];
            })}
          </TBody>
        </Table>
      )}

      {/* Paging. Sits below the table and states the exact window, so "20 of
          117" is never left to inference. Hidden while there is nothing to
          page through. */}
      {visible.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-body-sm text-text-subtle">Rows per page</span>
            <Select
              value={
                PAGE_SIZES.includes(pageSize) ? String(pageSize) : "custom"
              }
              onValueChange={(value) => {
                setCustomSize(value === "custom");
                if (value !== "custom") setPageSize(Number(value));
                setPage(1);
              }}
            >
              <SelectTrigger
                aria-label="Rows per page"
                className="h-8 w-[96px]"
              />
              <SelectContent>
                {PAGE_SIZES.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
                <SelectItem value="custom">Custom…</SelectItem>
              </SelectContent>
            </Select>
            {customSize || !PAGE_SIZES.includes(pageSize) ? (
              <input
                type="number"
                min={1}
                max={500}
                defaultValue={pageSize}
                aria-label="Custom rows per page"
                // Committed on blur/Enter, not per keystroke — re-slicing the
                // table on every digit makes "1" render one row mid-typing.
                onKeyDown={(event) => {
                  if (event.key === "Enter") event.currentTarget.blur();
                }}
                onBlur={(event) => {
                  const next = Math.min(
                    500,
                    Math.max(
                      1,
                      Number(event.target.value) || DEFAULT_PAGE_SIZE,
                    ),
                  );
                  event.target.value = String(next);
                  setPageSize(next);
                  setPage(1);
                }}
                className="h-8 w-20 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary outline-none focus:border-action-accent focus:shadow-input-focus"
              />
            ) : null}
            <span className="tabular text-body-sm text-text-subtle">
              {pageStart + 1} to {Math.min(pageStart + pageSize, visible.length)}{" "}
              of {visible.length}
            </span>
          </div>

          <Pagination
            page={currentPage}
            pageCount={pageCount}
            onPageChange={setPage}
          />
        </div>
      ) : null}

      {canManage ? (
        <ControlsBulkBar
          selected={checkedControls}
          onClear={() => setCheckedIds([])}
        />
      ) : null}

      <ControlDetailDialog
        control={selectedControl}
        canManage={canManage}
        autoConfirm={confirmDisable}
        onEdit={(control) => {
          setSelectedId(null);
          setEditing(control);
        }}
        onClose={() => setSelectedId(null)}
      />
      <ControlFormDialog
        mode="create"
        open={creating}
        onOpenChange={setCreating}
      />
      <ControlFormDialog
        mode="edit"
        control={editing}
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
      />
    </div>
  );
}
