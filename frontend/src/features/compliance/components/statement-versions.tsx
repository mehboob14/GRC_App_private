import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  TextArea,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import { errorToast } from "@/lib/api/describe-error";

/**
 * Approved versions of the Statement of Applicability (guided onboarding SC-6, EN-11). Approving
 * freezes the statement as it stands under the next number; each version downloads as it was.
 */

type Version = {
  id: string;
  number: number;
  framework_version: string;
  note: string | null;
  created_at: string;
};

async function download(frameworkId: string, number: number): Promise<void> {
  const response = await fetch(
    `/api/v1/frameworks/${frameworkId}/applicability/versions/${number}.xlsx`,
    { headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` } },
  );
  if (!response.ok) throw new Error("download failed");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `statement-of-applicability-v${number}.xlsx`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function StatementVersions({ frameworkId, canApprove }: { frameworkId: string; canApprove: boolean }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [approving, setApproving] = useState(false);
  const [listing, setListing] = useState(false);
  const [note, setNote] = useState("");
  const path = `/frameworks/${frameworkId}/applicability/versions`;
  const versions = useQuery({
    queryKey: ["statement-versions", frameworkId],
    queryFn: () => apiFetch<Version[]>(path),
  });
  const approve = useMutation({
    mutationFn: () => apiFetch<Version>(path, { method: "POST", body: JSON.stringify({ note: note || null }) }),
    onSuccess: async (v) => {
      await queryClient.invalidateQueries({ queryKey: ["statement-versions", frameworkId] });
      setApproving(false);
      setNote("");
      toast({ title: `Version ${v.number} approved`, tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "statement"), tone: "danger" }),
  });
  const held = versions.data ?? [];

  return (
    <>
      {held.length ? (
        <Button variant="ghost" size="sm" onClick={() => setListing(true)}>
          Version {held[0].number}
        </Button>
      ) : null}
      {canApprove ? (
        <Button variant="secondary" size="sm" onClick={() => setApproving(true)}>
          Approve version
        </Button>
      ) : null}

      <Dialog open={approving} onOpenChange={setApproving}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Approve version {(held[0]?.number ?? 0) + 1}</DialogTitle>
            <DialogDescription>
              The statement is frozen as it stands. Later changes need a new version.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <TextArea label="Note" optional rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setApproving(false)}>
              Cancel
            </Button>
            <Button loading={approve.isPending} onClick={() => approve.mutate()}>
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={listing} onOpenChange={setListing}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Approved versions</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <ul className="space-y-2">
              {held.map((v) => (
                <li key={v.id} className="flex items-center justify-between gap-3 text-body-sm">
                  <span className="text-text-primary">
                    Version {v.number}, {new Date(v.created_at).toLocaleDateString()}
                    {v.note ? <span className="block text-text-secondary">{v.note}</span> : null}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      void download(frameworkId, v.number).catch((error: unknown) =>
                        toast({ title: errorToast(error, "statement"), tone: "danger" }),
                      )
                    }
                  >
                    Download
                  </Button>
                </li>
              ))}
            </ul>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </>
  );
}
