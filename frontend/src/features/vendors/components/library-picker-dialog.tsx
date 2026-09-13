import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
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
  Icon,
  SearchInput,
  Skeleton,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { getQuestionnaireLibrary, importQuestions } from "../api";
import { TYPE_META } from "../questionnaire-logic";
import type { LibraryQuestion, LibraryTemplate, Questionnaire } from "../types";

const LEVEL_LABEL: Record<string, Record<string, string>> = {
  tiering: { lite: "Standard", core: "Extended", detail: "Extended" },
  due_diligence: { lite: "Lite", core: "Core", detail: "Full" },
};

/**
 * Pick library questions into a questionnaire. Grouped the way the library is
 * written, searchable, and a question already copied in is shown as added
 * rather than offered twice.
 */
export function LibraryPickerDialog({
  open,
  onOpenChange,
  questionnaire,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  questionnaire: Questionnaire;
  onAdded: (next: Questionnaire) => void;
}) {
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [templateCode, setTemplateCode] = useState<string | null>(null);

  const library = useQuery({
    queryKey: ["vendor-questionnaire-library", questionnaire.purpose],
    queryFn: () => getQuestionnaireLibrary(questionnaire.purpose),
    enabled: open,
  });

  const present = useMemo(
    () => new Set(questionnaire.questions.map((q) => q.library_code).filter(Boolean)),
    [questionnaire.questions],
  );
  const templates = library.data ?? [];
  const template: LibraryTemplate | undefined =
    templates.find((t) => t.code === templateCode) ?? templates[0];

  const groups = useMemo(() => {
    if (!template) return [];
    const needle = search.trim().toLowerCase();
    const rows = template.questions.filter(
      (q) => !needle || q.prompt.toLowerCase().includes(needle) || q.section.toLowerCase().includes(needle),
    );
    const out: { section: string; questions: LibraryQuestion[] }[] = [];
    for (const q of rows) {
      const group = out.find((g) => g.section === q.section);
      if (group) group.questions.push(q);
      else out.push({ section: q.section, questions: [q] });
    }
    return out;
  }, [template, search]);

  const close = (next: boolean) => {
    if (!next) {
      setPicked(new Set());
      setSearch("");
    }
    onOpenChange(next);
  };

  const add = useMutation({
    mutationFn: () => importQuestions(questionnaire.id, [...picked]),
    onSuccess: (next) => {
      const added = next.question_count - questionnaire.question_count;
      onAdded(next);
      toast({ title: `${added} ${added === 1 ? "question" : "questions"} added`, tone: "success" });
      close(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questions"), tone: "danger" }),
  });

  const toggle = (id: string, on: boolean) =>
    setPicked((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const available = (group: { questions: LibraryQuestion[] }) =>
    group.questions.filter((q) => !present.has(q.code));

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent size="lg" scrollBody className="max-h-[min(46rem,92vh)]">
        <DialogHeader>
          <DialogTitle>Add from library</DialogTitle>
        </DialogHeader>
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-5 pb-3">
          {templates.length > 1 ? (
            <div className="flex flex-wrap gap-1.5">
              {templates.map((t) => (
                <button
                  key={t.code}
                  type="button"
                  onClick={() => setTemplateCode(t.code)}
                  aria-pressed={t.code === template?.code}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-label-sm transition-colors duration-80 ease-state",
                    t.code === template?.code
                      ? "border-action-accent bg-action-accent-tint text-action-accent"
                      : "border-border text-text-secondary hover:bg-surface-hover",
                  )}
                >
                  {t.name}
                </button>
              ))}
            </div>
          ) : null}
          <SearchInput
            className="ml-auto w-full sm:w-56"
            placeholder="Search questions"
            value={search}
            onChange={setSearch}
          />
        </div>

        <DialogBody className="space-y-4">
          {library.isLoading ? <Skeleton className="h-64" /> : null}
          {groups.map((group) => {
            const open = available(group);
            const all = open.length > 0 && open.every((q) => picked.has(q.id));
            return (
              <section key={group.section}>
                <div className="mb-1.5 flex items-center gap-2">
                  <Checkbox
                    checked={all}
                    disabled={open.length === 0}
                    onCheckedChange={(on) => open.forEach((q) => toggle(q.id, on))}
                    aria-label={`Select all in ${group.section}`}
                  />
                  <h3 className="type-overline">{group.section}</h3>
                  <span className="tabular text-caption text-text-subtle">{group.questions.length}</span>
                </div>
                <ul className="divide-y divide-border overflow-hidden rounded-md border border-border">
                  {group.questions.map((q) => {
                    const added = present.has(q.code);
                    return (
                      <li key={q.id}>
                        <label
                          className={cn(
                            "flex items-start gap-3 px-3 py-2.5",
                            added ? "bg-surface-sunken/60" : "cursor-pointer hover:bg-surface-hover",
                          )}
                        >
                          <Checkbox
                            className="mt-0.5"
                            checked={added || picked.has(q.id)}
                            disabled={added}
                            onCheckedChange={(on) => toggle(q.id, on)}
                            aria-label={q.prompt}
                          />
                          <span className="min-w-0 flex-1">
                            <span className={cn("block text-body-md", added ? "text-text-subtle" : "text-text-primary")}>
                              {q.prompt}
                            </span>
                            <span className="mt-1 flex flex-wrap items-center gap-1.5 text-caption text-text-subtle">
                              <Icon name={TYPE_META[q.answer_type].icon} className="size-3.5" />
                              {TYPE_META[q.answer_type].label}
                              <span aria-hidden>·</span>
                              {LEVEL_LABEL[questionnaire.purpose]?.[q.scope_level] ?? q.scope_level}
                              {q.critical ? <Badge variant="countWarn">Critical</Badge> : null}
                              {q.evidence === "required" ? <Badge variant="neutral">Evidence</Badge> : null}
                              {q.condition_code ? <Badge variant="role">Follow up</Badge> : null}
                            </span>
                          </span>
                          {added ? <Badge variant="statusPass">Added</Badge> : null}
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
          {!library.isLoading && groups.length === 0 ? (
            <p className="py-10 text-center text-body-sm text-text-subtle">No questions match.</p>
          ) : null}
        </DialogBody>

        <DialogFooter className="justify-between">
          <span className="text-label-sm text-text-secondary">
            <span className="tabular">{picked.size}</span> selected
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => close(false)}>
              Cancel
            </Button>
            <Button disabled={picked.size === 0} loading={add.isPending} onClick={() => add.mutate()}>
              Add {picked.size || ""} {picked.size === 1 ? "question" : "questions"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
