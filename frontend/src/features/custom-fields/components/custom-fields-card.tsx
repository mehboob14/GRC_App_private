import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  Switch,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { createCustomField, setCustomFieldArchived, updateCustomField } from "../api";
import { customFieldsKey, useCustomFields } from "../hooks";
import {
  CUSTOM_FIELD_TYPES,
  FIELD_TYPE_HINT,
  FIELD_TYPE_LABEL,
  type CustomFieldDefinition,
  type CustomFieldScope,
  type CustomFieldType,
} from "../types";

const BLANK = {
  label: "",
  field_type: "text" as CustomFieldType,
  optionText: "",
  help_text: "",
  required: false,
};

/**
 * The settings half of custom fields: what this workspace collects on a record,
 * in the order it is asked for. Archived rather than deleted, because a value
 * written last year has to stay readable after somebody stops collecting it.
 */
export function CustomFieldsCard({
  scope,
  noun,
  canEdit,
}: {
  scope: CustomFieldScope;
  /** What the records are called, for the copy: "asset", "finding". */
  noun: string;
  canEdit: boolean;
}) {
  // "a finding", "an asset": the copy reads either way round and a wrong
  // article is the first thing a reader notices.
  const article = /^[aeiou]/i.test(noun) ? "an" : "a";
  const fieldsQuery = useCustomFields(scope, true);
  const [editing, setEditing] = useState<CustomFieldDefinition | null>(null);
  const [open, setOpen] = useState(false);
  const fields = fieldsQuery.data ?? [];
  const active = fields.filter((f) => !f.archived);
  const archived = fields.filter((f) => f.archived);

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-title-sm text-text-primary">Custom fields</h2>
          <p className="mt-1 text-body-sm text-text-secondary">
            Extra questions this workspace asks on every {noun}. They appear on the {noun}
            itself, in the order below.
          </p>
        </div>
        {canEdit ? (
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Icon name="plus" className="size-4" />
            Add field
          </Button>
        ) : null}
      </div>

      {!canEdit ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          You can view these settings. Editing needs the Manage permission.
        </p>
      ) : null}

      {fieldsQuery.isPending ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-14 w-full rounded-md" />
          <Skeleton className="h-14 w-full rounded-md" />
        </div>
      ) : fieldsQuery.isError ? (
        <div className="mt-4">
          <ErrorState
            title={describeError(fieldsQuery.error, "custom fields").title}
            description={describeError(fieldsQuery.error, "custom fields").message}
            onRetry={() => void fieldsQuery.refetch()}
          />
        </div>
      ) : fields.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            icon="textbox"
            title="No custom fields yet"
            description={`Add one to collect something this platform does not ask for on ${article} ${noun}.`}
          />
        </div>
      ) : (
        <div className="mt-4 divide-y divide-border">
          {[...active, ...archived].map((f) => (
            <FieldRow
              key={f.id}
              field={f}
              scope={scope}
              canEdit={canEdit}
              onEdit={() => {
                setEditing(f);
                setOpen(true);
              }}
            />
          ))}
        </div>
      )}

      <FieldDialog
        scope={scope}
        field={editing}
        position={active.length}
        open={open}
        onOpenChange={setOpen}
      />
    </div>
  );
}

function FieldRow({
  field,
  scope,
  canEdit,
  onEdit,
}: {
  field: CustomFieldDefinition;
  scope: CustomFieldScope;
  canEdit: boolean;
  onEdit: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const archive = useMutation({
    mutationFn: () => setCustomFieldArchived(scope, field.id, !field.archived),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["custom-fields", scope] });
      toast({
        title: field.archived ? `${field.label} is collected again` : `${field.label} archived`,
        tone: "success",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "custom field"), tone: "danger" }),
  });

  return (
    <div className="flex items-center gap-3 py-3">
      <span className="grid size-8 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-subtle">
        <Icon name="textbox" className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 text-label-md text-text-primary">
          {field.label}
          <Badge variant="neutral">{FIELD_TYPE_LABEL[field.field_type]}</Badge>
          {field.required && !field.archived ? <Badge variant="statusPending">Required</Badge> : null}
          {field.archived ? <Badge variant="neutral">Archived</Badge> : null}
        </p>
        <p className="truncate text-caption text-text-subtle">
          {field.field_type === "select" && field.options.length
            ? field.options.join(" · ")
            : (field.help_text ?? field.key)}
        </p>
      </div>
      {canEdit ? (
        <div className="flex shrink-0 items-center gap-1.5">
          {!field.archived ? (
            <Button variant="ghost" size="sm" onClick={onEdit}>
              Edit
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            loading={archive.isPending}
            onClick={() => archive.mutate()}
          >
            {field.archived ? "Restore" : "Archive"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function FieldDialog({
  scope,
  field,
  position,
  open,
  onOpenChange,
}: {
  scope: CustomFieldScope;
  field: CustomFieldDefinition | null;
  position: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(BLANK);
  const editing = field !== null;

  useEffect(() => {
    if (!open) return;
    setForm(
      field
        ? {
            label: field.label,
            field_type: field.field_type,
            optionText: field.options.join("\n"),
            help_text: field.help_text ?? "",
            required: field.required,
          }
        : BLANK,
    );
  }, [open, field]);

  const options = form.optionText
    .split("\n")
    .map((o) => o.trim())
    .filter(Boolean);

  const save = useMutation({
    mutationFn: () => {
      const body = {
        label: form.label.trim(),
        field_type: form.field_type,
        options: form.field_type === "select" ? options : [],
        help_text: form.help_text.trim() || null,
        required: form.required,
        position: field ? field.position : position,
      };
      return field
        ? updateCustomField(scope, field.id, body)
        : createCustomField(scope, body);
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: customFieldsKey(scope, true) });
      void queryClient.invalidateQueries({ queryKey: customFieldsKey(scope, false) });
      toast({ title: editing ? `${saved.label} saved` : `${saved.label} added`, tone: "success" });
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "custom field"), tone: "danger" }),
  });

  const incomplete =
    !form.label.trim() || (form.field_type === "select" && options.length === 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md" scrollBody className="max-h-[88vh] p-0">
        <DialogHeader className="border-b border-border px-6 pb-4 pt-5">
          <DialogTitle>{editing ? `Edit ${field.label}` : "Add a field"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "The type cannot change once values are written against it."
              : "It appears on the form the next time somebody opens it."}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            if (!incomplete) save.mutate();
          }}
        >
          <DialogBody className="mx-0 space-y-3.5 px-6 py-5">
            <TextField
              label="Field name"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="Cost centre"
              autoFocus
            />
            <SelectField label="Type">
              <Select
                value={form.field_type}
                onValueChange={(v) => setForm((f) => ({ ...f, field_type: v as CustomFieldType }))}
                disabled={editing}
              >
                <SelectTrigger aria-label="Field type" />
                <SelectContent>
                  {CUSTOM_FIELD_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {FIELD_TYPE_LABEL[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <p className="text-body-sm text-text-subtle">{FIELD_TYPE_HINT[form.field_type]}</p>

            {form.field_type === "select" ? (
              <TextArea
                label="Choices"
                rows={4}
                value={form.optionText}
                onChange={(e) => setForm((f) => ({ ...f, optionText: e.target.value }))}
                placeholder={"CC-100\nCC-200"}
                hint="One per line."
              />
            ) : null}

            <TextField
              label="Helper text"
              optional
              value={form.help_text}
              onChange={(e) => setForm((f) => ({ ...f, help_text: e.target.value }))}
              placeholder="Shown under the field on the form"
            />

            <div className="flex items-center justify-between rounded-lg border border-border bg-surface-sunken px-3.5 py-3">
              <span>
                <span className="block text-label-md text-text-primary">Required</span>
                <span className="block text-caption text-text-subtle">
                  Applies the next time each record is saved, not to records already stored.
                </span>
              </span>
              <Switch
                checked={form.required}
                onCheckedChange={(v) => setForm((f) => ({ ...f, required: v }))}
                aria-label="Required"
              />
            </div>
          </DialogBody>
          <DialogFooter className="mt-0 border-t border-border px-6 py-4">
            <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending} disabled={incomplete}>
              {editing ? "Save changes" : "Add field"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
