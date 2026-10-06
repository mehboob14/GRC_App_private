import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  RadioGroup,
  RadioGroupItem,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { downloadAuditExport } from "../api";
import type { AuditExportFormat } from "../types";

/**
 * Download the trail as Excel or CSV, oldest events first. The dates are the only way
 * to narrow the file: the facets on the page filter the events already loaded, not
 * the trail, so they do not carry over. The system activity box starts from the
 * page's own setting.
 */
export function AuditExportDialog({
  includeSystem: pageIncludesSystem,
  onOpenChange,
}: {
  includeSystem: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const [format, setFormat] = useState<AuditExportFormat>("xlsx");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [includeSystem, setIncludeSystem] = useState(pageIncludesSystem);

  // ISO dates compare correctly as strings.
  const backwards = from !== "" && to !== "" && to < from;

  const download = useMutation({
    mutationFn: () => downloadAuditExport({ format, from, to, includeSystem }),
    onSuccess: () => {
      toast({ title: "Audit log exported", tone: "success" });
      onOpenChange(false);
    },
    // The dialog stays open on a refusal: a range too long for Excel is fixed by
    // changing the dates, and the reader should not have to start again.
    onError: (error: unknown) => toast({ title: errorToast(error, "audit log"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Export audit log</DialogTitle>
          <DialogDescription>Download the trail with the oldest events first.</DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          <fieldset>
            <legend className="mb-2 font-sans text-label-sm text-text-secondary">Format</legend>
            <RadioGroup
              aria-label="Format"
              value={format}
              onValueChange={(value) => setFormat(value as AuditExportFormat)}
            >
              <RadioGroupItem value="xlsx" label="Excel" description="Up to 50,000 events" />
              <RadioGroupItem value="csv" label="CSV" description="No limit on events" />
            </RadioGroup>
          </fieldset>
          <div>
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="From"
                optional
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => setFrom(e.target.value)}
              />
              <TextField
                label="To"
                optional
                type="date"
                value={to}
                min={from || undefined}
                error={backwards ? "To can't be before From." : undefined}
                onChange={(e) => setTo(e.target.value)}
              />
            </div>
            <p className="mt-1.5 text-caption text-text-subtle">
              Dates are UTC days and both are included.
            </p>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-body-sm text-text-secondary">
            <Checkbox checked={includeSystem} onCheckedChange={setIncludeSystem} />
            Include system activity
          </label>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={download.isPending} disabled={backwards} onClick={() => download.mutate()}>
            <Icon name="download" className="size-4" />
            Download
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
