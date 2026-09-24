import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { raiseRiskFromFinding, type RaisedRisk } from "../api";
import { invalidateOtherEnds } from "../hooks";

/**
 * Turn a finding into a risk in the register. The server scores it from the
 * finding (severity for impact, exploitability for likelihood) and links it
 * back to the finding and its asset; the person only confirms the title.
 */
export function RaiseRiskDialog({
  open,
  onOpenChange,
  instanceId,
  defaultTitle,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instanceId: string;
  defaultTitle: string;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [title, setTitle] = useState(defaultTitle);
  const [raised, setRaised] = useState<RaisedRisk | null>(null);

  useEffect(() => {
    if (open) {
      setTitle(defaultTitle);
      setRaised(null);
    }
  }, [open, defaultTitle]);

  const raise = useMutation({
    mutationFn: () => raiseRiskFromFinding(instanceId, title),
    onSuccess: (risk) => {
      setRaised(risk);
      invalidateOtherEnds(queryClient);
      void queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "risk"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {raised ? (
          <>
            <div className="flex flex-col items-center gap-3 py-2 text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-status-success-base text-white">
                <Icon name="check" className="size-6" />
              </span>
              <DialogTitle>{raised.code} raised</DialogTitle>
              <DialogDescription>
                It is in the register, scored from this finding and linked to it
                and its asset.
              </DialogDescription>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => onOpenChange(false)}>
                Done
              </Button>
              <Button asChild>
                <Link to={`/risks/${raised.id}`}>
                  Open risk
                  <Icon name="arrowr" className="size-4" />
                </Link>
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              raise.mutate();
            }}
          >
            <DialogHeader>
              <DialogTitle>Raise a risk</DialogTitle>
              <DialogDescription>
                Scored from this finding&apos;s severity and exploitability, and
                linked back to it.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              <TextField
                label="Risk title"
                value={title}
                maxLength={300}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <DialogFooter className="mt-5">
              <Button
                variant="secondary"
                type="button"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                loading={raise.isPending}
                disabled={!title.trim()}
              >
                <Icon name="risk" className="size-4" />
                Raise risk
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
