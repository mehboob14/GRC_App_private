import type { MouseEvent } from "react";
import { Link } from "react-router-dom";
import { CodeChip, Icon, Tooltip } from "@/components/ui";
import type { Control, Evidence } from "@/lib/api/types";
import { automatedBy, typeIcon, typeLabel } from "../tokens";

/** The kind of artefact and how it got here, each on one line. */
export function TypeCell({ item }: { item: Evidence }) {
  const automated = automatedBy(item) !== null;
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid size-8 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-secondary">
        <Icon name={typeIcon(item.evidence_type)} className="size-4" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block whitespace-nowrap text-body-sm font-semibold text-text-primary">
          {typeLabel(item.evidence_type)}
        </span>
        <span className="flex items-center gap-1 whitespace-nowrap text-caption text-text-subtle">
          {automated ? (
            <>
              <Icon name="lightning" className="size-3 text-action-accent" aria-hidden />
              Automated
            </>
          ) : item.kind === "link" ? (
            "Link"
          ) : (
            "Uploaded"
          )}
        </span>
      </span>
    </div>
  );
}

/** Controls shown before the rest fold into a count. */
const SHOWN = 3;

type ControlLink = Evidence["control_links"][number];

function ControlTip({ link, control }: { link: ControlLink; control: Control | undefined }) {
  return (
    <span className="block">
      <span className="block font-semibold">
        {link.code}
        {control ? `: ${control.name}` : ""}
      </span>
      {link.criteria.length > 0 ? (
        <span className="block font-normal opacity-80">{link.criteria.join(" · ")}</span>
      ) : null}
    </span>
  );
}

/** The row opens the item when it is clicked, so what is clicked inside it must not. */
const keepRowClick = (event: MouseEvent) => event.stopPropagation();

/**
 * The controls an item supports, as the same code chips the controls library uses.
 * Each chip is a link to its control, and a name and the criteria it answers sit in a
 * tooltip that opens on focus as well as hover, so the row stays one line however many
 * controls an item has and the detail is still reachable from the keyboard.
 */
export function ControlsCell({
  links,
  controlIds,
  controlsByCode,
}: {
  links: ControlLink[];
  /** The id of each link's control, in the same order. */
  controlIds: string[];
  controlsByCode: Map<string, Control>;
}) {
  if (links.length === 0) {
    return <span className="text-caption text-status-warning-text">None</span>;
  }
  const rest = links.slice(SHOWN);
  return (
    <div className="flex flex-nowrap items-center gap-1 whitespace-nowrap">
      {links.slice(0, SHOWN).map((link, index) => {
        const control = controlsByCode.get(link.code);
        return (
          <Tooltip key={link.code} content={<ControlTip link={link} control={control} />}>
            <Link
              to={`/controls/${controlIds[index] ?? ""}`}
              onClick={keepRowClick}
              aria-label={control ? `${link.code}, ${control.name}` : link.code}
              className="rounded-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-action-accent"
            >
              <CodeChip code={link.code} />
            </Link>
          </Tooltip>
        );
      })}
      {rest.length > 0 ? (
        <Tooltip
          content={
            <span className="block space-y-1">
              {rest.map((link) => (
                <ControlTip key={link.code} link={link} control={controlsByCode.get(link.code)} />
              ))}
            </span>
          }
        >
          <button
            type="button"
            onClick={keepRowClick}
            aria-label={`${rest.length} more controls: ${rest.map((link) => link.code).join(", ")}`}
            className="rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption font-bold text-text-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-action-accent"
          >
            +{rest.length}
          </button>
        </Tooltip>
      ) : null}
    </div>
  );
}
