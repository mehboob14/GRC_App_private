import { useQuery, type QueryClient } from "@tanstack/react-query";
import { getLinks, linksKey, type AnchorType } from "./api";

export function useLinkedRecords(anchorType: AnchorType, anchorId: string) {
  return useQuery({
    queryKey: linksKey(anchorType, anchorId),
    queryFn: () => getLinks(anchorType, anchorId),
    enabled: Boolean(anchorId),
  });
}

/** A link has two ends: every page that shows the other end reads it afresh. */
export function invalidateOtherEnds(queryClient: QueryClient) {
  for (const queryKey of [
    ["linked-records"],
    ["risk"],
    ["risks"],
    ["evidence-links"],
  ]) {
    void queryClient.invalidateQueries({ queryKey });
  }
}
