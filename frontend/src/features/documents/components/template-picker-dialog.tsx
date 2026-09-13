import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorState,
  Icon,
  SearchInput,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { createDocumentFromTemplate, listPolicyTemplates } from "../api";
import type { PolicyTemplate } from "../types";

/**
 * Start from a written policy instead of a blank page.
 *
 * Each template becomes a *copy* in the tenant's register — from that moment the
 * wording is theirs, and nothing upstream can change it. Two workspaces starting
 * from the same policy never see each other's edits.
 *
 * The count of placeholders is shown up front on purpose. A template is not a
 * finished policy: it says things like "reviewed on a {{frequency}} basis", and
 * that is a decision the customer has to make and then live up to. Better they
 * know before they start than discover it at the audit.
 */

export function TemplatePickerDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const query = useQuery({ queryKey: ["policy-templates"], queryFn: listPolicyTemplates });

  const create = useMutation({
    mutationFn: async (keys: string[]) => {
      // Sequential, not Promise.all: each one takes the next document code, and
      // racing them would fight over it.
      const made = [];
      for (const key of keys) made.push(await createDocumentFromTemplate({ template_key: key }));
      return made;
    },
    onSuccess: async (made) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      onOpenChange(false);
      setSelected(new Set());
      toast({
        title:
          made.length === 1
            ? `${made[0].title} added as a draft`
            : `${made.length} policies added as drafts`,
        tone: "success",
      });
      if (made.length === 1) navigate(`/documents/${made[0].id}`);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "template"), tone: "danger" }),
  });

  const templates = query.data ?? [];
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return templates;
    return templates.filter(
      (t) =>
        t.title.toLowerCase().includes(needle) ||
        (t.summary ?? "").toLowerCase().includes(needle) ||
        t.tags.some((tag) => tag.toLowerCase().includes(needle)) ||
        Object.values(t.satisfies)
          .flat()
          .some((c) => c.toLowerCase().includes(needle)),
    );
  }, [templates, search]);

  const toggle = (key: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const attribution = templates.find((t) => t.source_url && t.license);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setSearch("");
          setSelected(new Set());
        }
        onOpenChange(next);
      }}
    >
      <DialogContent
        className="flex max-h-[90vh] w-[min(96vw,60rem)] max-w-none flex-col"
        aria-describedby={undefined}
      >
        <DialogHeader>
          <DialogTitle>Start a draft from a template</DialogTitle>
        </DialogHeader>

        <DialogBody className="min-h-0 flex-1 overflow-y-auto">
          {query.isError ? (
            <ErrorState
              title="Couldn't load the templates"
              description={describeError(query.error, "template library").message}
              onRetry={() => void query.refetch()}
            />
          ) : query.isLoading ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">Loading templates…</p>
          ) : (
            <>
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Search templates"
                className="mb-3"
              />
              {filtered.length === 0 ? (
                <p className="py-8 text-center text-body-sm text-text-subtle">
                  No template matches “{search}”.
                </p>
              ) : (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {filtered.map((template) => (
                    <TemplateCard
                      key={template.key}
                      template={template}
                      checked={selected.has(template.key)}
                      onToggle={() => toggle(template.key)}
                    />
                  ))}
                </ul>
              )}
            </>
          )}
        </DialogBody>

        <DialogFooter className="flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:justify-between">
          {/* Apache 2.0 requires attribution. Saying where the wording came from
              is also just honest: the customer is adopting someone else's text. */}
          {attribution ? (
            <p className="text-caption text-text-subtle">
              Templates from{" "}
              <a
                href={attribution.source_url ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="text-text-link hover:underline"
              >
                Openlane Policy Hub
              </a>
              , {attribution.license}.
            </p>
          ) : (
            <span />
          )}
          <div className="flex shrink-0 gap-2">
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              loading={create.isPending}
              disabled={selected.size === 0}
              onClick={() => create.mutate([...selected])}
            >
              {selected.size <= 1 ? "Create draft" : `Create ${selected.size} drafts`}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TemplateCard({
  template,
  checked,
  onToggle,
}: {
  template: PolicyTemplate;
  checked: boolean;
  onToggle: () => void;
}) {
  const criteria = Object.values(template.satisfies).flat();
  // company_name is filled in on creation, so it is not work for the reader.
  const toDecide = template.placeholders
    .filter((p) => p.key !== "company_name")
    .reduce((n, p) => n + p.count, 0);

  return (
    <li>
      <label
        className={cn(
          "flex h-full cursor-pointer gap-3 rounded-md border p-3 transition-colors",
          checked
            ? "border-action-accent bg-action-accent-tint"
            : "border-border hover:bg-surface-hover",
        )}
      >
        <Checkbox checked={checked} onCheckedChange={onToggle} className="mt-0.5 shrink-0" />
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="text-body-md font-semibold text-text-primary">{template.title}</span>
            {template.already_used ? (
              <Badge variant="neutral">Already added</Badge>
            ) : null}
          </span>
          {template.summary ? (
            <span className="mt-1 block line-clamp-2 text-body-sm text-text-secondary">
              {template.summary}
            </span>
          ) : null}
          <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-text-subtle">
            {criteria.length > 0 ? (
              <span className="flex items-center gap-1">
                <Icon name="shield" className="size-3.5" aria-hidden />
                {criteria.length} SOC 2 criteria
              </span>
            ) : null}
            {toDecide > 0 ? (
              <span className="flex items-center gap-1 text-status-warning-text">
                <Icon name="alert" className="size-3.5" aria-hidden />
                {toDecide} to fill in
              </span>
            ) : null}
          </span>
        </span>
      </label>
    </li>
  );
}
