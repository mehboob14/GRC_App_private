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
import { controlsApi, evidenceApi, iamApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { Control } from "@/lib/api/types";

type Option = { value: string; label: string; hint?: string };

/**
 * A dependency-free searchable multi-select. Expands inline rather than floating
 * in a popover, because the dialog it lives in is `overflow-y-auto` and would
 * clip an absolutely-positioned panel. Disabled mode renders the trigger with a
 * "Soon" tag for domains that are not built yet (risks, assets, vulnerabilities).
 */
function MultiSelect({
  label,
  optional,
  placeholder,
  options,
  selected,
  onChange,
  disabled,
  note,
  loading,
  emptyText = "No matches.",
}: {
  label: string;
  optional?: boolean;
  placeholder: string;
  options: Option[];
  selected: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  note?: string;
  loading?: boolean;
  emptyText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const byValue = useMemo(
    () => new Map(options.map((option) => [option.value, option])),
    [options],
  );
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(q) ||
        (option.hint ?? "").toLowerCase().includes(q),
    );
  }, [options, query]);

  function toggle(value: string, next: boolean) {
    onChange(
      next
        ? [...new Set([...selected, value])]
        : selected.filter((v) => v !== value),
    );
  }

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-sans text-label-sm text-text-secondary">
          {label}
          {optional ? (
            <span className="font-normal text-text-faint"> (optional)</span>
          ) : null}
        </span>
        {!disabled && selected.length > 0 ? (
          <span className="text-caption font-medium text-action-accent">
            {selected.length} selected
          </span>
        ) : null}
      </div>

      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-sm border border-border bg-surface-primary px-3 py-2 text-left text-body-sm",
          disabled
            ? "cursor-not-allowed"
            : "text-text-primary hover:border-border-strong",
        )}
      >
        <span className="truncate">
          {disabled ? (
            <span className="text-text-subtle">{note ?? placeholder}</span>
          ) : selected.length ? (
            `${selected.length} selected`
          ) : (
            <span className="text-text-subtle">{placeholder}</span>
          )}
        </span>
        {disabled ? (
          <span className="shrink-0 rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption uppercase tracking-wide text-text-subtle">
            Soon
          </span>
        ) : (
          <Icon
            name="chev"
            className={cn(
              "size-4 shrink-0 text-text-subtle transition-transform",
              open && "rotate-180",
            )}
          />
        )}
      </button>

      {!disabled && selected.length > 0 ? (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {selected.map((value) => (
            <span
              key={value}
              className="inline-flex items-center gap-1 rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption text-text-secondary"
            >
              {byValue.get(value)?.label ?? value}
              <button
                type="button"
                onClick={() => toggle(value, false)}
                className="text-text-subtle hover:text-text-primary"
                aria-label={`Remove ${byValue.get(value)?.label ?? value}`}
              >
                <Icon name="x" className="size-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      {open && !disabled ? (
        <div className="mt-2 rounded-sm border border-border">
          <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
            <Icon name="search" className="size-4 shrink-0 text-text-subtle" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search…"
              className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
            />
          </div>
          <div className="max-h-40 overflow-y-auto">
            {loading ? (
              <p className="px-3 py-4 text-center text-caption text-text-subtle">
                Loading…
              </p>
            ) : filtered.length === 0 ? (
              <p className="px-3 py-4 text-center text-caption text-text-subtle">
                {emptyText}
              </p>
            ) : (
              filtered.map((option) => {
                const checked = selected.includes(option.value);
                return (
                  <label
                    key={option.value}
                    className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 hover:bg-surface-hover"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(next) => toggle(option.value, Boolean(next))}
                      aria-label={option.label}
                    />
                    <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">
                      <span className="font-medium">{option.label}</span>
                      {option.hint ? (
                        <span className="text-text-subtle"> · {option.hint}</span>
                      ) : null}
                    </span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Author an internal control, or edit any control. One form for both: create
 * mints a `custom` (internal) control with a unique code; edit patches the
 * fields the API allows. SOC 2 controls keep their code and mechanism type.
 */
export function ControlFormDialog({
  mode,
  control,
  open,
  onOpenChange,
}: {
  mode: "create" | "edit";
  control?: Control | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const isInternal = mode === "create" || control?.origin === "custom";

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [subCategory, setSubCategory] = useState("");
  const [design, setDesign] = useState("Preventive");
  const [automation, setAutomation] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [evidencePrefilled, setEvidencePrefilled] = useState(false);

  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));
  const canReadEvidence = Boolean(principal?.permissions.includes("evidence:read"));

  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: open && canReadMembers,
  });
  const vocabularyQuery = useQuery({
    queryKey: ["control-vocabulary"],
    queryFn: () => controlsApi.vocabulary(),
    enabled: open,
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence"],
    queryFn: () => evidenceApi.list(),
    enabled: open && canReadEvidence,
  });
  const vocab = vocabularyQuery.data;

  const members = canReadMembers
    ? (membersQuery.data ?? [])
    : principal
      ? [{ membership_id: principal.membership_id, full_name: principal.user.full_name }]
      : [];

  const evidenceOptions: Option[] = useMemo(
    () =>
      (evidenceQuery.data ?? []).map((item) => ({
        value: item.id,
        label: item.title,
        hint: item.evidence_type.replace(/_/g, " "),
      })),
    [evidenceQuery.data],
  );
  // Suggestions for the chosen Type, from the shipped library. Not a closed list.
  const subCategoryOptions = vocab?.sub_categories[category] ?? [];

  // (Re)seed the form each time it opens, from the control on edit or blank on
  // create. Evidence links prefill separately once the list resolves.
  useEffect(() => {
    if (!open) return;
    setEvidencePrefilled(false);
    if (mode === "edit" && control) {
      setName(control.name);
      setCode(control.code);
      setDescription(control.description);
      setCategory(control.category);
      setSubCategory(control.sub_category ?? "");
      setDesign(control.control_type ?? "");
      setAutomation(control.control_sub_type ?? "");
      setOwnerId(control.owner_membership_id ?? "");
      setEvidenceIds([]);
    } else {
      setName("");
      setCode("");
      setDescription("");
      setCategory("");
      setSubCategory("");
      setDesign("Preventive");
      setAutomation("");
      setOwnerId(principal?.membership_id ?? "");
      setEvidenceIds([]);
    }
  }, [open, mode, control, principal?.membership_id]);

  // Prefill linked evidence once, when the list arrives (ControlOut carries no
  // evidence ids, so the linkage is read from the evidence list itself).
  useEffect(() => {
    if (!open || mode !== "edit" || !control || evidencePrefilled) return;
    if (!evidenceQuery.data) return;
    setEvidenceIds(
      evidenceQuery.data
        .filter((item) => item.control_ids.includes(control.id))
        .map((item) => item.id),
    );
    setEvidencePrefilled(true);
  }, [open, mode, control, evidenceQuery.data, evidencePrefilled]);

  // A new control needs a valid (constrained) category, so default to the first
  // once the vocabulary loads rather than submitting an empty one.
  useEffect(() => {
    if (open && mode === "create" && category === "" && vocab?.categories.length) {
      setCategory(vocab.categories[0]);
    }
  }, [open, mode, category, vocab]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return controlsApi.create({
          name: name.trim(),
          description: description.trim(),
          category: category.trim(),
          sub_category: subCategory || null,
          control_type: design,
          control_sub_type: automation || null,
          owner_membership_id: ownerId || null,
          evidence_ids: evidenceIds,
        });
      }
      return controlsApi.update(control!.id, {
        name: name.trim(),
        description: description.trim(),
        category: category.trim(),
        sub_category: subCategory,
        // Mechanism type is authored only on internal controls (spec).
        control_type: isInternal ? design : undefined,
        control_sub_type: automation || null,
        owner_membership_id: ownerId || null,
        clear_owner: ownerId === "",
        // Omitted until the link set has prefilled, so a quick save cannot wipe
        // existing links; once prefilled, the array replaces them wholesale.
        evidence_ids: evidencePrefilled ? evidenceIds : undefined,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
      toast({ title: mode === "create" ? "Control created" : "Control updated", tone: "success" });
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  const canSubmit =
    name.trim() !== "" && description.trim() !== "" && category.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" className="max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "New control" : "Edit control"}</DialogTitle>
          <p className="text-body-md text-text-secondary">
            {isInternal
              ? "Authored as an internal control"
              : `SOC 2 control · ${control?.code}`}
          </p>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
          <div className="col-span-2">
            <TextField
              label="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Quarterly privileged-access review"
            />
          </div>

          <div className="col-span-2">
            <TextField
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What the control does and how it operates."
            />
          </div>

          {mode === "edit" ? (
            <TextField label="Code" value={code} disabled onChange={() => {}} />
          ) : null}
          {/* The vocabulary feeds Type, Design and Automation, so one line covers
              all three rather than repeating the same failure. Type is the
              domain (the category); Sub-type the area inside it. */}
          <div>
            <SelectField label="Type">
              <Select
                value={category}
                onValueChange={(value) => {
                  setCategory(value);
                  setSubCategory("");
                }}
              >
                <SelectTrigger aria-label="Type" />
                <SelectContent>
                  {(vocab?.categories ?? []).map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            {vocabularyQuery.isError ? (
              <p className="mt-1 text-body-sm text-status-danger-text">
                {describeError(vocabularyQuery.error, "category list").message}
              </p>
            ) : null}
          </div>

          {/* Suggestions from the shipped library for the chosen Type; free text
              is allowed, so a workspace can name an area of its own. */}
          <div>
            <TextField
              label="Sub-type"
              optional
              list="control-sub-types"
              maxLength={100}
              value={subCategory}
              onChange={(event) => setSubCategory(event.target.value)}
              placeholder={subCategoryOptions[0] ?? ""}
            />
            <datalist id="control-sub-types">
              {subCategoryOptions.map((sub) => (
                <option key={sub} value={sub} />
              ))}
            </datalist>
          </div>

          {isInternal ? (
            <SelectField label="Design">
              <Select value={design} onValueChange={setDesign}>
                <SelectTrigger aria-label="Design" />
                <SelectContent>
                  {(vocab?.control_types ?? []).map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          ) : (
            <TextField label="Design" value={design} disabled onChange={() => {}} />
          )}

          <SelectField label="Automation" optional>
            <Select
              value={automation || "none"}
              onValueChange={(value) => setAutomation(value === "none" ? "" : value)}
            >
              <SelectTrigger aria-label="Automation" />
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                {(vocab?.control_sub_types ?? []).map((st) => (
                  <SelectItem key={st} value={st}>
                    {st}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>

          <div>
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
            {membersQuery.isError ? (
              <p className="mt-1 text-body-sm text-status-danger-text">
                {describeError(membersQuery.error, "team list").message}
              </p>
            ) : null}
          </div>
          <div />

          <div className="col-span-2">
            <MultiSelect
              label="Evidence"
              optional
              placeholder="Attach evidence…"
              options={evidenceOptions}
              selected={evidenceIds}
              onChange={setEvidenceIds}
              loading={evidenceQuery.isLoading}
              disabled={!canReadEvidence}
              note={canReadEvidence ? undefined : "Requires evidence access"}
              emptyText="No evidence yet."
            />
            {/* Without this the picker reads "No evidence yet", which is a
                claim about the library rather than about the request. */}
            {evidenceQuery.isError ? (
              <p className="mt-1 text-body-sm text-status-danger-text">
                {describeError(evidenceQuery.error, "evidence library").message}
              </p>
            ) : null}
          </div>

          {/* Risk, asset and vulnerability registers are not built yet
              (Phase 3). The selectors are shown disabled so the form reads the
              way it will once those modules land. */}
          <MultiSelect
            label="Risks"
            optional
            placeholder="Link risks…"
            options={[]}
            selected={[]}
            onChange={() => {}}
            disabled
            note="Risk register"
          />
          <MultiSelect
            label="Assets"
            optional
            placeholder="Link assets…"
            options={[]}
            selected={[]}
            onChange={() => {}}
            disabled
            note="Asset inventory"
          />
          <MultiSelect
            label="Vulnerabilities"
            optional
            placeholder="Link vulnerabilities…"
            options={[]}
            selected={[]}
            onChange={() => {}}
            disabled
            note="Vulnerability register"
          />
          <div />
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
            {mode === "create" ? "Create control" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
