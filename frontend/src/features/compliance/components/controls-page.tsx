import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  Checkbox,
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
  Pagination,
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
  TR,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { complianceApi, controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { Control, ControlStatus } from "@/lib/api/types";
import { OwnerSelect } from "@/features/iam/components/owner-select";
import { ControlFormDialog } from "./control-form-dialog";
import { ControlsBulkBar } from "./controls-bulk-bar";
import { FrameworkChip, TrustServiceChip } from "./trust-services";
import {
  TRUST_SERVICES,
  frameworksFor,
  trustServicesFor,
  type TrustService,
} from "@/features/compliance/trust-services";

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
function displayStatus(control: Control): { label: string; family: StatusFamily } {
  if (control.disabled_at) return { label: "Disabled", family: "neutral" };
  return { label: STATUS_LABEL[control.status], family: STATUS_FAMILY[control.status] };
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

/** Type is a taxonomy, not a status — neutral chips (DS §1, F12). */
function TypeChip({ label }: { label: string }) {
  return <Badge variant="neutral">{label}</Badge>;
}

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZES = [10, 20, 50, 100];

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
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't update the status.",
        tone: "danger",
      }),
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
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't disable the control.",
        tone: "danger",
      }),
  });

  const enableMutation = useMutation({
    mutationFn: () => controlsApi.enable(control!.id),
    onSuccess: async () => {
      await invalidate();
      toast({ title: "Control re-enabled", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't re-enable the control.",
        tone: "danger",
      }),
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
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't set the owner.",
        tone: "danger",
      }),
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
                    Disabled — {control.disabled_reason}
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
                    <span className="text-body-sm text-text-subtle">—</span>
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
                    <span className="text-body-sm text-text-subtle">—</span>
                  )}
                </div>
                {control.origin === "custom" ? (
                  <div>
                    <p className="type-overline mb-1.5">Type</p>
                    <TypeChip label={control.control_type} />
                  </div>
                ) : null}
                <div>
                  <p className="type-overline mb-1.5">Category</p>
                  <p className="text-body-sm text-text-secondary">
                    {control.category}
                  </p>
                </div>
              </div>

              {/* Owner is assignable in place — a control without a named owner
                  is the single most common audit finding. */}
              <div>
                <p className="type-overline mb-1.5">Owner</p>
                {canManage && !control.disabled_at ? (
                  <OwnerSelect
                    value={control.owner_membership_id}
                    valueLabel={control.owner_name}
                    onChange={(membershipId) => ownerMutation.mutate(membershipId)}
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
                  <p className="type-overline mb-1.5">Implementation guidance</p>
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
                      <li key={item.id} className="flex items-center gap-2 text-body-sm">
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
                        <Button variant="secondary" onClick={() => onEdit(control)}>
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

/** Controls — the tenant's working library, instantiated from the shipped
 *  templates. Code, description, Trust Services, mapped criteria, owner and
 *  status per row; Type shows on internal controls only, Sub-type is hidden. */
export function ControlsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));

  const [search, setSearch] = useState("");
  const [types, setTypes] = useState<string[]>([]);
  const [trustServices, setTrustServices] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [owners, setOwners] = useState<string[]>([]);
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
  // gated: without it the column reports "—" rather than a confident 0, which
  // would otherwise read as "this control has no evidence" — a fabricated
  // compliance finding.
  const canReadEvidence = Boolean(principal?.permissions.includes("evidence:read"));
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
      map.set(requirement.requirement_key, requirement.trust_services_category as TrustService);
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
      return found.size ? TRUST_SERVICES.filter((t) => found.has(t)) : trustServicesFor(control);
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
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't build the library.",
        tone: "danger",
      }),
  });

  const controls = useMemo(() => controlsQuery.data ?? [], [controlsQuery.data]);
  const vocabulary = vocabularyQuery.data;

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return controls.filter(
      (control) =>
        (types.length === 0 || types.includes(control.control_type)) &&
        (trustServices.length === 0 ||
          tscFor(control).some((tsc) => trustServices.includes(tsc))) &&
        (owners.length === 0 ||
          owners.includes(control.owner_membership_id ?? "unassigned")) &&
        (statuses.length === 0 ||
          statuses.includes(control.disabled_at ? "disabled" : control.status)) &&
        (query === "" ||
          control.name.toLowerCase().includes(query) ||
          control.code.toLowerCase().includes(query) ||
          (control.owner_name ?? "").toLowerCase().includes(query) ||
          control.requirement_keys.some((key) =>
            key.toLowerCase().includes(query),
          )),
    );
  }, [controls, search, types, trustServices, owners, statuses, tscFor]);

  // Selection survives filtering. Pruning to the visible rows would wipe a
  // selection on every search keystroke — you pick five controls, type to find
  // a sixth, and the first five are gone. The count stays honest instead by
  // resolving against the whole library, so the bar never names a row that no
  // longer exists.
  const checkedControls = useMemo(
    () => controls.filter((control) => checkedIds.includes(control.id)),
    [controls, checkedIds],
  );

  // --- Paging ---------------------------------------------------------------
  const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
  // Clamp rather than reset: narrowing a filter while on page 9 should land on
  // the last page that still exists, not silently show an empty table.
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const paged = useMemo(
    () => visible.slice(pageStart, pageStart + pageSize),
    [visible, pageStart, pageSize],
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
    return unassigned ? [...options, { value: "unassigned", label: "Unassigned" }] : options;
  }, [controls]);

  const ownerLabel = (value: string) =>
    ownerOptions.find((option) => option.value === value)?.label ?? value;

  // Header summary — real counts only, so the line stays true as data changes.
  const frameworkSummary = useMemo(() => {
    const all = new Set<string>();
    for (const control of controls) for (const f of frameworksFor(control)) all.add(f);
    const list = [...all].sort();
    if (list.length === 0) return "no framework yet";
    if (list.length === 1) return list[0];
    return `${list.slice(0, -1).join(", ")} and ${list[list.length - 1]}`;
  }, [controls]);
  const unowned = controls.filter(
    (control) => !control.owner_membership_id && !control.disabled_at,
  ).length;
  const noEvidence = controls.filter(
    (control) => !control.disabled_at && (evidenceCounts.get(control.id) ?? 0) === 0,
  ).length;

  const activeFilters = [
    ...types.map((t) => `Type: ${t}`),
    ...trustServices.map((t) => `Trust Services: ${t}`),
    ...owners.map((o) => `Owner: ${ownerLabel(o)}`),
    ...statuses.map((s) => `Status: ${STATUS_LABEL[s as ControlStatus] ?? s}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];

  function clearFilters() {
    setSearch("");
    setTypes([]);
    setTrustServices([]);
    setOwners([]);
    setStatuses([]);
  }

  if (controlsQuery.isError) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <ErrorState
          title="Couldn’t load controls"
          description={
            controlsQuery.error instanceof ApiError
              ? controlsQuery.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          referenceId={
            controlsQuery.error instanceof ApiError
              ? controlsQuery.error.correlationId
              : undefined
          }
          onRetry={() => void controlsQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="type-overline text-text-subtle">Compliance</p>
          <h1 className="mt-1 font-display text-heading-lg text-text-primary">Controls</h1>
          <p className="mt-1.5 text-body-lg text-text-secondary">
            <span className="tabular">{controls.length}</span> controls across{" "}
            {frameworkSummary}
            {unowned > 0 ? (
              <>
                {" · "}
                <span className="font-semibold text-status-warning-text">
                  {unowned} unassigned
                </span>
              </>
            ) : null}
            {evidenceKnown && noEvidence > 0 ? (
              <>
                {" · "}
                <span className="font-semibold text-text-primary">
                  {noEvidence} without evidence
                </span>
              </>
            ) : null}
          </p>
        </div>
        {canManage ? (
          <Button className="shrink-0" onClick={() => setCreating(true)}>
            <Icon name="plus" className="size-4" />
            New control
          </Button>
        ) : null}
      </div>

      <div
        role="search"
        aria-label="Filter controls"
        className="mb-4 mt-5 flex flex-wrap items-center gap-2"
      >
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by name, code or criterion…"
          aria-label="Search controls"
          className="w-full sm:w-72"
        />
        {vocabulary ? (
          <>
            <FilterFacet
              label="Trust Services"
              options={TRUST_SERVICES.map((v) => ({ value: v, label: v }))}
              values={trustServices}
              onChange={setTrustServices}
            />
            <FilterFacet
              label="Type"
              options={vocabulary.control_types.map((v) => ({
                value: v,
                label: v,
              }))}
              values={types}
              onChange={setTypes}
            />
            <FilterFacet
              label="Owner"
              options={ownerOptions}
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
          </>
        ) : null}
        {activeFilters.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
        <p aria-live="polite" className="ml-auto text-caption text-text-subtle">
          Showing <span className="tabular">{visible.length}</span> of{" "}
          <span className="tabular">{controls.length}</span> controls
        </p>
      </div>

      {controlsQuery.isLoading ? (
        <TableSkeleton rows={10} density="comfortable" />
      ) : controls.length === 0 ? (
        // First use: the library exists as templates but has not been adopted.
        <EmptyState
          icon="controls"
          title="Your control library is empty"
          description="Build it from the shipped SOC 2 template library — 114 controls, already mapped to the criteria they satisfy."
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
        <Table density="comfortable">
          <THead>
            <TR>
              {/* Selection exists to drive bulk actions — without the
                  permission to act there is nothing to select for. */}
              {canManage ? (
                <TH className="w-10">
                  <Checkbox
                    checked={
                      allChecked ? true : checkedVisibleCount > 0 ? "indeterminate" : false
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
              <TH>Control</TH>
              <TH>Trust Services</TH>
              <TH>Criteria</TH>
              <TH>Frameworks</TH>
              <TH>Owner</TH>
              <TH numeric>Evidence</TH>
              <TH>Status</TH>
              <TH className="w-20 text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {paged.map((control) => {
              const tsc = tscFor(control);
              const frameworks = frameworksFor(control);
              const evidenceCount = evidenceCounts.get(control.id) ?? 0;
              const isChecked = checkedIds.includes(control.id);
              return (
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
                    <div className="max-w-[320px]">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-caption text-text-subtle">
                          {control.code}
                        </span>
                        {/* Type is authored on internal controls only. */}
                        {control.origin === "custom" ? (
                          <>
                            <Badge variant="role">Internal</Badge>
                            <TypeChip label={control.control_type} />
                          </>
                        ) : null}
                      </div>
                      <span className="mt-0.5 block truncate text-body-md font-medium text-text-primary">
                        {control.name}
                      </span>
                    </div>
                  </TD>
                  <TD>
                    {tsc.length ? (
                      <div className="flex flex-wrap gap-1">
                        {tsc.map((t) => (
                          <TrustServiceChip key={t} tsc={t} />
                        ))}
                      </div>
                    ) : (
                      <span className="text-text-subtle">—</span>
                    )}
                  </TD>
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
                  <TD>
                    {frameworks.length ? (
                      <div className="flex flex-wrap gap-1">
                        {frameworks.map((framework) => (
                          <FrameworkChip key={framework} label={framework} />
                        ))}
                      </div>
                    ) : (
                      <span className="text-text-subtle">—</span>
                    )}
                  </TD>
                  <TD>
                    {control.owner_name ? (
                      <span className="flex items-center gap-2">
                        <Avatar name={control.owner_name} size="sm" />
                        <span className="truncate text-body-sm text-text-secondary">
                          {control.owner_name}
                        </span>
                      </span>
                    ) : (
                      <span className="text-body-sm text-text-subtle">Unassigned</span>
                    )}
                  </TD>
                  <TD numeric>
                    {evidenceKnown ? (
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5",
                          evidenceCount === 0 ? "text-text-subtle" : "text-text-secondary",
                        )}
                      >
                        <Icon name="doc" className="size-3.5" />
                        {evidenceCount}
                      </span>
                    ) : (
                      <span className="text-text-subtle">—</span>
                    )}
                  </TD>
                  <TD>
                    <StatusPill
                      kind="inline"
                      status={displayStatus(control).family}
                      label={displayStatus(control).label}
                    />
                  </TD>
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
                              <DropdownMenuItem onSelect={() => setEditing(control)}>
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
              value={PAGE_SIZES.includes(pageSize) ? String(pageSize) : "custom"}
              onValueChange={(value) => {
                setCustomSize(value === "custom");
                if (value !== "custom") setPageSize(Number(value));
                setPage(1);
              }}
            >
              <SelectTrigger aria-label="Rows per page" className="h-8 w-[96px]" />
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
                  const next = Math.min(500, Math.max(1, Number(event.target.value) || DEFAULT_PAGE_SIZE));
                  event.target.value = String(next);
                  setPageSize(next);
                  setPage(1);
                }}
                className="h-8 w-20 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary outline-none focus:border-action-accent focus:shadow-input-focus"
              />
            ) : null}
            <span className="tabular text-body-sm text-text-subtle">
              {pageStart + 1}–{Math.min(pageStart + pageSize, visible.length)} of{" "}
              {visible.length}
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
      <ControlFormDialog mode="create" open={creating} onOpenChange={setCreating} />
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
