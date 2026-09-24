import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ConfirmDialog,
  DetailHeader,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import {
  deleteQuestion,
  duplicateQuestionnaire,
  getFacets,
  getQuestionnaire,
  reorderQuestions,
  setQuestionnaireStatus,
} from "../api";
import { EVIDENCE_LABEL, isChoice, TYPE_META } from "../questionnaire-logic";
import type { BuilderQuestion, Questionnaire } from "../types";
import { fmtDate, TIER_META } from "../tokens";
import { LibraryPickerDialog } from "./library-picker-dialog";
import { QuestionEditor } from "./question-editor";
import { QuestionnairePreviewDialog } from "./questionnaire-preview-dialog";
import { QuestionnaireSettingsDialog } from "./questionnaire-settings-dialog";
import { ThresholdRuler } from "./threshold-ruler";
import { TierBadge } from "./tier-badge";

const PURPOSE_LABEL = { tiering: "Tiering", due_diligence: "Due diligence" } as const;

type Section = { name: string; questions: BuilderQuestion[] };

/** Consecutive questions sharing a section, in position order. */
function sectionsOf(questions: BuilderQuestion[]): Section[] {
  const out: Section[] = [];
  for (const q of questions) {
    const last = out[out.length - 1];
    if (last && last.name === q.section) last.questions.push(q);
    else out.push({ name: q.section, questions: [q] });
  }
  return out;
}

/**
 * Where a questionnaire is built: sections of questions down the page, an
 * outline and the add buttons beside them, and every edit in a panel so the
 * page never becomes a form.
 */
export function QuestionnaireBuilderPage() {
  const { questionnaireId = "" } = useParams();
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const key = ["vendor-questionnaire", questionnaireId];

  const query = useQuery({ queryKey: key, queryFn: () => getQuestionnaire(questionnaireId) });
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });

  const [editing, setEditing] = useState<{ question: BuilderQuestion | null; afterId: string | null } | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const apply = (next: Questionnaire) => {
    queryClient.setQueryData(key, next);
    void queryClient.invalidateQueries({ queryKey: ["vendor-questionnaires"] });
  };
  const fail = (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" });

  const reorder = useMutation({
    mutationFn: (ids: string[]) => reorderQuestions(questionnaireId, ids),
    onSuccess: apply,
    onError: fail,
  });
  const [removing, setRemoving] = useState<BuilderQuestion | null>(null);
  const remove = useMutation({
    mutationFn: (questionId: string) => deleteQuestion(questionnaireId, questionId),
    onSuccess: (next) => {
      apply(next);
      setRemoving(null);
      toast({ title: "Question removed", tone: "success" });
    },
    onError: fail,
  });
  const duplicate = useMutation({
    mutationFn: () => duplicateQuestionnaire(questionnaireId),
    onSuccess: (copy) => {
      void queryClient.invalidateQueries({ queryKey: ["vendor-questionnaires"] });
      toast({ title: "Questionnaire copied", tone: "success" });
      navigate(`/vendors/questionnaires/${copy.id}`);
    },
    onError: fail,
  });
  const status = useMutation({
    mutationFn: (next: "active" | "archived") => setQuestionnaireStatus(questionnaireId, next),
    onSuccess: (next) => {
      apply(next);
      toast({ title: next.status === "archived" ? "Archived" : "Restored", tone: "success" });
    },
    onError: fail,
  });

  const questionnaire = query.data;
  const sections = useMemo(() => sectionsOf(questionnaire?.questions ?? []), [questionnaire]);
  const numberOf = useMemo(
    () => new Map((questionnaire?.questions ?? []).map((q, i) => [q.id, i + 1])),
    [questionnaire],
  );

  if (query.isError) {
    const error = describeError(query.error, "questionnaire");
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        referenceId={error.referenceId}
        onRetry={error.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  if (!questionnaire) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const tiering = questionnaire.purpose === "tiering";
  const archived = questionnaire.status === "archived";
  const editable = canManage && !archived;
  const ids = questionnaire.questions.map((q) => q.id);

  const move = (question: BuilderQuestion, delta: -1 | 1) => {
    const from = ids.indexOf(question.id);
    const next = [...ids];
    [next[from], next[from + delta]] = [next[from + delta], next[from]];
    reorder.mutate(next);
  };
  const moveSection = (index: number, delta: -1 | 1) => {
    const order = [...sections];
    [order[index], order[index + delta]] = [order[index + delta], order[index]];
    reorder.mutate(order.flatMap((s) => s.questions.map((q) => q.id)));
  };

  return (
    <div className="w-full">
      <DetailHeader
        backTo={`/vendors/questionnaires${tiering ? "" : "?purpose=due_diligence"}`}
        backLabel="Back to Questionnaires"
        icon="checklist"
        title={questionnaire.name}
        chips={
          <>
            <Badge variant="neutral">{PURPOSE_LABEL[questionnaire.purpose]}</Badge>
            {questionnaire.is_default ? (
              <Badge variant="role">
                <Icon name="star" className="size-3" />
                Default
              </Badge>
            ) : null}
            {questionnaire.default_tiers.map((tier) => (
              <TierBadge key={tier} tier={tier} label={`${TIER_META[tier]?.label ?? tier} tier`} />
            ))}
            {archived ? <Badge variant="countWarn">Archived</Badge> : null}
          </>
        }
        meta={[
          `${questionnaire.question_count} questions`,
          `${questionnaire.section_count} sections`,
          `Updated ${fmtDate(questionnaire.updated_at)}`,
          questionnaire.updated_by_name,
        ]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => setPreviewOpen(true)}
              disabled={questionnaire.question_count === 0}
            >
              <Icon name="eye" className="size-4" />
              Preview
            </Button>
            {canManage ? (
              <>
                <Button variant="secondary" onClick={() => setSettingsOpen(true)}>
                  <Icon name="sliders" className="size-4" />
                  Settings
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="secondary" size="icon" aria-label="More actions">
                      <Icon name="more" className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => duplicate.mutate()}>
                      <Icon name="copy" className="size-4" />
                      Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      disabled={questionnaire.is_default && !archived}
                      onSelect={() => status.mutate(archived ? "active" : "archived")}
                    >
                      <Icon name="archive" className="size-4" />
                      {archived ? "Restore" : "Archive"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : null}
          </div>
        }
      />

      <div className="grid items-start gap-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="space-y-3 lg:sticky lg:top-4">
          <div className="rounded-lg border border-border bg-surface-primary p-3">
            <p className="type-overline px-1">Sections</p>
            {sections.length === 0 ? (
              <p className="px-1 pt-2 text-body-sm text-text-subtle">None yet</p>
            ) : (
              <ul className="mt-1.5 space-y-0.5">
                {sections.map((section, index) => (
                  <li key={`${section.name}-${index}`}>
                    <button
                      type="button"
                      onClick={() =>
                        document
                          .getElementById(`section-${index}`)
                          ?.scrollIntoView({ behavior: "smooth", block: "start" })
                      }
                      className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-body-sm text-text-secondary transition-colors duration-80 ease-state hover:bg-surface-hover hover:text-text-primary"
                    >
                      <span className="min-w-0 flex-1 truncate">{section.name}</span>
                      <span className="tabular text-caption text-text-subtle">
                        {section.questions.length}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {editable ? (
              <div className="mt-3 grid gap-2 border-t border-border pt-3">
                <Button onClick={() => setEditing({ question: null, afterId: null })}>
                  <Icon name="plus" className="size-4" />
                  Add question
                </Button>
                <Button variant="secondary" onClick={() => setLibraryOpen(true)}>
                  <Icon name="book" className="size-4" />
                  From library
                </Button>
              </div>
            ) : null}
          </div>

          {tiering ? (
            <div className="rounded-lg border border-border bg-surface-primary p-3">
              <p className="type-overline px-1">Tier scale</p>
              <ThresholdRuler
                className="mt-1"
                score={null}
                thresholds={
                  Object.keys(questionnaire.tier_thresholds).length
                    ? questionnaire.tier_thresholds
                    : (facetsQuery.data?.tier_thresholds ?? { critical: 75, high: 50, medium: 25 })
                }
                effectiveTier={null}
              />
              <p className="mt-2 px-1 text-caption text-text-subtle">
                Answers add points. The total out of 100 sets the tier.
              </p>
            </div>
          ) : null}
        </aside>

        <main className="min-w-0 space-y-4">
          {questionnaire.questions.length === 0 ? (
            <EmptyState
              icon="checklist"
              title="No questions yet"
              description="Pick questions from the library or write your own."
              action={
                editable ? (
                  <div className="flex gap-2">
                    <Button onClick={() => setLibraryOpen(true)}>
                      <Icon name="book" className="size-4" />
                      From library
                    </Button>
                    <Button variant="secondary" onClick={() => setEditing({ question: null, afterId: null })}>
                      <Icon name="plus" className="size-4" />
                      Add question
                    </Button>
                  </div>
                ) : undefined
              }
            />
          ) : (
            sections.map((section, sectionIndex) => (
              <section
                key={`${section.name}-${sectionIndex}`}
                id={`section-${sectionIndex}`}
                className="scroll-mt-4 overflow-hidden rounded-lg border border-border bg-surface-primary"
              >
                <header className="flex items-center gap-2 border-b border-border bg-surface-sunken/60 px-4 py-2.5">
                  <h2 className="min-w-0 flex-1 truncate font-display text-title-sm text-text-primary">
                    {section.name}
                  </h2>
                  <span className="tabular text-caption text-text-subtle">
                    {section.questions.length}
                  </span>
                  {editable && sections.length > 1 ? (
                    <>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Move ${section.name} up`}
                        disabled={sectionIndex === 0 || reorder.isPending}
                        onClick={() => moveSection(sectionIndex, -1)}
                      >
                        <Icon name="arrowup" className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Move ${section.name} down`}
                        disabled={sectionIndex === sections.length - 1 || reorder.isPending}
                        onClick={() => moveSection(sectionIndex, 1)}
                      >
                        <Icon name="arrowdown" className="size-3.5" />
                      </Button>
                    </>
                  ) : null}
                </header>
                <ol className="divide-y divide-border">
                  {section.questions.map((question, index) => (
                    <QuestionRow
                      key={question.id}
                      question={question}
                      number={numberOf.get(question.id) ?? 0}
                      tiering={tiering}
                      parent={questionnaire.questions.find((q) => q.id === question.condition.question_id)}
                      parentNumber={numberOf.get(question.condition.question_id ?? "")}
                      editable={editable}
                      busy={reorder.isPending || remove.isPending}
                      canMoveUp={index > 0}
                      canMoveDown={index < section.questions.length - 1}
                      onEdit={() => setEditing({ question, afterId: null })}
                      onAddBelow={() => setEditing({ question: null, afterId: question.id })}
                      onMove={(delta) => move(question, delta)}
                      onDelete={() => setRemoving(question)}
                    />
                  ))}
                </ol>
              </section>
            ))
          )}
        </main>
      </div>

      {editable ? (
        <>
          <QuestionEditor
            open={editing !== null}
            onOpenChange={(open) => !open && setEditing(null)}
            questionnaire={questionnaire}
            question={editing?.question ?? null}
            afterId={editing?.afterId ?? null}
            riskDomains={facetsQuery.data?.risk_domains ?? []}
            onSaved={(next) => {
              apply(next);
              setEditing(null);
            }}
          />
          <ConfirmDialog
            open={removing !== null}
            onOpenChange={(open) => {
              if (!open) setRemoving(null);
            }}
            title="Remove this question?"
            consequence={
              <>
                <span className="font-semibold text-text-primary">{removing?.prompt}</span> leaves
                this questionnaire. Reviews already sent keep their own copy.
              </>
            }
            confirmLabel="Remove question"
            loading={remove.isPending}
            onConfirm={() => {
              if (removing) remove.mutate(removing.id);
            }}
          />
          <LibraryPickerDialog
            open={libraryOpen}
            onOpenChange={setLibraryOpen}
            questionnaire={questionnaire}
            onAdded={apply}
          />
        </>
      ) : null}
      {canManage ? (
        <QuestionnaireSettingsDialog
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          questionnaire={questionnaire}
          workspaceThresholds={facetsQuery.data?.tier_thresholds ?? { critical: 75, high: 50, medium: 25 }}
          onSaved={apply}
        />
      ) : null}
      <QuestionnairePreviewDialog
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        questionnaire={questionnaire}
        workspaceThresholds={facetsQuery.data?.tier_thresholds ?? { critical: 75, high: 50, medium: 25 }}
      />
    </div>
  );
}

function Chip({ icon, children, tone = "neutral" }: { icon?: Parameters<typeof Icon>[0]["name"]; children: React.ReactNode; tone?: "neutral" | "warn" | "danger" | "accent" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-xs px-1.5 py-0.5 text-caption font-medium",
        tone === "neutral" && "bg-surface-sunken text-text-secondary",
        tone === "warn" && "bg-status-warning-bg text-status-warning-text",
        tone === "danger" && "bg-status-danger-bg text-status-danger-text",
        tone === "accent" && "bg-action-accent-tint text-action-accent",
      )}
    >
      {icon ? <Icon name={icon} className="size-3" /> : null}
      {children}
    </span>
  );
}

function QuestionRow({
  question: q,
  number,
  tiering,
  parent,
  parentNumber,
  editable,
  busy,
  canMoveUp,
  canMoveDown,
  onEdit,
  onAddBelow,
  onMove,
  onDelete,
}: {
  question: BuilderQuestion;
  number: number;
  tiering: boolean;
  parent: BuilderQuestion | undefined;
  parentNumber: number | undefined;
  editable: boolean;
  busy: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onEdit: () => void;
  onAddBelow: () => void;
  onMove: (delta: -1 | 1) => void;
  onDelete: () => void;
}) {
  const type = TYPE_META[q.answer_type];
  const whenLabels = parent
    ? parent.options
        .filter((o) => (q.condition.option_keys ?? []).includes(o.key))
        .map((o) => o.label)
    : [];
  const floors = q.options.filter((o) => o.min_tier);
  const choice = isChoice(q.answer_type);

  return (
    <li className="group flex items-start gap-3 px-4 py-3 transition-colors duration-80 ease-state hover:bg-surface-hover/40">
      <span className="tabular mt-0.5 w-8 shrink-0 text-label-sm text-text-subtle">Q{number}</span>
      <button
        type="button"
        onClick={onEdit}
        disabled={!editable}
        className="min-w-0 flex-1 rounded-sm text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent disabled:cursor-default"
      >
        <p className="text-body-md text-text-primary">{q.prompt}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <Chip icon={type.icon}>{type.label}</Chip>
          {q.required ? null : <Chip>Optional</Chip>}
          {q.evidence !== "none" && !tiering ? (
            <Chip icon="paperclip" tone={q.evidence === "required" ? "accent" : "neutral"}>
              {EVIDENCE_LABEL[q.evidence]}
            </Chip>
          ) : null}
          {parent ? (
            <Chip icon="branch" tone="accent">
              If Q{parentNumber} is {whenLabels.join(" or ")}
            </Chip>
          ) : null}
          {q.critical ? <Chip tone="danger">Critical</Chip> : null}
          {q.blocking ? <Chip tone="warn">Blocks approval</Chip> : null}
          {q.weight !== 1 ? <Chip>Weight {q.weight}</Chip> : null}
          {floors.length ? (
            <Chip icon="gauge" tone="warn">
              Can set {TIER_META[floors[0].min_tier ?? ""]?.label ?? floors[0].min_tier}
            </Chip>
          ) : null}
        </div>
        {choice ? (
          <p className="mt-1.5 line-clamp-1 text-caption text-text-subtle">
            {q.options
              .map((o) => (tiering ? `${o.label} (${o.score})` : o.flag ? `${o.label} (gap)` : o.label))
              .join("   ·   ")}
          </p>
        ) : null}
      </button>
      {editable ? (
        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Move Q${number} up`}
            disabled={!canMoveUp || busy}
            onClick={() => onMove(-1)}
          >
            <Icon name="arrowup" className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Move Q${number} down`}
            disabled={!canMoveDown || busy}
            onClick={() => onMove(1)}
          >
            <Icon name="arrowdown" className="size-3.5" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label={`Actions for Q${number}`}>
                <Icon name="more" className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={onEdit}>
                <Icon name="edit" className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={onAddBelow}>
                <Icon name="plus" className="size-4" />
                Add question below
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={onDelete}>
                <Icon name="trash" className="size-4" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ) : null}
    </li>
  );
}
