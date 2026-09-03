import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { complianceApi, controlsApi, iamApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { CLASS_LABEL, TYPE_LABEL } from "../labels";
import {
  createDocument,
  updateDocument,
  uploadDocument,
} from "@/features/documents/api";
import {
  CLASSIFICATIONS,
  DOC_TYPES,
  type Classification,
  type Document,
  type DocType,
} from "@/features/documents/types";


type Option = { value: string; label: string };

/** Compact inline-expand multi-select (clip-safe inside the dialog). */
function MultiSelect({
  label,
  placeholder,
  options,
  selected,
  onChange,
  loading,
  error,
}: {
  label: string;
  placeholder: string;
  options: Option[];
  selected: string[];
  onChange: (next: string[]) => void;
  loading?: boolean;
  /** Set when the option list failed to load, so the empty list does not read as "none exist". */
  error?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const byValue = useMemo(() => new Map(options.map((o) => [o.value, o.label])), [options]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter((o) => o.label.toLowerCase().includes(q)) : options;
  }, [options, query]);
  const toggle = (value: string, next: boolean) =>
    onChange(next ? [...new Set([...selected, value])] : selected.filter((v) => v !== value));

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-sans text-label-sm text-text-secondary">
          {label} <span className="font-normal text-text-faint">(optional)</span>
        </span>
        {selected.length > 0 ? (
          <span className="text-caption font-medium text-action-accent">
            {selected.length} selected
          </span>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-sm border border-border bg-surface-primary px-3 py-2 text-left text-body-sm text-text-primary hover:border-border-strong"
      >
        <span className="truncate">
          {selected.length ? `${selected.length} selected` : (
            <span className="text-text-subtle">{placeholder}</span>
          )}
        </span>
        <Icon
          name="chev"
          className={cn("size-4 shrink-0 text-text-subtle transition-transform", open && "rotate-180")}
        />
      </button>
      {selected.length > 0 ? (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {selected.map((value) => (
            <span
              key={value}
              className="inline-flex items-center gap-1 rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption text-text-secondary"
            >
              {byValue.get(value) ?? value}
              <button
                type="button"
                onClick={() => toggle(value, false)}
                className="text-text-subtle hover:text-text-primary"
                aria-label={`Remove ${byValue.get(value) ?? value}`}
              >
                <Icon name="x" className="size-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}
      {open ? (
        <div className="mt-2 rounded-sm border border-border">
          <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
            <Icon name="search" className="size-4 shrink-0 text-text-subtle" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
            />
          </div>
          <div className="max-h-40 overflow-y-auto">
            {error ? (
              <p className="px-3 py-4 text-center text-body-sm text-status-danger-text">{error}</p>
            ) : loading ? (
              <p className="px-3 py-4 text-center text-caption text-text-subtle">Loading…</p>
            ) : filtered.length === 0 ? (
              <p className="px-3 py-4 text-center text-caption text-text-subtle">No matches.</p>
            ) : (
              filtered.map((option) => (
                <label
                  key={option.value}
                  className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 hover:bg-surface-hover"
                >
                  <Checkbox
                    checked={selected.includes(option.value)}
                    onCheckedChange={(next) => toggle(option.value, Boolean(next))}
                    aria-label={option.label}
                  />
                  <span className="text-body-sm text-text-primary">{option.label}</span>
                </label>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function DocumentFormDialog({
  mode,
  document: doc,
  open,
  onOpenChange,
}: {
  mode: "create" | "edit";
  document?: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));

  const [source, setSource] = useState<"upload" | "blank">("blank");
  const [ownerId, setOwnerId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [docType, setDocType] = useState<DocType>("policy");
  const [classification, setClassification] = useState<Classification>("internal");
  const [frameworkIds, setFrameworkIds] = useState<string[]>([]);
  const [controlIds, setControlIds] = useState<string[]>([]);

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
  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: open && canReadMembers,
  });
  const members = membersQuery.data ?? [];

  const frameworkOptions: Option[] = useMemo(
    () => (frameworksQuery.data ?? []).map((f) => ({ value: f.id, label: f.name })),
    [frameworksQuery.data],
  );
  const controlOptions: Option[] = useMemo(
    () =>
      (controlsQuery.data ?? [])
        .filter((c) => !c.disabled_at)
        .map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` })),
    [controlsQuery.data],
  );

  useEffect(() => {
    if (!open) return;
    setSource("blank");
    setFile(null);
    if (mode === "edit" && doc) {
      setTitle(doc.title);
      setDescription(doc.description);
      setDocType(doc.doc_type);
      setClassification(doc.classification);
      // The document carries framework names + control codes; map back to ids.
      const fwByName = new Map((frameworksQuery.data ?? []).map((f) => [f.name, f.id]));
      const ctByCode = new Map((controlsQuery.data ?? []).map((c) => [c.code, c.id]));
      setFrameworkIds(doc.frameworks.map((n) => fwByName.get(n)).filter(Boolean) as string[]);
      setControlIds(doc.controls.map((c) => ctByCode.get(c)).filter(Boolean) as string[]);
      setOwnerId(doc.owner?.membership_id ?? "");
    } else {
      setTitle("");
      setDescription("");
      setDocType("policy");
      setClassification("internal");
      setFrameworkIds([]);
      setControlIds([]);
      setOwnerId(principal?.membership_id ?? "");
    }
  }, [open, mode, doc, frameworksQuery.data, controlsQuery.data, principal?.membership_id]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (mode === "edit" && doc) {
        return updateDocument(doc.id, {
          title,
          description: description || null,
          doc_type: docType,
          classification,
          owner_membership_id: ownerId || undefined,
          clear_owner: ownerId === "",
          framework_ids: frameworkIds,
          control_ids: controlIds,
        });
      }
      if (source === "upload" && file) {
        const created = await uploadDocument(file, {
          title,
          doc_type: docType,
          classification,
          description: description || null,
        });
        if (frameworkIds.length || controlIds.length || ownerId) {
          await updateDocument(created.id, {
            owner_membership_id: ownerId || undefined,
            framework_ids: frameworkIds,
            control_ids: controlIds,
          });
        }
        return created;
      }
      return createDocument({
        title,
        description: description || null,
        doc_type: docType,
        classification,
        owner_membership_id: ownerId || null,
        framework_ids: frameworkIds,
        control_ids: controlIds,
      });
    },
    onSuccess: () => {
      toast({
        title: mode === "create" ? "Document created" : "Document updated",
        tone: "success",
      });
      onOpenChange(false);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  const canSubmit =
    title.trim() !== "" && (mode === "edit" || source === "blank" || file !== null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" className="max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "New document" : "Edit document"}</DialogTitle>
          <p className="text-body-md text-text-secondary">
            {mode === "create"
              ? "Upload an existing file, or start a document you'll author in-app."
              : `Editing ${doc?.code ?? ""}`}
          </p>
        </DialogHeader>

        <div className="space-y-3">
          {mode === "create" ? (
            <div className="grid grid-cols-2 gap-2">
              {(["blank", "upload"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSource(s)}
                  className={cn(
                    "rounded-sm border px-3 py-2.5 text-left",
                    source === s
                      ? "border-action-accent bg-action-accent-tint"
                      : "border-border hover:border-border-strong",
                  )}
                >
                  <span className="flex items-center gap-2 text-body-md font-medium text-text-primary">
                    <Icon name={s === "blank" ? "doc" : "download"} className="size-4" />
                    {s === "blank" ? "Author in-app" : "Upload a file"}
                  </span>
                  <span className="mt-0.5 block text-caption text-text-subtle">
                    {s === "blank"
                      ? "Write and version it in the editor"
                      : "PDF or Word, kept in the register"}
                  </span>
                </button>
              ))}
            </div>
          ) : null}

          {mode === "create" && source === "upload" ? (
            <label className="flex cursor-pointer items-center justify-between gap-3 rounded-sm border border-dashed border-border px-3 py-3 hover:border-border-strong">
              <span className="flex items-center gap-2 text-body-sm text-text-secondary">
                <Icon name="download" className="size-4 text-text-subtle" />
                {file?.name ?? "Choose a PDF or Word file…"}
              </span>
              <span className="rounded-xs bg-surface-sunken px-2 py-1 text-caption text-text-secondary">
                Browse
              </span>
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          ) : null}

          <TextField
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Acceptable Use Policy"
          />
          <TextField
            label="Description"
            optional
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this document covers."
          />

          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <SelectField label="Document type">
              <Select value={docType} onValueChange={(v) => setDocType(v as DocType)}>
                <SelectTrigger aria-label="Document type" />
                <SelectContent>
                  {DOC_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {TYPE_LABEL[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Classification">
              <Select
                value={classification}
                onValueChange={(v) => setClassification(v as Classification)}
              >
                <SelectTrigger aria-label="Classification" />
                <SelectContent>
                  {CLASSIFICATIONS.map((c) => (
                    <SelectItem key={c} value={c}>
                      {CLASS_LABEL[c]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>

            <SelectField label="Owner" optional>
              <Select
                value={ownerId || "none"}
                onValueChange={(v) => setOwnerId(v === "none" ? "" : v)}
              >
                <SelectTrigger aria-label="Owner" />
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {members.map((m) => (
                    <SelectItem key={m.membership_id} value={m.membership_id}>
                      {m.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {membersQuery.isError ? (
                <p className="mt-1 text-body-sm text-status-danger-text">
                  {describeError(membersQuery.error, "member list").message}
                </p>
              ) : null}
            </SelectField>
            <div />

            <MultiSelect
              label="Frameworks"
              placeholder="Link frameworks…"
              options={frameworkOptions}
              selected={frameworkIds}
              onChange={setFrameworkIds}
              loading={frameworksQuery.isLoading}
              error={
                frameworksQuery.isError
                  ? describeError(frameworksQuery.error, "framework list").message
                  : undefined
              }
            />
            <MultiSelect
              label="Controls"
              placeholder="Link controls…"
              options={controlOptions}
              selected={controlIds}
              onChange={setControlIds}
              loading={controlsQuery.isLoading}
              error={
                controlsQuery.isError
                  ? describeError(controlsQuery.error, "control list").message
                  : undefined
              }
            />
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
            {mode === "create" ? "Create document" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
