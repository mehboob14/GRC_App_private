import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  Icon,
  SegmentedControl,
  Skeleton,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import {
  createQuestionnaire,
  duplicateQuestionnaire,
  getQuestionnaireLibrary,
  listQuestionnaires,
  setQuestionnaireStatus,
  updateQuestionnaire,
} from "../api";
import type { QuestionnairePurpose, QuestionnaireSummary } from "../types";
import { fmtDate, TIER_META } from "../tokens";
import { TierBadge } from "./tier-badge";

const PURPOSES = [
  { id: "tiering", label: "Tiering" },
  { id: "due_diligence", label: "Due diligence" },
] as const;

const EXPLAINER: Record<QuestionnairePurpose, { icon: "gauge" | "vendor"; text: string }> = {
  tiering: { icon: "gauge", text: "Your team answers these about a vendor. The answers set its tier." },
  due_diligence: {
    icon: "vendor",
    text: "Vendors answer these in the portal. The answers set the residual score and raise findings.",
  },
};

/**
 * The tenant's questionnaires, one tab per purpose.
 *
 * Tiering and due diligence sit side by side because people mix them up: the
 * explainer line under the switch says who answers each one and what it sets.
 */
export function VendorQuestionnairesPage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const [params, setParams] = useSearchParams();
  const purpose: QuestionnairePurpose =
    params.get("purpose") === "due_diligence" ? "due_diligence" : "tiering";
  const [showArchived, setShowArchived] = useState(false);
  const [creating, setCreating] = useState(false);

  const query = useQuery({
    queryKey: ["vendor-questionnaires", { archived: showArchived }],
    queryFn: () => listQuestionnaires(undefined, showArchived),
  });

  const rows = useMemo(
    () => (query.data ?? []).filter((q) => q.purpose === purpose),
    [query.data, purpose],
  );
  const counts = useMemo(() => {
    const active = (query.data ?? []).filter((q) => q.status === "active");
    return {
      tiering: active.filter((q) => q.purpose === "tiering").length,
      due_diligence: active.filter((q) => q.purpose === "due_diligence").length,
    };
  }, [query.data]);

  if (query.isError) {
    const error = describeError(query.error, "questionnaires");
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        referenceId={error.referenceId}
        onRetry={error.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const explainer = EXPLAINER[purpose];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <SegmentedControl
          label="Questionnaire type"
          items={PURPOSES.map((p) => ({
            id: p.id,
            label: query.data ? `${p.label} ${counts[p.id]}` : p.label,
          }))}
          value={purpose}
          onChange={(id) => setParams(id === "tiering" ? {} : { purpose: id }, { replace: true })}
        />
        <p className="flex min-w-0 flex-1 items-center gap-2 text-body-sm text-text-secondary">
          <Icon name={explainer.icon} className="size-4 shrink-0 text-text-subtle" />
          <span className="truncate">{explainer.text}</span>
        </p>
        <label className="flex items-center gap-2 text-label-sm text-text-secondary">
          <Checkbox
            checked={showArchived}
            onCheckedChange={setShowArchived}
            aria-label="Show archived"
          />
          Show archived
        </label>
        {canManage ? (
          <Button onClick={() => setCreating(true)}>
            <Icon name="plus" className="size-4" />
            New questionnaire
          </Button>
        ) : null}
      </div>

      {query.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="checklist"
          title="No questionnaires here yet"
          description="Start one from the library or build it question by question."
          action={
            canManage ? (
              <Button onClick={() => setCreating(true)}>
                <Icon name="plus" className="size-4" />
                New questionnaire
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <QuestionnaireCard key={row.id} row={row} canManage={canManage} />
          ))}
        </div>
      )}

      <NewQuestionnaireDialog open={creating} onOpenChange={setCreating} purpose={purpose} />
    </div>
  );
}

function QuestionnaireCard({ row, canManage }: { row: QuestionnaireSummary; canManage: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const archived = row.status === "archived";
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["vendor-questionnaires"] });

  const duplicate = useMutation({
    mutationFn: () => duplicateQuestionnaire(row.id),
    onSuccess: (copy) => {
      refresh();
      toast({ title: "Questionnaire copied", tone: "success" });
      navigate(`/vendors/questionnaires/${copy.id}`);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });
  const status = useMutation({
    mutationFn: () => setQuestionnaireStatus(row.id, archived ? "active" : "archived"),
    onSuccess: () => {
      refresh();
      toast({ title: archived ? "Questionnaire restored" : "Questionnaire archived", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });
  const makeDefault = useMutation({
    mutationFn: () =>
      updateQuestionnaire(row.id, {
        name: row.name,
        description: row.description,
        default_tiers: row.default_tiers,
        tier_thresholds: {},
        is_default: true,
      }),
    onSuccess: () => {
      refresh();
      toast({ title: `${row.name} is now the default`, tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });

  return (
    <article
      className={cn(
        "group flex flex-col rounded-lg border border-border bg-surface-primary p-4 transition-shadow duration-150 ease-state hover:shadow-2",
        archived && "opacity-70",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
          <Icon name="checklist" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <Link
            to={`/vendors/questionnaires/${row.id}`}
            className="line-clamp-2 font-display text-title-md text-text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
          >
            {row.name}
          </Link>
          <p className="mt-0.5 text-caption text-text-subtle">
            {row.question_count} {row.question_count === 1 ? "question" : "questions"} ·{" "}
            {row.section_count} {row.section_count === 1 ? "section" : "sections"}
          </p>
        </div>
        {canManage ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${row.name}`}>
                <Icon name="more" className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => navigate(`/vendors/questionnaires/${row.id}`)}>
                <Icon name="edit" className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => duplicate.mutate()}>
                <Icon name="copy" className="size-4" />
                Duplicate
              </DropdownMenuItem>
              {row.purpose === "tiering" && !row.is_default && !archived ? (
                <DropdownMenuItem onSelect={() => makeDefault.mutate()}>
                  <Icon name="star" className="size-4" />
                  Make default
                </DropdownMenuItem>
              ) : null}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => status.mutate()}
                disabled={row.is_default && !archived}
              >
                <Icon name="archive" className="size-4" />
                {archived ? "Restore" : "Archive"}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>

      {row.description ? (
        <p className="mt-3 line-clamp-2 text-body-sm text-text-secondary">{row.description}</p>
      ) : null}

      <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-4">
        {row.is_default ? (
          <Badge variant="role">
            <Icon name="star" className="size-3" />
            Default
          </Badge>
        ) : null}
        {row.default_tiers.map((tier) => (
          <TierBadge key={tier} tier={tier} label={`${TIER_META[tier]?.label ?? tier} tier`} />
        ))}
        {archived ? <Badge variant="neutral">Archived</Badge> : null}
        <span className="ml-auto text-caption text-text-subtle">
          {[fmtDate(row.updated_at), row.updated_by_name].filter(Boolean).join(" · ")}
        </span>
      </div>
    </article>
  );
}

/**
 * Start from the library or from nothing. One screen: pick a starting point,
 * name it, create. The library's presets say how many questions each brings.
 */
function NewQuestionnaireDialog({
  open,
  onOpenChange,
  purpose,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  purpose: QuestionnairePurpose;
}) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<QuestionnairePurpose>(purpose);
  const [start, setStart] = useState<string>("blank");
  const [name, setName] = useState("");

  const library = useQuery({
    queryKey: ["vendor-questionnaire-library", kind],
    queryFn: () => getQuestionnaireLibrary(kind),
    enabled: open,
  });

  const choices = useMemo(
    () =>
      (library.data ?? []).flatMap((template) =>
        template.presets.map((preset) => ({
          id: `${template.code}:${preset.key}`,
          template,
          preset,
          title:
            template.presets.length > 1 ? `${template.name}, ${preset.label.toLowerCase()}` : template.name,
        })),
      ),
    [library.data],
  );
  const chosen = choices.find((c) => c.id === start) ?? null;

  const reset = (next: boolean) => {
    if (next) {
      setKind(purpose);
      setStart("blank");
      setName("");
    }
    onOpenChange(next);
  };

  const create = useMutation({
    mutationFn: () =>
      createQuestionnaire({
        purpose: kind,
        name: name.trim() || chosen?.title || "Untitled questionnaire",
        library_code: chosen?.template.code ?? null,
        preset: chosen?.preset.key ?? null,
      }),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["vendor-questionnaires"] });
      reset(false);
      navigate(`/vendors/questionnaires/${created.id}`);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "questionnaire"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogContent size="md" scrollBody className="max-h-[min(44rem,90vh)]">
        <DialogHeader>
          <DialogTitle>New questionnaire</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <SegmentedControl
            label="Questionnaire type"
            items={PURPOSES}
            value={kind}
            onChange={(id) => {
              setKind(id);
              setStart("blank");
            }}
          />

          <div role="radiogroup" aria-label="Start from" className="grid gap-2">
            {library.isLoading ? <Skeleton className="h-16" /> : null}
            {choices.map((choice) => (
              <StartOption
                key={choice.id}
                selected={start === choice.id}
                onSelect={() => setStart(choice.id)}
                icon="book"
                title={choice.title}
                detail={choice.template.description}
                meta={`${choice.preset.question_count} questions`}
              />
            ))}
            <StartOption
              selected={start === "blank"}
              onSelect={() => setStart("blank")}
              icon="plus"
              title="Blank"
              detail="Add your own questions, or pick some from the library later."
            />
          </div>

          <TextField
            label="Name"
            value={name}
            placeholder={chosen?.title ?? "Cloud providers"}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => reset(false)}>
            Cancel
          </Button>
          <Button loading={create.isPending} onClick={() => create.mutate()}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StartOption({
  selected,
  onSelect,
  icon,
  title,
  detail,
  meta,
}: {
  selected: boolean;
  onSelect: () => void;
  icon: "book" | "plus";
  title: string;
  detail: string | null;
  meta?: string;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "flex w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        selected
          ? "border-action-accent bg-action-accent-tint"
          : "border-border bg-surface-primary hover:bg-surface-hover",
      )}
    >
      <span
        className={cn(
          "mt-0.5 grid size-8 shrink-0 place-items-center rounded-sm",
          selected ? "bg-action-accent text-white" : "bg-surface-sunken text-text-subtle",
        )}
      >
        <Icon name={icon} className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-3">
          <span className="text-label-md text-text-primary">{title}</span>
          {meta ? <span className="tabular shrink-0 text-caption text-text-subtle">{meta}</span> : null}
        </span>
        {detail ? (
          <span className="mt-0.5 line-clamp-2 block text-caption text-text-subtle">{detail}</span>
        ) : null}
      </span>
    </button>
  );
}
