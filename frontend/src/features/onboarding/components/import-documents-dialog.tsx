import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  SearchableSelect,
  useToast,
} from "@/components/ui";
import { uploadDocument } from "@/features/documents/api";
import { apiFetch } from "@/lib/api/client";
import { errorToast } from "@/lib/api/describe-error";

/**
 * Import existing documents (guided onboarding EX-3): drop files, each gets a suggested match to
 * a Required documents row by its name, the person confirms or changes every match, then the
 * files are uploaded as drafts and matched. Approval stays a separate, explicit step.
 */

type Row = { title: string; template: string | null; document_id: string | null };

const WORDS = /[a-z]{3,}/g;

function suggest(filename: string, rows: Row[]): string | null {
  const name = new Set(filename.toLowerCase().replace(/\.[a-z0-9]+$/, "").match(WORDS) ?? []);
  let best: { key: string; score: number } | null = null;
  for (const r of rows) {
    if (!r.template) continue;
    const words = r.title.toLowerCase().match(WORDS) ?? [];
    const score = words.filter((w) => name.has(w) && w !== "policy" && w !== "and").length;
    if (score > 0 && (!best || score > best.score)) best = { key: r.template, score };
  }
  return best?.key ?? null;
}

export function ImportDocumentsDialog({
  open,
  onOpenChange,
  rows,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  rows: Row[];
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [files, setFiles] = useState<{ file: File; template: string | null }[]>([]);
  const [busy, setBusy] = useState(false);
  const open_ = rows.filter((r) => r.template && !r.document_id);
  const options = open_.map((r) => ({ value: r.template as string, label: r.title }));

  const pick = (list: FileList | null) =>
    setFiles(Array.from(list ?? []).map((file) => ({ file, template: suggest(file.name, open_) })));

  async function save() {
    setBusy(true);
    try {
      for (const f of files) {
        const doc = await uploadDocument(f.file, {
          title: f.file.name.replace(/\.[a-z0-9]+$/i, ""),
          doc_type: "policy",
          classification: "internal",
        });
        if (f.template) {
          await apiFetch(`/documents/${doc.id}/match-template`, {
            method: "POST",
            body: JSON.stringify({ template_key: f.template }),
          });
        }
      }
      await queryClient.invalidateQueries({ queryKey: ["required-documents"] });
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      toast({ title: `${files.length} documents imported as drafts`, tone: "success" });
      setFiles([]);
      onOpenChange(false);
    } catch (error: unknown) {
      toast({ title: errorToast(error, "document"), tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Import your documents</DialogTitle>
          <DialogDescription>
            Each file is matched by its name. Check every match, then import. They arrive as drafts.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-3">
          <input
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.md,.txt,.html"
            aria-label="Files to import"
            onChange={(e) => pick(e.target.files)}
            className="text-body-sm"
          />
          {files.map((f, i) => (
            <div key={f.file.name + i} className="grid gap-2 sm:grid-cols-[1fr_260px] sm:items-center">
              <span className="truncate text-body-sm text-text-primary">{f.file.name}</span>
              <SearchableSelect
                aria-label={`Match for ${f.file.name}`}
                value={f.template}
                onChange={(v) => setFiles(files.map((x, j) => (j === i ? { ...x, template: v } : x)))}
                placeholder="No match, keep as a draft"
                clearLabel="No match"
                options={options}
              />
            </div>
          ))}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!files.length} loading={busy} onClick={() => void save()}>
            Import {files.length || ""}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
