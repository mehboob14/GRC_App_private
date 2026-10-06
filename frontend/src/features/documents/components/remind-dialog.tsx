import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { remindCampaign } from "../api";
import type { Campaign } from "../types";

const people = (count: number) => `${count} ${count === 1 ? "person" : "people"}`;

/**
 * Chase the people who have not signed. A popup rather than a button that fires, so
 * the owner sees how many are about to hear from them before anyone does.
 */
export function RemindDialog({
  campaign,
  open,
  onOpenChange,
}: {
  campaign: Campaign;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const remind = useMutation({
    mutationFn: () => remindCampaign(campaign.id),
    onSuccess: ({ reminded, skipped }) => {
      toast(
        reminded === 0
          ? { title: "Everyone left was reminded in the last 24 hours", tone: "neutral" }
          : {
              title: `Reminded ${people(reminded)}${skipped > 0 ? `, ${skipped} skipped` : ""}`,
              tone: "success",
            },
      );
      void queryClient.invalidateQueries({ queryKey: ["campaign", campaign.id] });
      onOpenChange(false);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "campaign"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Remind {people(campaign.pending)}?</DialogTitle>
          <p className="text-body-md text-text-secondary">
            {campaign.pending === 1 ? "1 person has" : `${campaign.pending} people have`} not
            signed yet. Each gets a notification and an email. Anyone reminded in the last 24
            hours is skipped.
          </p>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={remind.isPending} onClick={() => remind.mutate()}>
            <Icon name="mail" className="size-4" />
            Send reminder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
