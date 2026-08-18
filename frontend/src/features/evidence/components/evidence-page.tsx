import { useMemo, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
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
import { complianceApi, controlsApi, evidenceApi, iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { getAccessToken } from "@/lib/auth/session";
import type { Control, Evidence, EvidenceFreshness } from "@/lib/api/types";
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
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't add the evidence.",
        tone: "danger",
      }),
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
              <ControlPicker
                groups={groups}
                value={controlIds}
                onChange={setControlIds}
                loading={controlsQuery.isLoading}
              />
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
  const navigate = useNavigate();
  const { toast } = useToast();
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
              <TH>
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {visible.map((item) => (
              <TR
                key={item.id}
                onClick={() => navigate(`/evidence/${item.id}`)}
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
      <EvidenceDrawer item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
