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
import { complianceApi, controlsApi, iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { Control } from "@/lib/api/types";

// Internal controls carry a mechanism type; SOC 2 controls keep the type they
// were shipped with, so the toggle is offered on authoring only (spec).
const INTERNAL_TYPES = ["Preventive", "Detective"];

function slug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
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
  const [codeEdited, setCodeEdited] = useState(false);
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [controlType, setControlType] = useState("Preventive");
  const [subType, setSubType] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [guidance, setGuidance] = useState("");
  const [criteriaKeys, setCriteriaKeys] = useState<string[]>([]);
  const [criteriaSearch, setCriteriaSearch] = useState("");

  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));
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
  const soc2 =
    frameworksQuery.data?.find((f) => f.code.toUpperCase().startsWith("SOC")) ??
    frameworksQuery.data?.[0];
  const requirementsQuery = useQuery({
    queryKey: ["requirements", soc2?.id],
    queryFn: () => complianceApi.listRequirements(soc2!.id),
    enabled: open && Boolean(soc2?.id),
  });
  // Category / type / sub-type are CHECK-constrained columns, so they come from
  // the server's vocabulary, never free text.
  const vocabularyQuery = useQuery({
    queryKey: ["control-vocabulary"],
    queryFn: () => controlsApi.vocabulary(),
    enabled: open,
  });
  const vocab = vocabularyQuery.data;

  const members = canReadMembers
    ? (membersQuery.data ?? [])
    : principal
      ? [{ membership_id: principal.membership_id, full_name: principal.user.full_name }]
      : [];
  const requirements = useMemo(() => requirementsQuery.data ?? [], [requirementsQuery.data]);

  // (Re)seed the form each time it opens, from the control on edit or blank on
  // create. Criteria are held as keys so prefill needs no async round-trip.
  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && control) {
      setName(control.name);
      setCode(control.code);
      setDescription(control.description);
      setCategory(control.category);
      setControlType(control.control_type);
      setSubType(control.control_sub_type ?? "");
      setOwnerId(control.owner_membership_id ?? "");
      setGuidance(control.implementation_guidance ?? "");
      setCriteriaKeys(control.requirement_keys);
    } else {
      setName("");
      setCode("");
      setCodeEdited(false);
      setDescription("");
      setCategory("");
      setControlType("Preventive");
      setSubType("");
      setOwnerId(principal?.membership_id ?? "");
      setGuidance("");
      setCriteriaKeys([]);
    }
    setCriteriaSearch("");
  }, [open, mode, control, principal?.membership_id]);

  // A new control needs a valid (constrained) category, so default to the first
  // once the vocabulary loads rather than submitting an empty one.
  useEffect(() => {
    if (open && mode === "create" && category === "" && vocab?.categories.length) {
      setCategory(vocab.categories[0]);
    }
  }, [open, mode, category, vocab]);

  const filteredCriteria = useMemo(() => {
    const q = criteriaSearch.trim().toLowerCase();
    if (!q) return requirements;
    return requirements.filter(
      (req) =>
        req.code.toLowerCase().includes(q) || req.name.toLowerCase().includes(q),
    );
  }, [requirements, criteriaSearch]);

  function requirementIds(): string[] {
    return requirements.filter((req) => criteriaKeys.includes(req.requirement_key)).map((req) => req.id);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return controlsApi.create({
          code: code.trim() || slug(name),
          name: name.trim(),
          description: description.trim(),
          category: category.trim(),
          control_type: controlType,
          control_sub_type: subType.trim() || null,
          implementation_guidance: guidance.trim() || null,
          owner_membership_id: ownerId || null,
          requirement_ids: requirementIds(),
        });
      }
      return controlsApi.update(control!.id, {
        name: name.trim(),
        description: description.trim(),
        category: category.trim(),
        // Mechanism type is authored only on internal controls (spec).
        control_type: isInternal ? controlType : undefined,
        control_sub_type: subType.trim() || null,
        implementation_guidance: guidance.trim() || null,
        owner_membership_id: ownerId || null,
        clear_owner: ownerId === "",
        requirement_ids: requirementIds(),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      toast({ title: mode === "create" ? "Control created" : "Control updated", tone: "success" });
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({
        title: error instanceof ApiError ? error.message : "Couldn't save the control.",
        tone: "danger",
      }),
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
              onChange={(event) => {
                setName(event.target.value);
                if (mode === "create" && !codeEdited) setCode(slug(event.target.value));
              }}
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

          <TextField
            label="Code"
            value={code}
            disabled={mode === "edit"}
            onChange={(event) => {
              setCode(event.target.value);
              setCodeEdited(true);
            }}
            placeholder="quarterly-access-review"
          />
          <SelectField label="Category">
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger aria-label="Category" />
              <SelectContent>
                {(vocab?.categories ?? []).map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>

          {isInternal ? (
            <SelectField label="Type">
              <Select value={controlType} onValueChange={setControlType}>
                <SelectTrigger aria-label="Type" />
                <SelectContent>
                  {INTERNAL_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          ) : (
            <TextField label="Type" value={controlType} disabled onChange={() => {}} />
          )}

          <SelectField label="Sub-type" optional>
            <Select
              value={subType || "none"}
              onValueChange={(value) => setSubType(value === "none" ? "" : value)}
            >
              <SelectTrigger aria-label="Sub-type" />
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
          <div />

          <div className="col-span-2">
            <TextField
              label="Implementation guidance"
              optional
              value={guidance}
              onChange={(event) => setGuidance(event.target.value)}
              placeholder="How to implement and operate this control."
            />
          </div>

          {/* Mapped criteria — optional searchable multi-select */}
          <div className="col-span-2">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="font-sans text-label-sm text-text-secondary">
                Mapped criteria <span className="font-normal text-text-faint">(optional)</span>
              </span>
              {criteriaKeys.length > 0 ? (
                <span className="text-caption font-medium text-action-accent">
                  {criteriaKeys.length} selected
                </span>
              ) : null}
            </div>
            <div className="mb-2 flex items-center gap-2 rounded-sm border border-border bg-surface-primary px-3 py-1.5">
              <Icon name="search" className="size-4 shrink-0 text-text-subtle" />
              <input
                type="text"
                value={criteriaSearch}
                onChange={(event) => setCriteriaSearch(event.target.value)}
                placeholder="Search criteria by code or name…"
                className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
              />
            </div>
            <div className="max-h-40 overflow-y-auto rounded-sm border border-border">
              {requirementsQuery.isLoading ? (
                <p className="px-3 py-4 text-center text-caption text-text-subtle">Loading criteria…</p>
              ) : filteredCriteria.length === 0 ? (
                <p className="px-3 py-4 text-center text-caption text-text-subtle">No criteria match.</p>
              ) : (
                filteredCriteria.map((req) => {
                  const checked = criteriaKeys.includes(req.requirement_key);
                  return (
                    <label
                      key={req.id}
                      className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 hover:bg-surface-hover"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(next) =>
                          setCriteriaKeys((prev) =>
                            next
                              ? [...new Set([...prev, req.requirement_key])]
                              : prev.filter((key) => key !== req.requirement_key),
                          )
                        }
                        aria-label={req.code}
                      />
                      <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">
                        <span className="font-medium">{req.code}</span>
                        <span className="text-text-subtle"> · {req.name}</span>
                      </span>
                    </label>
                  );
                })
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
            {mode === "create" ? "Create control" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
