import { Link } from "react-router-dom";
import { Button, Icon } from "@/components/ui";
import type { LinkType } from "../api";

/** The way into a record's trace: its Linked records header and the risk page carry it. */
export function TraceButton({ type, id }: { type: LinkType; id: string }) {
  return (
    <Button asChild variant="secondary">
      <Link to={`/trace/${type}/${id}`}>
        <Icon name="workflow" className="size-4" />
        Trace
      </Link>
    </Button>
  );
}
