import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  Icon,
  RadioGroup,
  RadioGroupItem,
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
import { controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { getAccessToken } from "@/lib/auth/session";
import type { Evidence, EvidenceFreshness } from "@/lib/api/types";

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

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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

function AddEvidenceDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [kind, setKind] = useState<"file" | "link">("file");
  const [title, setTitle] = useState("");
  const [evidenceType, setEvidenceType] = useState("screenshot");
  const [collectedAt, setCollectedAt] = useState(today());
  const [renewalDate, setRenewalDate] = useState("");
  const [sourceLabel, setSourceLabel] = useState("");
  const [description, setDescription] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [controlIds, setControlIds] = useState<string[]>([]);

  const vocabularyQuery = useQuery({
    queryKey: ["evidence-vocabulary"],
    queryFn: () => evidenceApi.vocabulary(),
  });
  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
  });

  const types = vocabularyQuery.data?.types ?? [];
  const selectedType = types.find((type) => type.value === evidenceType);

  function reset() {
    setKind("file");
    setTitle("");
    setEvidenceType("screenshot");
    setCollectedAt(today());
    setRenewalDate("");
    setSourceLabel("");
    setDescription("");
    setLinkUrl("");
    setFile(null);
    setControlIds([]);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (kind === "link") {
        return evidenceApi.addLink({
          title,
          link_url: linkUrl,
          evidence_type: evidenceType,
          collected_at: collectedAt,
          description: description || null,
          source_label: sourceLabel || null,
          // Blank means "use the type's default" — the server fills it in.
          renewal_date: renewalDate || null,
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
      if (renewalDate) form.append("renewal_date", renewalDate);
      for (const id of controlIds) form.append("control_ids", id);
      return evidenceApi.uploadFile(form);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
      toast({ title: "Evidence added", tone: "success" });
      reset();
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't add the evidence.",
        tone: "danger",
      }),
  });

  const canSubmit =
    title.trim() !== "" &&
    (kind === "link" ? linkUrl.trim() !== "" : file !== null);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add evidence</DialogTitle>
          <DialogDescription>
            Upload a file or image, or record a link. One item can satisfy more
            than one control.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <fieldset>
            <legend className="mb-1.5 font-sans text-label-sm text-text-secondary">
              Evidence is
            </legend>
            <RadioGroup
              value={kind}
              onValueChange={(value) => setKind(value as "file" | "link")}
            >
              <RadioGroupItem
                value="file"
                label="A file or image"
                description="Stored by Verity and hashed on upload, so its integrity is checkable later."
              />
              <RadioGroupItem
                value="link"
                label="A link"
                description="Points at a system Verity does not hold, so there is nothing to hash."
              />
            </RadioGroup>
          </fieldset>

          {kind === "file" ? (
            <div>
              <label
                htmlFor="evidence-file"
                className="mb-1.5 block font-sans text-label-sm text-text-secondary"
              >
                File
              </label>
              <input
                id="evidence-file"
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="block w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-secondary file:mr-3 file:rounded-sm file:border-0 file:bg-surface-sunken file:px-3 file:py-1.5 file:text-label-sm file:text-text-primary"
              />
            </div>
          ) : (
            <TextField
              label="Link URL"
              value={linkUrl}
              onChange={(event) => setLinkUrl(event.target.value)}
              placeholder="https://…"
            />
          )}

          <TextField
            label="Title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Q1 access review export"
          />

          <SelectField label="Evidence type">
            <Select value={evidenceType} onValueChange={setEvidenceType}>
              <SelectTrigger aria-label="Evidence type" />
              <SelectContent>
                {types.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label} · {type.default_validity_days}d
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>

          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Collected on"
              type="date"
              value={collectedAt}
              onChange={(event) => setCollectedAt(event.target.value)}
            />
            <TextField
              label="Renewal date"
              type="date"
              optional
              value={renewalDate}
              onChange={(event) => setRenewalDate(event.target.value)}
            />
          </div>
          {/* The type only suggests a period; a date typed above always wins. */}
          {!renewalDate && selectedType ? (
            <p className="-mt-1 text-caption text-text-subtle">
              Left blank, this becomes {selectedType.default_validity_days} days
              after collection — the default for {selectedType.label}. Set a date
              to override it.
            </p>
          ) : null}

          <TextField
            label="Source"
            optional
            value={sourceLabel}
            onChange={(event) => setSourceLabel(event.target.value)}
            placeholder="Okta admin console"
          />
          <TextField
            label="Description"
            optional
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />

          <SelectField label="Attach to a control" optional>
            <Select
              value={controlIds[0] ?? ""}
              onValueChange={(value) => setControlIds(value ? [value] : [])}
            >
              <SelectTrigger aria-label="Control" />
              <SelectContent>
                {(controlsQuery.data ?? []).map((control) => (
                  <SelectItem key={control.id} value={control.id}>
                    {control.code} — {control.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
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

function EvidenceDrawer({
  item,
  onClose,
}: {
  item: Evidence | null;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const meta = item ? FRESHNESS[item.freshness] : null;

  return (
    <Drawer open={item !== null} onOpenChange={(open) => !open && onClose()}>
      <DrawerContent size="lg">
        {item && meta ? (
          <>
            <DrawerHeader>
              <DrawerTitle>{item.title}</DrawerTitle>
              <DrawerDescription>
                {item.description || "No description recorded."}
              </DrawerDescription>
            </DrawerHeader>

            <DrawerBody className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={meta.family} label={meta.label} />
                <Badge variant="neutral">
                  {item.kind === "file" ? "File" : "Link"}
                </Badge>
                <Badge variant="neutral">
                  {item.evidence_type.replace(/_/g, " ")}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="type-overline mb-1.5">Owner</p>
                  <p className="text-body-sm text-text-secondary">
                    {item.owner_name ?? "Unassigned"}
                  </p>
                </div>
                <div>
                  <p className="type-overline mb-1.5">Source</p>
                  <p className="text-body-sm text-text-secondary">
                    {item.source_label ?? "—"}
                  </p>
                </div>
                <div>
                  <p className="type-overline mb-1.5">Collected</p>
                  <p className="text-body-sm text-text-secondary">
                    {formatDate(item.collected_at)}
                  </p>
                </div>
                <div>
                  <p className="type-overline mb-1.5">Renewal</p>
                  <p className="text-body-sm text-text-secondary">
                    {formatDate(item.renewal_date)}
                  </p>
                </div>
              </div>

              <div>
                <p className="type-overline mb-1.5">Supports controls</p>
                {item.control_codes.length ? (
                  <div className="flex flex-wrap gap-1">
                    {item.control_codes.map((code) => (
                      <span
                        key={code}
                        className="rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link"
                      >
                        {code}
                      </span>
                    ))}
                  </div>
                ) : (
                  // Unattached evidence proves nothing — say so rather than
                  // leaving an empty space that reads as fine.
                  <p className="text-body-sm text-status-warning-text">
                    Not attached to any control
                  </p>
                )}
              </div>

              {item.kind === "file" ? (
                <div className="rounded-md border border-border bg-surface-sunken p-3.5">
                  <p className="type-overline mb-2">Stored file</p>
                  <dl className="space-y-1.5 text-body-sm">
                    <div className="flex gap-2">
                      <dt className="w-24 shrink-0 text-text-subtle">Filename</dt>
                      <dd className="min-w-0 break-all text-text-secondary">
                        {item.filename}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="w-24 shrink-0 text-text-subtle">Type</dt>
                      <dd className="text-text-secondary">{item.content_type}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="w-24 shrink-0 text-text-subtle">Size</dt>
                      <dd className="tabular text-text-secondary">
                        {formatBytes(item.size_bytes)}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="w-24 shrink-0 text-text-subtle">SHA-256</dt>
                      <dd className="min-w-0 break-all font-mono text-caption text-text-secondary">
                        {item.sha256}
                      </dd>
                    </div>
                  </dl>
                  <p className="mt-2 text-caption text-text-subtle">
                    Recorded at upload. Re-hash a download and compare to prove
                    the file has not changed since.
                  </p>
                </div>
              ) : (
                <div>
                  <p className="type-overline mb-1.5">Link</p>
                  <a
                    href={item.link_url ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-body-sm font-semibold text-text-link"
                  >
                    {item.link_url}
                  </a>
                </div>
              )}
            </DrawerBody>

            {item.kind === "file" ? (
              <DrawerFooter>
                <Button
                  variant="secondary"
                  onClick={() =>
                    void downloadEvidence(item).catch(() =>
                      toast({
                        title: "Couldn't download the file.",
                        tone: "danger",
                      }),
                    )
                  }
                >
                  <Icon name="doc" className="size-4" />
                  Download
                </Button>
              </DrawerFooter>
            ) : null}
          </>
        ) : null}
      </DrawerContent>
    </Drawer>
  );
}

/** Evidence library — every artefact, what it proves, and whether it is still
 *  good. Freshness comes from the server, derived from the renewal date. */
export function EvidencePage() {
  const { principal } = useAuth();
  const canManage = Boolean(principal?.permissions.includes("evidence:manage"));

  const [search, setSearch] = useState("");
  const [freshnessFilter, setFreshnessFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [selected, setSelected] = useState<Evidence | null>(null);
  const [adding, setAdding] = useState(false);

  const evidenceQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => evidenceApi.list(),
  });
  const vocabularyQuery = useQuery({
    queryKey: ["evidence-vocabulary"],
    queryFn: () => evidenceApi.vocabulary(),
  });

  const items = useMemo(() => evidenceQuery.data ?? [], [evidenceQuery.data]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter(
      (item) =>
        (freshnessFilter.length === 0 ||
          freshnessFilter.includes(item.freshness)) &&
        (typeFilter.length === 0 || typeFilter.includes(item.evidence_type)) &&
        (query === "" ||
          item.title.toLowerCase().includes(query) ||
          (item.source_label ?? "").toLowerCase().includes(query) ||
          item.control_codes.some((code) => code.toLowerCase().includes(query))),
    );
  }, [items, search, freshnessFilter, typeFilter]);

  const counts = useMemo(() => {
    const by: Record<string, number> = {};
    for (const item of items) by[item.freshness] = (by[item.freshness] ?? 0) + 1;
    return by;
  }, [items]);

  const activeFilters = [
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
  }

  if (evidenceQuery.isError) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <ErrorState
          title="Couldn’t load evidence"
          description={
            evidenceQuery.error instanceof ApiError
              ? evidenceQuery.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          onRetry={() => void evidenceQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-heading-lg text-text-primary">
            Evidence
          </h1>
          <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
            Every artefact that proves a control operates. One item can support
            more than one control.
          </p>
        </div>
        {canManage ? (
          <Button className="shrink-0" onClick={() => setAdding(true)}>
            <Icon name="plus" className="size-4" />
            Add evidence
          </Button>
        ) : null}
      </div>

      {items.length > 0 ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {FRESHNESS_ORDER.map((state) => (
            <div
              key={state}
              className="flex items-center gap-2 rounded-md border border-border bg-surface-primary px-3 py-2"
            >
              <StatusPill
                kind="inline"
                status={FRESHNESS[state].family}
                label={FRESHNESS[state].label}
              />
              <span className="tabular font-display text-numeral-sm text-text-primary">
                {counts[state] ?? 0}
              </span>
            </div>
          ))}
        </div>
      ) : null}

      <div
        role="search"
        aria-label="Filter evidence"
        className="mb-4 mt-5 flex flex-wrap items-center gap-2"
      >
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by title, source or control…"
          aria-label="Search evidence"
          className="w-full sm:w-72"
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
        <p aria-live="polite" className="ml-auto text-caption text-text-subtle">
          Showing <span className="tabular">{visible.length}</span> of{" "}
          <span className="tabular">{items.length}</span> items
        </p>
      </div>

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
        <Table density="comfortable">
          <THead>
            <TR>
              <TH>Evidence</TH>
              <TH>Type</TH>
              <TH>Controls</TH>
              <TH>Owner</TH>
              <TH>Renewal</TH>
              <TH>Freshness</TH>
            </TR>
          </THead>
          <TBody>
            {visible.map((item) => (
              <TR
                key={item.id}
                onClick={() => setSelected(item)}
                className="cursor-pointer"
              >
                <TD>
                  <div className="flex items-start gap-2.5">
                    <Icon
                      name={item.kind === "file" ? "doc" : "globe"}
                      className="mt-0.5 size-4 shrink-0 text-text-subtle"
                      aria-hidden
                    />
                    <span className="min-w-0">
                      <span className="block text-body-md text-text-primary">
                        {item.title}
                      </span>
                      {item.source_label ? (
                        <span className="block truncate text-body-sm text-text-subtle">
                          {item.source_label}
                        </span>
                      ) : null}
                    </span>
                  </div>
                </TD>
                <TD>
                  <Badge variant="neutral">
                    {item.evidence_type.replace(/_/g, " ")}
                  </Badge>
                </TD>
                <TD>
                  <div className="flex flex-wrap gap-1">
                    {item.control_codes.length ? (
                      item.control_codes.map((code) => (
                        <span
                          key={code}
                          className="rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption font-medium text-text-secondary"
                        >
                          {code}
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
                  <span className="text-body-sm text-text-secondary">
                    {item.owner_name ?? "Unassigned"}
                  </span>
                </TD>
                <TD>
                  <span className="tabular text-body-sm text-text-secondary">
                    {formatDate(item.renewal_date)}
                  </span>
                </TD>
                <TD>
                  <StatusPill
                    kind="inline"
                    status={FRESHNESS[item.freshness].family}
                    label={FRESHNESS[item.freshness].label}
                  />
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <AddEvidenceDialog open={adding} onOpenChange={setAdding} />
      <EvidenceDrawer item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
