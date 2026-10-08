import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { commitImport, downloadTemplate, previewImport } from "../api";
import type { ImportPreview, Register } from "../types";
import { scoreOf } from "../scoring";
import { STATUS_META } from "../tokens";

/**
 * Spreadsheet import in two steps. The preview validates every row on the
 * server and writes nothing; the import sends back only the rows that passed.
 */
export function ImportRisksDialog({
  open,
  onOpenChange,
  register,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  register: Register;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [dragging, setDragging] = useState(false);
  const [showIssuesOnly, setShowIssuesOnly] = useState(false);

  useEffect(() => {
    if (open) {
      setFile(null);
      setPreview(null);
      setShowIssuesOnly(false);
    }
  }, [open]);

  const check = useMutation({
    mutationFn: (f: File) => previewImport(register.id, f),
    onSuccess: setPreview,
    onError: (e: unknown) => toast({ title: errorToast(e, "file"), tone: "danger" }),
  });
  const commit = useMutation({
    mutationFn: () => commitImport(register.id, preview!.rows.filter((r) => r.errors.length === 0)),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["risks"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-registers"] });
      toast({
        title: `${result.created} ${result.created === 1 ? "risk" : "risks"} imported${
          result.failed.length ? `, ${result.failed.length} skipped` : ""
        }`,
        tone: "success",
      });
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "import"), tone: "danger" }),
  });

  const pick = (f: File | undefined) => {
    if (!f) return;
    setFile(f);
    setPreview(null);
    check.mutate(f);
  };

  const rows = preview ? preview.rows.filter((r) => !showIssuesOnly || r.errors.length || r.warnings.length) : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[90vh] w-[min(960px,calc(100vw-2rem))]">
        <DialogHeader>
          <DialogTitle>Import risks</DialogTitle>
          <DialogDescription>Into {register.name}. Nothing is saved until you import.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_16rem]">
          <button
            type="button"
            onClick={() => input.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              pick(e.dataTransfer.files[0]);
            }}
            className={cn(
              "flex items-center gap-3 rounded-lg border-2 px-4 py-4 text-left transition-colors",
              dragging ? "border-action-accent bg-action-accent-tint" : "border-border bg-surface-sunken hover:bg-surface-hover",
            )}
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-surface-primary text-action-accent">
              <Icon name={check.isPending ? "spinner" : "upload"} className={cn("size-5", check.isPending && "animate-spin")} />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-body-md font-semibold text-text-primary">
                {file ? file.name : "Drop the filled template here, or choose a file"}
              </span>
              <span className="block text-caption text-text-subtle">Excel or CSV, up to 2000 risks</span>
            </span>
          </button>
          <input
            ref={input}
            type="file"
            accept=".xlsx,.csv"
            className="hidden"
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <div className="flex flex-col justify-center gap-1.5 rounded-lg border border-border p-3">
            <p className="text-label-sm text-text-primary">Excel template</p>
            <p className="text-caption text-text-subtle">Dropdowns for this register, subcategories follow the category.</p>
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                downloadTemplate(register.id).catch(() => toast({ title: "The template could not be downloaded.", tone: "danger" }))
              }
            >
              <Icon name="download" className="size-4" />
              Download template
            </Button>
          </div>
        </div>

        {preview ? (
          <>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-status-success-bg px-2.5 py-1 text-label-sm text-status-success-text">
                <Icon name="check" className="size-3.5" />
                {preview.valid} ready
              </span>
              {preview.invalid ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-status-danger-bg px-2.5 py-1 text-label-sm text-status-danger-text">
                  <Icon name="alert" className="size-3.5" />
                  {preview.invalid} with errors, skipped
                </span>
              ) : null}
              <label className="ml-auto flex items-center gap-2 text-caption text-text-subtle">
                <input type="checkbox" checked={showIssuesOnly} onChange={(e) => setShowIssuesOnly(e.target.checked)} />
                Only rows with issues
              </label>
            </div>
            <DialogBody className="mt-2">
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-body-sm">
                  <thead className="bg-surface-sunken text-caption text-text-subtle">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Row</th>
                      <th className="px-3 py-2 font-semibold">Title</th>
                      <th className="px-3 py-2 font-semibold">Category</th>
                      <th className="px-3 py-2 font-semibold">Status</th>
                      <th className="px-3 py-2 font-semibold">Owner</th>
                      <th className="px-3 py-2 font-semibold">Score</th>
                      <th className="px-3 py-2 font-semibold">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rows.map((r) => (
                      <tr key={r.row_number} className={cn(r.errors.length && "bg-status-danger-bg/40")}>
                        <td className="tabular px-3 py-2 text-text-subtle">{r.row_number}</td>
                        <td className="max-w-[16rem] truncate px-3 py-2 text-text-primary">{r.title || "Untitled"}</td>
                        <td className="px-3 py-2 text-text-secondary">
                          {[r.category_name, r.sub_category_name].filter(Boolean).join(" · ") || "None"}
                        </td>
                        <td className="px-3 py-2 text-text-secondary">{STATUS_META[r.status]?.label ?? r.status}</td>
                        <td className="px-3 py-2 text-text-secondary">{r.owner_name ?? "None"}</td>
                        <td className="tabular px-3 py-2 text-text-secondary">
                          {r.inherent_likelihood && r.inherent_impact ? scoreOf(register.scoring_formula, r.inherent_likelihood, r.inherent_impact) : "None"}
                        </td>
                        <td className="px-3 py-2">
                          {r.errors.length ? (
                            <span className="text-caption font-semibold text-status-danger-text">{r.errors.join(". ")}</span>
                          ) : r.warnings.length ? (
                            <span className="text-caption text-status-warning-text">{r.warnings.join(". ")}</span>
                          ) : (
                            <Icon name="check" className="size-4 text-status-success-base" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DialogBody>
          </>
        ) : null}

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!preview || preview.valid === 0} loading={commit.isPending} onClick={() => commit.mutate()}>
            Import {preview?.valid ?? 0} {preview?.valid === 1 ? "risk" : "risks"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
