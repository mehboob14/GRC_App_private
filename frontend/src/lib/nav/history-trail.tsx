import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { recordEntry } from "@/lib/nav/history-log";

/** Mount once inside the router: it notes each page the tab shows, for the back links. Renders nothing. */
export function HistoryTrail() {
  const location = useLocation();
  useEffect(() => {
    recordEntry(location.pathname + location.search);
  }, [location]);
  return null;
}
