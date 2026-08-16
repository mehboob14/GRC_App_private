import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  EmptyState,
  ErrorState,
  FilterFacet,
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
import { controlsApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { Control, ControlStatus } from "@/lib/api/types";

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

/** Type is a taxonomy, not a status — neutral chips (DS §1, F12). */
function TypeChip({ label }: { label: string }) {
  return <Badge variant="neutral">{label}</Badge>;
}

function ControlDrawer({
  control,
  onClose,
  canManage,
}: {
  control: Control | null;
  onClose: () => void;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);

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
  });

  return (
    <Drawer
      open={control !== null}
      onOpenChange={(open) => {
        if (!open) {
          setConfirming(false);
          setReason("");
          onClose();
        }
      }}
    >
      <DrawerContent size="lg">
        {control ? (
          <>
            <DrawerHeader>
              <DrawerTitle className="flex flex-wrap items-center gap-2">
                <span className="rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link">
                  {control.code}
                </span>
                {control.name}
              </DrawerTitle>
              <DrawerDescription>{control.description}</DrawerDescription>
            </DrawerHeader>

            <DrawerBody className="space-y-5">
              {control.disabled_at ? (
                <div className="rounded-md border border-status-neutral-border bg-status-neutral-bg px-3.5 py-3">
                  <p className="text-label-md text-status-neutral-text">
                    Disabled — {control.disabled_reason}
                  </p>
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="type-overline mb-1.5">Type</p>
                  <TypeChip label={control.control_type} />
                </div>
                <div>
                  <p className="type-overline mb-1.5">Sub-type</p>
                  {control.control_sub_type ? (
                    <TypeChip label={control.control_sub_type} />
                  ) : (
                    <span className="text-body-sm text-text-subtle">—</span>
                  )}
                </div>
                <div>
                  <p className="type-overline mb-1.5">Category</p>
                  <p className="text-body-sm text-text-secondary">
                    {control.category}
                  </p>
                </div>
                <div>
                  <p className="type-overline mb-1.5">Owner</p>
                  <p className="text-body-sm text-text-secondary">
                    {control.owner_name ?? "Unassigned"}
                  </p>
                </div>
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
            </DrawerBody>

            {canManage ? (
              <DrawerFooter>
                {control.disabled_at ? (
                  <Button
                    variant="secondary"
                    loading={enableMutation.isPending}
                    onClick={() => enableMutation.mutate()}
                  >
                    Re-enable control
                  </Button>
                ) : confirming ? (
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
                  <Button
                    variant="destructive-2"
                    onClick={() => setConfirming(true)}
                  >
                    Disable control
                  </Button>
                )}
              </DrawerFooter>
            ) : null}
          </>
        ) : null}
      </DrawerContent>
    </Drawer>
  );
}

/** Controls — the tenant's working library, instantiated from the shipped
 *  templates. Type, Sub-type, owner, status and mapped criteria per row. */
export function ControlsPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));

  const [search, setSearch] = useState("");
  const [types, setTypes] = useState<string[]>([]);
  const [subTypes, setSubTypes] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [selected, setSelected] = useState<Control | null>(null);

  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
  });
  const vocabularyQuery = useQuery({
    queryKey: ["control-vocabulary"],
    queryFn: () => controlsApi.vocabulary(),
  });

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
        (subTypes.length === 0 ||
          (control.control_sub_type !== null &&
            subTypes.includes(control.control_sub_type))) &&
        (statuses.length === 0 || statuses.includes(control.status)) &&
        (query === "" ||
          control.name.toLowerCase().includes(query) ||
          control.code.toLowerCase().includes(query) ||
          control.requirement_keys.some((key) =>
            key.toLowerCase().includes(query),
          )),
    );
  }, [controls, search, types, subTypes, statuses]);

  const activeFilters = [
    ...types.map((t) => `Type: ${t}`),
    ...subTypes.map((s) => `Sub-type: ${s}`),
    ...statuses.map((s) => `Status: ${STATUS_LABEL[s as ControlStatus] ?? s}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];

  function clearFilters() {
    setSearch("");
    setTypes([]);
    setSubTypes([]);
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
      <h1 className="font-display text-heading-lg text-text-primary">Controls</h1>
      <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
        Your working control library, instantiated from the shipped SOC 2
        templates. Each control shows what it does, how it is operated, and the
        criteria it satisfies.
      </p>

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
              label="Type"
              options={vocabulary.control_types.map((v) => ({
                value: v,
                label: v,
              }))}
              values={types}
              onChange={setTypes}
            />
            <FilterFacet
              label="Sub-type"
              options={vocabulary.control_sub_types.map((v) => ({
                value: v,
                label: v,
              }))}
              values={subTypes}
              onChange={setSubTypes}
            />
            <FilterFacet
              label="Status"
              options={vocabulary.statuses.map((v) => ({
                value: v,
                label: STATUS_LABEL[v],
              }))}
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
              <TH>Control</TH>
              <TH>Type</TH>
              <TH>Sub-type</TH>
              <TH>Owner</TH>
              <TH>Status</TH>
              <TH>Criteria</TH>
            </TR>
          </THead>
          <TBody>
            {visible.map((control) => (
              <TR
                key={control.id}
                onClick={() => setSelected(control)}
                className="cursor-pointer"
              >
                <TD>
                  <div className="flex items-start gap-2.5">
                    <span className="shrink-0 rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link">
                      {control.code}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-body-md text-text-primary">
                        {control.name}
                      </span>
                      {control.origin === "custom" ? (
                        <Badge variant="role" className="mt-1">
                          Custom
                        </Badge>
                      ) : null}
                    </span>
                  </div>
                </TD>
                <TD>
                  <TypeChip label={control.control_type} />
                </TD>
                <TD>
                  {control.control_sub_type ? (
                    <TypeChip label={control.control_sub_type} />
                  ) : (
                    <span className="text-text-subtle">—</span>
                  )}
                </TD>
                <TD>
                  <span
                    className={cn(
                      "text-body-sm",
                      control.owner_name
                        ? "text-text-secondary"
                        : "text-text-subtle",
                    )}
                  >
                    {control.owner_name ?? "Unassigned"}
                  </span>
                </TD>
                <TD>
                  <StatusPill
                    kind="inline"
                    status={STATUS_FAMILY[control.status]}
                    label={STATUS_LABEL[control.status]}
                  />
                </TD>
                <TD>
                  <div className="flex flex-wrap gap-1">
                    {control.requirement_keys.length ? (
                      control.requirement_keys.map((key) => (
                        <span
                          key={key}
                          className="rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption font-medium text-text-secondary"
                        >
                          {key.replace("SOC2:", "")}
                        </span>
                      ))
                    ) : (
                      <span className="text-caption text-status-warning-text">
                        None
                      </span>
                    )}
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <ControlDrawer
        control={selected}
        canManage={canManage}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
