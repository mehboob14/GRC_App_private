import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, useToast } from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { onboardingApi, type AssistKind } from "../api";

/**
 * "Draft with AI" (guided onboarding AI-1, AI-2, AI-6). Fills an editable draft and says where it
 * came from. Nothing is saved here: the person edits, then saves or approves as usual.
 */
export function DraftButton({
  kind,
  subject,
  onDraft,
  label = "Draft with AI",
}: {
  kind: AssistKind;
  subject?: string;
  onDraft: (text: string) => void;
  label?: string;
}) {
  const { toast } = useToast();
  const [note, setNote] = useState<string | null>(null);
  const draft = useMutation({
    mutationFn: () => onboardingApi.assist(kind, subject),
    onSuccess: (d) => {
      onDraft(d.text);
      setNote(d.notice ?? "Draft, written with AI. Check it before you save.");
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "draft"), tone: "danger" }),
  });
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Button type="button" size="sm" variant="ghost" loading={draft.isPending} onClick={() => draft.mutate()}>
        {label}
      </Button>
      {note ? <span className="text-caption text-text-subtle">{note}</span> : null}
    </span>
  );
}
