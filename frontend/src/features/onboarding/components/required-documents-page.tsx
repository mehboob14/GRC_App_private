import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorState,
  PageHeader,
  SearchableSelect,
  Skeleton,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { apiFetch } from "@/lib/api/client";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { ImportDocumentsDialog } from "./import-documents-dialog";

/**
 * Required documents (guided onboarding RD-1 to RD-9): what the workspace's frameworks expect,
 * each with its state and the one next step that moves it on. Rows the profile makes unnecessary
 * are listed below the table with the answer behind them, so nothing disappears silently.
 */

type Row = {
  number: number;
  title: string;
  kind: "template" | "product" | "guidance" | "part_of";
  template: string | null;
  template_available: boolean;
  product: string | null;
  frameworks: string[];
  controls: string[];
  acknowledge: boolean;
  state: string;
  document_id: string | null;
};

type Required = {
  rows: Row[];
  hidden: { number: number; title: string; because: string }[];
  counted: number;
  approved: number;
  in_review: number;
};

const STATE: Record<string, { family: StatusFamily; label: string }> = {
  not_started: { family: "neutral", label: "Not started" },
  draft: { family: "progress", label: "Draft" },
  in_review: { family: "pending", label: "Waiting for approval" },
  approved: { family: "success", label: "Approved" },
  review_overdue: { family: "warning", label: "Review overdue" },
  in_product: { family: "neutral", label: "Kept in Verity" },
  guidance: { family: "neutral", label: "Guidance" },
  part_of: { family: "neutral", label: "Part of another" },
};

const FRAMEWORK: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

export function RequiredDocumentsPage() {
  const { principal } = useAuth();
  const canStart = hasPermission(principal, "documents:manage");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["required-documents", principal?.tenant_id],
    queryFn: () => apiFetch<Required>("/onboarding/required-documents"),
  });
  const start = useMutation({
    mutationFn: (template: string) =>
      apiFetch<{ id: string }>("/documents/from-template", {
        method: "POST",
        body: JSON.stringify({ template_key: template }),
      }),
    onSuccess: async (doc) => {
      await queryClient.invalidateQueries({ queryKey: ["required-documents"] });
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      navigate(`/documents/${doc.id}`);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  const canConfirm = hasPermission(principal, "documents:approve");
  const [importing, setImporting] = useState(
    () => new URLSearchParams(window.location.search).get("import") === "1",
  );
  const [having, setHaving] = useState<Row | null>(null);
  const [pick, setPick] = useState<string | null>(null);
  const [approvedOn, setApprovedOn] = useState("");
  const drafts = useQuery({
    queryKey: ["documents", principal?.tenant_id, "drafts-for-required"],
    queryFn: () => apiFetch<{ id: string; title: string; lifecycle: string; template_key: string | null }[]>("/documents"),
    enabled: having !== null,
  });
  const confirm = useMutation({
    mutationFn: () =>
      apiFetch<{ id: string }>(`/documents/${pick}/approved-elsewhere`, {
        method: "POST",
        body: JSON.stringify({ approved_on: approvedOn, template_key: having?.template ?? null }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["required-documents"] });
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      setHaving(null);
      toast({ title: "Counted as approved outside Verity", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  if (query.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (query.isError || !query.data) {
    const failure = describeError(query.error, "required documents");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  const data = query.data;

  const action = (row: Row) => {
    if (row.kind === "product" && row.product) {
      return (
        <Button asChild variant="secondary" size="sm">
          <Link to={row.product}>Open</Link>
        </Button>
      );
    }
    if (row.kind === "guidance") {
      return <span className="text-body-sm text-text-subtle">Your audit firm supplies the format</span>;
    }
    if (row.kind === "part_of") {
      return <span className="text-body-sm text-text-subtle">Inside the access control policy</span>;
    }
    if (row.document_id) {
      const ack = row.state === "approved" && row.acknowledge;
      return (
        <Button asChild variant="secondary" size="sm">
          <Link to={`/documents/${row.document_id}${ack ? "?campaign=new" : ""}`}>
            {ack ? "Send to all staff for acknowledgement" : "Open"}
          </Link>
        </Button>
      );
    }
    if (!canStart) return null;
    if (row.template && row.template_available) {
      return (
        <Button
          size="sm"
          variant="secondary"
          loading={start.isPending && start.variables === row.template}
          onClick={() => row.template && start.mutate(row.template)}
        >
          Start from template
        </Button>
      );
    }
    return (
      <Button asChild variant="ghost" size="sm">
        <Link to="/documents">Upload your own</Link>
      </Button>
    );
  };
  const already = (row: Row) =>
    canConfirm && row.kind === "template" && !row.document_id ? (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          setPick(null);
          setApprovedOn("");
          setHaving(row);
        }}
      >
        We already have this
      </Button>
    ) : null;

  return (
    <div className="mx-auto w-full max-w-[1040px]">
      <PageHeader
        title="Required documents"
        actions={
          canStart ? (
            <Button variant="secondary" onClick={() => setImporting(true)}>
              Import documents
            </Button>
          ) : undefined
        }
      />
      <ImportDocumentsDialog open={importing} onOpenChange={setImporting} rows={data.rows} />
      <p className="mt-2 text-body-sm text-text-secondary">
        {data.counted} needed, {data.approved} approved, {data.in_review} waiting for approval.
      </p>
      <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-surface-primary">
        <table className="w-full min-w-[720px] text-left text-body-sm">
          <thead className="border-b border-border text-caption text-text-subtle">
            <tr>
              <th className="px-4 py-2.5 font-normal">Document</th>
              <th className="px-4 py-2.5 font-normal">Needed for</th>
              <th className="px-4 py-2.5 font-normal">State</th>
              <th className="px-4 py-2.5 font-normal">Supports</th>
              <th className="px-4 py-2.5 font-normal">
                <span className="sr-only">Next step</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => {
              const state = STATE[row.state] ?? { family: "neutral" as StatusFamily, label: row.state };
              return (
                <tr key={row.number} className="border-b border-border last:border-b-0">
                  <td className="px-4 py-3 font-semibold text-text-primary">{row.title}</td>
                  <td className="px-4 py-3">
                    <span className="flex flex-wrap gap-1">
                      {row.frameworks.map((f) => (
                        <span key={f} className="rounded-sm bg-surface-sunken px-1.5 py-px text-caption text-text-secondary">
                          {FRAMEWORK[f] ?? f}
                        </span>
                      ))}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={state.family} label={state.label} />
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    {row.controls.slice(0, 2).join(", ")}
                    {row.controls.length > 2 ? ` +${row.controls.length - 2}` : ""}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex flex-wrap justify-end gap-1">
                      {action(row)}
                      {already(row)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Dialog open={having !== null} onOpenChange={(v) => (v ? null : setHaving(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>{having?.title}</DialogTitle>
            <DialogDescription>
              Pick the document you uploaded and the date it was approved. It counts as approved
              outside Verity, confirmed by you.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <SearchableSelect
              aria-label="Document"
              value={pick}
              onChange={setPick}
              placeholder="Choose an uploaded draft"
              options={(drafts.data ?? [])
                .filter((d) => d.lifecycle === "draft" && !d.template_key)
                .map((d) => ({ value: d.id, label: d.title }))}
            />
            <TextField label="Approved on" type="date" value={approvedOn} onChange={(e) => setApprovedOn(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setHaving(null)}>
              Cancel
            </Button>
            <Button disabled={!pick || !approvedOn} loading={confirm.isPending} onClick={() => confirm.mutate()}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {data.hidden.length ? (
        <details className="mt-3 text-body-sm text-text-secondary">
          <summary className="cursor-pointer">
            {data.hidden.length} documents are hidden because of your profile
          </summary>
          <ul className="mt-2 space-y-1">
            {data.hidden.map((h) => (
              <li key={h.number}>
                <span className="font-semibold text-text-primary">{h.title}.</span> {h.because}{" "}
                <Link to="/settings/organization/profile" className="text-text-link">
                  Change your answer
                </Link>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
