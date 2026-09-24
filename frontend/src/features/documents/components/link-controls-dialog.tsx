import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { complianceApi, controlsApi } from "@/lib/api/endpoints";
import { mergeIntoDocumentDetail, updateDocument } from "../api";
import type { DocumentDetail } from "../types";
import { MultiSelect, type Option } from "./document-form-dialog";

/**
 * Mappings only: which frameworks this document belongs to, and which controls
 * it evidences.
 *
 * The Mappings tab used to open the whole edit form, which put the title, type,
 * classification and owner in front of somebody who came to tick two controls.
 * Everything else about the document is edited from the header's Edit button,
 * where it belongs.
 */
export function LinkControlsDialog({
  document: doc,
  open,
  onOpenChange,
}: {
  document: DocumentDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [frameworkIds, setFrameworkIds] = useState<string[]>([]);
  const [controlIds, setControlIds] = useState<string[]>([]);

  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
    enabled: open,
  });
  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
    enabled: open,
  });

  const frameworkOptions: Option[] = useMemo(
    () => (frameworksQuery.data ?? []).map((f) => ({ value: f.id, label: f.name })),
    [frameworksQuery.data],
  );
  const controlOptions: Option[] = useMemo(
    () =>
      (controlsQuery.data ?? [])
        .filter((c) => !c.disabled_at)
        .map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` })),
    [controlsQuery.data],
  );

  // The document carries framework names and control codes, so map them back to
  // ids once both lists have arrived.
  useEffect(() => {
    if (!open) return;
    const fwByName = new Map((frameworksQuery.data ?? []).map((f) => [f.name, f.id]));
    const ctByCode = new Map((controlsQuery.data ?? []).map((c) => [c.code, c.id]));
    setFrameworkIds(doc.frameworks.map((n) => fwByName.get(n)).filter(Boolean) as string[]);
    setControlIds(doc.controls.map((c) => ctByCode.get(c)).filter(Boolean) as string[]);
  }, [open, doc, frameworksQuery.data, controlsQuery.data]);

  const save = useMutation({
    mutationFn: () =>
      updateDocument(doc.id, { framework_ids: frameworkIds, control_ids: controlIds }),
    onSuccess: (next) => {
      mergeIntoDocumentDetail(queryClient, doc.id, next);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({ title: "Mappings saved", tone: "success" });
      onOpenChange(false);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "mappings"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="xl" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Link controls</DialogTitle>
          <p className="text-body-md text-text-secondary">
            What this document covers. A linked control counts this document toward its evidence.
          </p>
        </DialogHeader>
        <DialogBody className="space-y-5 py-1">
          <MultiSelect
            label="Frameworks"
            placeholder="Link frameworks…"
            options={frameworkOptions}
            selected={frameworkIds}
            onChange={setFrameworkIds}
            loading={frameworksQuery.isLoading}
            error={
              frameworksQuery.isError
                ? describeError(frameworksQuery.error, "framework list").message
                : undefined
            }
          />
          <MultiSelect
            label="Controls"
            placeholder="Link controls…"
            options={controlOptions}
            selected={controlIds}
            onChange={setControlIds}
            loading={controlsQuery.isLoading}
            error={
              controlsQuery.isError
                ? describeError(controlsQuery.error, "control list").message
                : undefined
            }
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            Save mappings
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
