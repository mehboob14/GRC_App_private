import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  CodeChip,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PersonSelect,
  RadioGroup,
  RadioGroupItem,
  SearchInput,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TextArea,
  TH,
  THead,
  Toolbar,
  TR,
  useToast,
  type StatusFamily,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { iamApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { useEntryState } from "@/lib/nav/entry-state";
import {
  downloadStatement,
  getStatement,
  putApplicability,
  type ApplicabilityRow,
  type ProvidedBy,
  type RequirementState,
} from "../frameworks-api";
import { useSelectedFramework } from "../use-frameworks";
import { StatementVersions } from "./statement-versions";

const STATE: Record<RequirementState, { label: string; family: StatusFamily }> = {
  met: { label: "Implemented", family: "success" },
  partly: { label: "In progress", family: "progress" },
  not_started: { label: "Not started", family: "neutral" },
  no_controls: { label: "No control", family: "warning" },
  excluded: { label: "Not needed", family: "pending" },
};

function Figure({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-md border border-border bg-surface-primary px-3 py-2.5">
      <p className="font-display text-numeral-sm tabular text-text-primary">{value}</p>
      <p className="text-caption text-text-subtle">{label}</p>
    </div>
  );
}

/**
 * The Statement of Applicability: every requirement of the framework with the
 * workspace's decision, the reason, who operates it and the controls behind it.
 * Implementation is read from those controls, never typed in, so the statement
 * cannot disagree with the rest of the platform.
 */
export function StatementPage() {
  const { principal } = useAuth();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));
  const { selected, isLoading: listLoading } = useSelectedFramework();
  const { toast } = useToast();

  const [search, setSearch] = useEntryState("soa.search", "");
  const [sections, setSections] = useEntryState<string[]>("soa.sections", []);
  const [decisions, setDecisions] = useEntryState<string[]>("soa.decisions", []);
  const [states, setStates] = useEntryState<string[]>("soa.states", []);
  const [editing, setEditing] = useState<ApplicabilityRow | null>(null);
  const [exporting, setExporting] = useState(false);

  const ready = Boolean(selected?.added && selected.scope_model === "applicability");
  const query = useQuery({
    queryKey: ["statement", selected?.framework_id],
    queryFn: () => getStatement(selected!.framework_id),
    enabled: ready,
  });
  const statement = query.data;
  const rows = useMemo(() => statement?.rows ?? [], [statement]);

  const sectionOptions = useMemo(() => {
    const seen: string[] = [];
    for (const row of rows) if (!seen.includes(row.category)) seen.push(row.category);
    return seen.map((value) => ({ value, label: value }));
  }, [rows]);

  const visible = useMemo(() => {
    const text = search.trim().toLowerCase();
    return rows.filter(
      (row) =>
        (sections.length === 0 || sections.includes(row.category)) &&
        (decisions.length === 0 || decisions.includes(row.applicable ? "applies" : "excluded")) &&
        (states.length === 0 || states.includes(row.state)) &&
        (text === "" || row.code.toLowerCase().includes(text) || row.name.toLowerCase().includes(text)),
    );
  }, [rows, search, sections, decisions, states]);

  const filtered = search.trim() !== "" || sections.length + decisions.length + states.length > 0;
  const clear = () => {
    setSearch("");
    setSections([]);
    setDecisions([]);
    setStates([]);
  };

  async function exportWorkbook() {
    if (!selected) return;
    setExporting(true);
    try {
      await downloadStatement(selected.framework_id);
    } catch (error: unknown) {
      toast({ title: errorToast(error, "statement"), tone: "danger" });
    } finally {
      setExporting(false);
    }
  }

  if (listLoading) return <Skeleton className="h-64 w-full rounded-lg" />;
  if (!ready || !selected) {
    return (
      <EmptyState
        icon="shield"
        title="No Statement of Applicability here"
        description="Choose a framework that works by applicability, such as ISO 27001, from the switch above. Add it from the Frameworks tab if it is not in your workspace yet."
        action={
          <Link to="/frameworks/list" className="text-body-md font-semibold text-text-link">
            Go to Frameworks
          </Link>
        }
      />
    );
  }
  if (query.isError) {
    const failure = describeError(query.error, "statement of applicability");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const summary = statement?.summary;

  return (
    <div>
      {summary ? (
        <div className="mb-4 grid grid-cols-3 gap-2.5 sm:grid-cols-4 lg:grid-cols-7">
          <Figure value={summary.total} label="Requirements" />
          <Figure value={summary.applicable} label="Apply" />
          <Figure value={summary.excluded} label="Excluded" />
          <Figure value={summary.met} label="Implemented" />
          <Figure value={summary.partly} label="In progress" />
          <Figure value={summary.not_started} label="Not started" />
          <Figure value={summary.no_controls} label="No control" />
        </div>
      ) : null}

      <Toolbar
        searchLabel="Filter requirements"
        search={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by reference or title"
            aria-label="Search requirements"
          />
        }
        actions={
          <>
            <StatementVersions
              frameworkId={selected.framework_id}
              canApprove={canManage}
            />
            <Button variant="secondary" size="sm" loading={exporting} onClick={() => void exportWorkbook()}>
              <Icon name="download" className="size-4" />
              Export XLSX
            </Button>
          </>
        }
      >
        <FilterFacet label="Section" options={sectionOptions} values={sections} onChange={setSections} />
        <FilterFacet
          label="Decision"
          options={[
            { value: "applies", label: "Applies" },
            { value: "excluded", label: "Excluded" },
          ]}
          values={decisions}
          onChange={setDecisions}
        />
        <FilterFacet
          label="Implementation"
          options={(Object.keys(STATE) as RequirementState[])
            .filter((s) => s !== "excluded")
            .map((s) => ({ value: s, label: STATE[s].label }))}
          values={states}
          onChange={setStates}
        />
        {filtered ? (
          <Button variant="ghost" size="sm" onClick={clear}>
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      <div className="mt-4">
        {query.isLoading ? (
          <TableSkeleton rows={8} density="comfortable" />
        ) : visible.length === 0 ? (
          <EmptyState
            variant="no-match"
            title="No requirements match your filters"
            description="Adjust or clear the filters."
            onClearFilters={filtered ? clear : undefined}
          />
        ) : (
          <Table density="comfortable">
            <THead>
              <TR>
                <TH>Requirement</TH>
                <TH>Decision</TH>
                <TH>Implementation</TH>
                <TH>Controls</TH>
                <TH>Owner</TH>
                <TH className="w-24">
                  <span className="sr-only">Edit</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {visible.map((row) => {
                const state = STATE[row.state];
                return (
                  <TR key={row.requirement_id}>
                    <TD>
                      <div className="flex items-start gap-2.5">
                        <CodeChip code={row.code} />
                        <span className="min-w-0">
                          <span className="block text-body-md text-text-primary">{row.name}</span>
                          <span className="block text-caption text-text-subtle">{row.category}</span>
                        </span>
                      </div>
                    </TD>
                    <TD>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <StatusPill
                          kind="inline"
                          status={row.applicable ? "neutral" : "pending"}
                          label={row.applicable ? "Applies" : "Excluded"}
                        />
                        {row.provided_by === "supplier" ? <Badge variant="role">Supplier</Badge> : null}
                      </div>
                      {row.justification ? (
                        <p className="mt-1 line-clamp-2 max-w-xs text-caption text-text-subtle" title={row.justification}>
                          {row.justification}
                        </p>
                      ) : null}
                    </TD>
                    <TD>
                      <StatusPill kind="inline" status={state.family} label={state.label} />
                    </TD>
                    <TD>
                      <div className="flex flex-wrap gap-1">
                        {row.controls.slice(0, 3).map((control) => (
                          <Link key={control.control_id} to={`/controls/${control.control_id}`} title={control.name}>
                            <CodeChip code={control.code} />
                          </Link>
                        ))}
                        {row.controls.length > 3 ? (
                          <span className="text-caption text-text-subtle">+{row.controls.length - 3}</span>
                        ) : null}
                        {row.controls.length === 0 ? (
                          <span className="text-caption text-text-subtle">None</span>
                        ) : null}
                      </div>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">{row.owner_name ?? "Unassigned"}</span>
                    </TD>
                    <TD className="text-right">
                      {canManage ? (
                        <Button variant="ghost" size="sm" onClick={() => setEditing(row)} aria-label={`Decide ${row.code}`}>
                          Decide
                        </Button>
                      ) : null}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        )}
      </div>

      <DecisionDialog frameworkId={selected.framework_id} row={editing} onClose={() => setEditing(null)} />
    </div>
  );
}

function DecisionDialog({
  frameworkId,
  row,
  onClose,
}: {
  frameworkId: string;
  row: ApplicabilityRow | null;
  onClose: () => void;
}) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));
  const selfId = principal?.membership_id ?? "";

  // Seeded from the row each time it opens, so a second requirement never inherits the first's text.
  const [seed, setSeed] = useState<string | null>(null);
  const [applies, setApplies] = useState(true);
  const [reason, setReason] = useState("");
  const [providedBy, setProvidedBy] = useState<ProvidedBy>("organization");
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(true);
  if (row && seed !== row.requirement_id) {
    setSeed(row.requirement_id);
    setApplies(row.applicable);
    setReason(row.justification ?? "");
    setProvidedBy(row.provided_by);
    setOwnerId(row.owner_membership_id);
    setReviewed(true);
  }
  if (!row && seed !== null) setSeed(null);

  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: row !== null && canReadMembers,
  });
  const people = canReadMembers
    ? (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.full_name, email: m.email }))
    : principal
      ? [{ id: selfId, name: principal.user.full_name }]
      : [];

  const save = useMutation({
    mutationFn: () =>
      putApplicability(frameworkId, row!.requirement_id, {
        applicable: applies,
        justification: reason.trim() || null,
        provided_by: providedBy,
        owner_membership_id: ownerId,
        reviewed,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["statement"] }),
        queryClient.invalidateQueries({ queryKey: ["compliance-dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["engagement-coverage"] }),
      ]);
      toast({ title: `${row?.code} saved`, tone: "success" });
      onClose();
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "requirement"), tone: "danger" }),
  });

  const needsReason = !applies && reason.trim() === "";

  return (
    <Dialog open={row !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent size="lg" scrollBody className="max-h-[88vh]">
        <DialogHeader>
          <DialogTitle>
            {row?.code} {row?.name}
          </DialogTitle>
          {row?.description ? <DialogDescription>{row.description}</DialogDescription> : null}
        </DialogHeader>
        <DialogBody>
          <div className="space-y-4">
            <fieldset>
              <legend className="mb-1.5 font-sans text-label-sm text-text-secondary">Does it apply?</legend>
              <RadioGroup value={applies ? "yes" : "no"} onValueChange={(v) => setApplies(v === "yes")}>
                <RadioGroupItem value="yes" label="It applies" description="The controls behind it are part of the management system." />
                <RadioGroupItem
                  value="no"
                  label="It does not apply"
                  description={
                    row?.locked
                      ? "Management system requirements apply to every organization and cannot be excluded."
                      : "Left out of scope. A reason is required and goes on the statement."
                  }
                  disabled={row?.locked}
                />
              </RadioGroup>
            </fieldset>

            <TextArea
              label={applies ? "Why it applies" : "Why it does not apply"}
              optional={applies}
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                applies
                  ? "The risk, obligation or contract that calls for it. The statement records a reason for every control included."
                  : "For example: no physical premises, the team is fully remote."
              }
            />

            {applies ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <SelectField label="Operated by">
                  <Select value={providedBy} onValueChange={(v) => setProvidedBy(v as ProvidedBy)}>
                    <SelectTrigger aria-label="Operated by" />
                    <SelectContent>
                      <SelectItem value="organization">Our organization</SelectItem>
                      <SelectItem value="supplier">A supplier, for example the hosting provider</SelectItem>
                    </SelectContent>
                  </Select>
                </SelectField>
                <div>
                  <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Owner</p>
                  <PersonSelect
                    people={people}
                    value={ownerId}
                    onChange={setOwnerId}
                    placeholder="Select owner"
                    clearLabel="No owner"
                    aria-label="Owner"
                  />
                </div>
              </div>
            ) : null}
            {applies && providedBy === "supplier" ? (
              <p className="text-body-sm text-text-subtle">
                Keep the supplier&apos;s certificate or report on their vendor record, so the statement has something to point to.
              </p>
            ) : null}

            <label className="flex cursor-pointer items-center gap-2.5 text-body-md text-text-primary">
              <Checkbox checked={reviewed} onCheckedChange={(v) => setReviewed(v === true)} />
              Mark as reviewed today
            </label>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={needsReason} loading={save.isPending} onClick={() => save.mutate()}>
            Save decision
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
