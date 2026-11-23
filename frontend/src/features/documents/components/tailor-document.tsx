import { useState } from "react";
import DOMPurify from "dompurify";
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
  useToast,
} from "@/components/ui";
import { onboardingApi } from "@/features/onboarding/api";
import { errorToast } from "@/lib/api/describe-error";
import { saveDocumentContent } from "../api";

/**
 * Tailor a draft to the company with AI (guided onboarding AI-1). The model's version is shown
 * for a person to read; only "Use this version" saves it, as a normal new version of the draft.
 */
export function TailorDocument({ documentId }: { documentId: string }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [draft, setDraft] = useState<{ html: string; notice: string | null } | null>(null);
  const tailor = useMutation({
    mutationFn: () => onboardingApi.assist("document_tailoring", documentId),
    onSuccess: (d) => setDraft({ html: d.text, notice: d.notice }),
    onError: (e: unknown) => toast({ title: errorToast(e, "document"), tone: "danger" }),
  });
  const use = useMutation({
    mutationFn: () =>
      saveDocumentContent(documentId, draft?.html ?? "", "minor", "Tailored with AI, read by a person"),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      setDraft(null);
      toast({ title: "Saved as a new draft version", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "document"), tone: "danger" }),
  });
  return (
    <>
      <Button variant="ghost" size="sm" loading={tailor.isPending} onClick={() => tailor.mutate()}>
        Tailor with AI
      </Button>
      <Dialog open={draft !== null} onOpenChange={(v) => (v ? null : setDraft(null))}>
        <DialogContent size="lg">
          <DialogHeader>
            <DialogTitle>Tailored draft</DialogTitle>
            <DialogDescription>
              {draft?.notice ?? "Written with AI. Read it before you use it; nothing is saved yet."}
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div
              className="prose max-h-[60vh] max-w-none overflow-y-auto text-body-sm"
              // Model output is untrusted: sanitized before it is shown.
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(draft?.html ?? "") }}
            />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDraft(null)}>
              Discard
            </Button>
            <Button loading={use.isPending} onClick={() => use.mutate()}>
              Use this version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
