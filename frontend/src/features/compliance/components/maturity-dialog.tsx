import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
} from "@/components/ui";
import { evidenceApi } from "@/lib/api/endpoints";
import type { Evidence } from "@/lib/api/types";

const VERDICT: Record<string, string> = {
  proves: "Proves it",
  partly: "Partly proves it",
  does_not: "Does not prove it",
};

/**
 * How well a file just uploaded under a control proves that control and the SOC 2
 * requirements linked to it. A draft from the model: it changes nothing, and a person
 * decides what to do with the gaps (rule 11).
 */
export function MaturityDialog({
  item,
  controlId,
  onClose,
}: {
  item: Evidence | null;
  controlId: string;
  onClose: () => void;
}) {
  const query = useQuery({
    queryKey: ["evidence-maturity", item?.id, controlId],
    queryFn: () => evidenceApi.assessMaturity(item!.id, controlId),
    enabled: item !== null,
    staleTime: Infinity,
    retry: false,
  });
  const result = query.data;
  return (
    <Dialog open={item !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>How well does this prove the control?</DialogTitle>
          <DialogDescription>{item?.title}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 px-6 pb-2">
          {query.isLoading ? (
            <Skeleton className="h-32 w-full rounded-md" />
          ) : query.isError || !result?.available ? (
            <p className="text-body-sm text-text-secondary">
              The AI check is not available right now (no model key is set, or it could not decide).
              The evidence is saved and linked either way.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={(result.maturity ?? 0) >= 70 ? "count" : "countWarn"}>
                  Maturity {result.maturity}/100
                </Badge>
                <span className="text-body-md font-semibold text-text-primary">
                  {VERDICT[result.verdict ?? "partly"]}
                </span>
                <span className="text-caption text-text-subtle">
                  {result.code} {result.name}
                </span>
              </div>
              <p className="text-body-sm text-text-secondary">{result.summary}</p>
              {result.requirements.length > 0 ? (
                <div>
                  <p className="type-overline mb-1">Linked requirements</p>
                  <ul className="space-y-1">
                    {result.requirements.map((r) => (
                      <li key={r.code} className="text-body-sm text-text-secondary">
                        <span className="font-semibold text-text-primary">{r.code}</span>{" "}
                        <span className="text-text-subtle">({r.verdict.replace(/_/g, " ")})</span> {r.note}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {result.gaps.length > 0 ? (
                <div>
                  <p className="type-overline mb-1">How to close the gaps</p>
                  <ul className="list-disc space-y-0.5 pl-5 text-body-sm text-text-secondary">
                    {result.gaps.map((g) => (
                      <li key={g}>{g}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </div>
        <DialogFooter>
          <Button onClick={onClose}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
