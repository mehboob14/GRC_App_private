import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
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
  Skeleton,
  Toolbar,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { adoptTemplates, listLibrary } from "../api";
import type { LibraryTemplate } from "../types";
import { TREATMENT_META } from "../tokens";
import { useRisksOutlet } from "./risks-outlet";
import { ScoreChip } from "./score";

/**
 * The starter library as a catalogue: pick what applies, add it in one go.
 * Adopted risks copy the text and link the suggested controls the workspace
 * has, so a later library update never rewrites a reviewed risk.
 */
export function RiskLibraryPage() {
  const { register, canManage } = useRisksOutlet();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [frameworks, setFrameworks] = useState<string[]>([]);
  const [hideAdopted, setHideAdopted] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  const [preview, setPreview] = useState<LibraryTemplate | null>(null);

  const query = useQuery({ queryKey: ["risk-library", register.id], queryFn: () => listLibrary(register.id) });
  const templates = useMemo(() => query.data ?? [], [query.data]);

  const allCategories = [...new Set(templates.map((t) => t.category))];
  const allFrameworks = [...new Set(templates.flatMap((t) => t.frameworks))].sort();
  const rows = templates.filter((t) => {
    const q = search.trim().toLowerCase();
    if (q && !`${t.title} ${t.description} ${t.code}`.toLowerCase().includes(q)) return false;
    if (categories.length && !categories.includes(t.category)) return false;
    if (frameworks.length && !t.frameworks.some((f) => frameworks.includes(f))) return false;
    if (hideAdopted && t.adopted) return false;
    return true;
  });
  const grouped = allCategories
    .map((c) => ({ category: c, items: rows.filter((t) => t.category === c) }))
    .filter((g) => g.items.length);
  const adoptedCount = templates.filter((t) => t.adopted).length;

  const adopt = useMutation({
    mutationFn: (codes: string[]) => adoptTemplates(register.id, codes),
    onSuccess: (result) => {
      setPicked([]);
      setPreview(null);
      void queryClient.invalidateQueries({ queryKey: ["risk-library", register.id] });
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      toast({
        title: `${result.created} ${result.created === 1 ? "risk" : "risks"} added${
          result.controls_linked ? ` with ${result.controls_linked} controls linked` : ""
        }`,
        tone: "success",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "library"), tone: "danger" }),
  });

  const toggle = (code: string) =>
    setPicked((p) => (p.includes(code) ? p.filter((c) => c !== code) : [...p, code]));

  if (query.isError) {
    const error = describeError(query.error, "risk library");
    return <ErrorState title={error.title} description={error.message} onRetry={() => void query.refetch()} />;
  }

  return (
    <div className="pb-20">
      <Toolbar
        searchLabel="Filter the library"
        search={<SearchInput value={search} onChange={setSearch} placeholder="Search the library" aria-label="Search library" />}
      >
        <FilterFacet label="Category" options={allCategories.map((c) => ({ value: c, label: c }))} values={categories} onChange={setCategories} />
        <FilterFacet label="Framework" options={allFrameworks.map((f) => ({ value: f, label: f }))} values={frameworks} onChange={setFrameworks} />
        <FilterFacet
          label="Show"
          options={[{ value: "hide", label: "Hide added" }]}
          values={hideAdopted ? ["hide"] : []}
          onChange={(v) => setHideAdopted(v.includes("hide"))}
        />
        <span className="ml-auto text-caption text-text-subtle">
          {templates.length} risks · {adoptedCount} in {register.name}
        </span>
      </Toolbar>

      <div className="mt-4 space-y-5">
        {query.isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-36 w-full" />
            ))}
          </div>
        ) : grouped.length === 0 ? (
          <EmptyState
            icon="book"
            variant={templates.length ? "no-match" : "no-data"}
            title={templates.length ? "Nothing matches" : "The library is empty"}
            description={templates.length ? "Adjust the filters." : "Load the content packs to see the starter library."}
          />
        ) : (
          grouped.map((g) => (
            <section key={g.category}>
              <h2 className="mb-2 flex items-center gap-2 text-label-md text-text-secondary">
                {g.category}
                <span className="tabular text-caption text-text-subtle">{g.items.length}</span>
              </h2>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {g.items.map((t) => {
                  const on = picked.includes(t.code);
                  return (
                    <article
                      key={t.code}
                      className={cn(
                        "group flex flex-col rounded-lg border bg-surface-primary p-4 transition-colors",
                        on ? "border-action-accent ring-1 ring-action-accent" : "border-border hover:border-border-strong",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        {canManage && !t.adopted ? (
                          <Checkbox checked={on} onCheckedChange={() => toggle(t.code)} aria-label={`Select ${t.title}`} />
                        ) : null}
                        <button type="button" onClick={() => setPreview(t)} className="min-w-0 flex-1 text-left">
                          <p className="text-body-md font-semibold text-text-primary group-hover:underline">{t.title}</p>
                          <p className="mt-0.5 text-caption text-text-subtle">
                            {t.sub_category} · {t.code}
                          </p>
                        </button>
                        <ScoreChip score={t.default_likelihood * t.default_impact} bands={libraryBands} size="sm" />
                      </div>
                      <p className="mt-2 line-clamp-2 text-body-sm text-text-secondary">{t.description}</p>
                      <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-3">
                        {t.adopted ? (
                          <Badge variant="statusPass">
                            <Icon name="check" className="size-3" />
                            In register
                          </Badge>
                        ) : null}
                        {t.control_keys.length ? (
                          <Badge variant="neutral">
                            {t.control_keys.length} {t.control_keys.length === 1 ? "control" : "controls"}
                          </Badge>
                        ) : null}
                        {t.frameworks.slice(0, 3).map((f) => (
                          <Badge key={f} variant="neutral">
                            {f}
                          </Badge>
                        ))}
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          ))
        )}
      </div>

      {picked.length ? (
        <div className="fixed inset-x-0 bottom-5 z-40 flex justify-center px-4">
          <div className="flex items-center gap-4 rounded-xl border border-border bg-surface-primary px-4 py-2.5 shadow-4">
            <span className="text-body-sm font-semibold text-text-primary">{picked.length} selected</span>
            <Button variant="ghost" size="sm" onClick={() => setPicked([])}>
              Clear
            </Button>
            <Button size="sm" loading={adopt.isPending} onClick={() => adopt.mutate(picked)}>
              <Icon name="plus" className="size-4" />
              Add to {register.name}
            </Button>
          </div>
        </div>
      ) : null}

      <Drawer open={preview !== null} onOpenChange={(o) => !o && setPreview(null)}>
        <DrawerContent size="lg">
          {preview ? (
            <>
              <DrawerHeader>
                <DrawerTitle>{preview.title}</DrawerTitle>
                <DrawerDescription>
                  {preview.category} · {preview.sub_category} · {preview.code}
                </DrawerDescription>
              </DrawerHeader>
              <DrawerBody className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-surface-sunken p-3.5">
                  <ScoreChip score={preview.default_likelihood * preview.default_impact} bands={libraryBands} size="lg" />
                  <div className="text-body-sm text-text-secondary">
                    <p>
                      Likelihood {preview.default_likelihood} · Impact {preview.default_impact} on a 5 point scale
                    </p>
                    <p className="text-caption text-text-subtle">Rescaled to {register.name} when added</p>
                  </div>
                  {preview.treatment ? (
                    <Badge variant="neutral" className="ml-auto">
                      {TREATMENT_META[preview.treatment].label}
                    </Badge>
                  ) : null}
                </div>
                {[
                  ["Description", preview.description],
                  ["Root cause", preview.root_cause],
                  ["Consequences", preview.consequences],
                  ["Recommendations", preview.recommendations],
                ].map(([label, value]) =>
                  value ? (
                    <div key={label}>
                      <p className="text-label-sm text-text-secondary">{label}</p>
                      <p className="mt-1 text-body-sm text-text-primary">{value}</p>
                    </div>
                  ) : null,
                )}
                {preview.control_keys.length ? (
                  <div>
                    <p className="text-label-sm text-text-secondary">Suggested controls</p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {preview.control_keys.map((k) => (
                        <Badge key={k} variant="neutral">
                          {k.replace(/-/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </DrawerBody>
              <DrawerFooter>
                <Button variant="secondary" onClick={() => setPreview(null)}>
                  Close
                </Button>
                {canManage && !preview.adopted ? (
                  <Button loading={adopt.isPending} onClick={() => adopt.mutate([preview.code])}>
                    <Icon name="plus" className="size-4" />
                    Add to register
                  </Button>
                ) : null}
              </DrawerFooter>
            </>
          ) : null}
        </DrawerContent>
      </Drawer>
    </div>
  );
}

/** Library scores are written on a 5 by 5 scale, so they band on the default thresholds. */
const libraryBands = [
  { key: "low" as const, label: "Low", min_score: 1 },
  { key: "medium" as const, label: "Medium", min_score: 5 },
  { key: "high" as const, label: "High", min_score: 10 },
  { key: "critical" as const, label: "Critical", min_score: 15 },
];
