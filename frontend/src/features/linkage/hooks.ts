import { useQuery, type QueryClient } from "@tanstack/react-query";
import {
  getLinks,
  getTrace,
  linksKey,
  traceKey,
  type AnchorType,
  type LinkType,
} from "./api";

export function useLinkedRecords(anchorType: AnchorType, anchorId: string) {
  return useQuery({
    queryKey: linksKey(anchorType, anchorId),
    queryFn: () => getLinks(anchorType, anchorId),
    enabled: Boolean(anchorId),
  });
}

export function useTrace(type: LinkType, id: string, depth: number) {
  return useQuery({
    queryKey: traceKey(type, id, depth),
    queryFn: () => getTrace(type, id, depth),
    enabled: Boolean(id),
    // Changing the depth keeps the tree on screen until the new one arrives; a
    // different record does not borrow the last one's.
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === type && previousQuery.queryKey[2] === id
        ? previous
        : undefined,
  });
}

/** A link has two ends: every page that shows the other end reads it afresh. */
export function invalidateOtherEnds(queryClient: QueryClient) {
  for (const queryKey of [
    ["linked-records"],
    ["trace"],
    ["risk"],
    ["risks"],
    ["evidence-links"],
  ]) {
    void queryClient.invalidateQueries({ queryKey });
  }
}
