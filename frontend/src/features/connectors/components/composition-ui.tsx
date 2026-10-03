import { Link } from "react-router-dom";
import { Badge, Icon, StatusPill, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import type {
  AutomationStatus,
  ComposeMode,
  Composition,
  CompositionSource,
} from "../api";
import { MODE, MODULE, SOURCE_STATE } from "./composition-meta";

/**
 * The shared words and marks for "what evidences this control": the Checks tab,
 * the controls register and the criterion view all draw from here, so a source
 * never reads one way in one place and another way in the next.
 */

/** A provider's mark, or Verity's own for the built in modules. */
export function SourceMark({
  providerKey,
  name,
  size = 22,
}: {
  providerKey: string;
  name: string;
  size?: number;
}) {
  if (providerKey === "verity") {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-xs bg-action-accent text-white"
        style={{ width: size, height: size }}
        aria-hidden
      >
        <Icon name="controls" className={size >= 22 ? "size-3.5" : "size-3"} />
      </span>
    );
  }
  return <ConnectorLogo id={providerKey} name={name} size={size} />;
}

export function ModeBadge({ mode }: { mode: ComposeMode }) {
  return (
    <Badge variant={mode === "manual" ? "neutral" : "role"}>
      {MODE[mode].label}
    </Badge>
  );
}

/** One capability and the system that supplies it, as a compact chip. */
export function SourceChip({ source }: { source: CompositionSource }) {
  const state = SOURCE_STATE[source.state];
  const names = source.providers.join(", ");
  const shown = source.providers.slice(0, 3);
  return (
    <Tooltip
      content={`${source.name}: ${state.label}${names ? `. ${names}` : ""}`}
    >
      <span
        className={cn(
          "inline-flex items-center gap-2 rounded-lg border px-2.5 py-1.5",
          source.state === "connected"
            ? "border-status-success-border bg-status-success-bg"
            : "border-border bg-surface-primary",
        )}
      >
        <span className="flex -space-x-1.5">
          {source.provider_keys.slice(0, 3).map((key, index) => (
            <SourceMark
              key={key}
              providerKey={key}
              name={shown[index] ?? key}
              size={20}
            />
          ))}
        </span>
        <span className="text-body-sm font-semibold text-text-primary">
          {source.name}
        </span>
        <span
          className={cn(
            "text-caption",
            source.state === "connected"
              ? "font-semibold text-status-success-text"
              : "text-text-subtle",
          )}
        >
          {state.label}
        </span>
      </span>
    </Tooltip>
  );
}

/** What evidences a control, small enough for a table cell. */
export function EvidencedBy({
  composition,
  className,
  size = 20,
}: {
  composition: Composition;
  className?: string;
  size?: number;
}) {
  const connectors = composition.sources.filter((s) => s.kind === "connector");
  const platform = composition.sources.some((s) => s.kind === "platform");
  const people = composition.items_manual + composition.items_planned > 0;
  if (connectors.length === 0 && !platform && !people) {
    return <span className="text-body-sm text-text-subtle">Not set</span>;
  }
  const marks = connectors.flatMap((s) =>
    s.provider_keys.slice(0, 1).map((key) => ({ key: `${s.key}:${key}`, source: s, providerKey: key })),
  );
  return (
    <span className={cn("flex items-center gap-1.5", className)}>
      {marks.slice(0, 2).map(({ key, source, providerKey }) => (
        <Tooltip
          key={key}
          content={`${source.name}: ${SOURCE_STATE[source.state].label}`}
        >
          <span
            className={cn(
              "rounded-xs",
              source.state === "connected" ? "" : "opacity-60",
            )}
          >
            <SourceMark
              providerKey={providerKey}
              name={source.providers[0] ?? providerKey}
              size={size}
            />
          </span>
        </Tooltip>
      ))}
      {marks.length > 2 ? (
        <span className="text-caption text-text-subtle">+{marks.length - 2}</span>
      ) : null}
      {platform ? (
        <Tooltip content="Verity modules">
          <span>
            <SourceMark providerKey="verity" name="Verity" size={size} />
          </span>
        </Tooltip>
      ) : null}
      {people ? (
        <Tooltip content="People provide some of the evidence">
          <span
            className="grid place-items-center rounded-xs bg-surface-sunken text-text-secondary"
            style={{ width: size, height: size }}
          >
            <Icon name="users" className="size-3" />
          </span>
        </Tooltip>
      ) : null}
    </span>
  );
}

/** Where the module that holds an evidence item lives. */
export function ModuleLink({ module }: { module: string | null }) {
  const target = module ? MODULE[module] : undefined;
  if (!target) return null;
  return (
    <Link
      to={target.to}
      className="font-semibold text-action-accent hover:underline"
    >
      {target.label}
    </Link>
  );
}

/** What the checks last found, in a word. Said only when they have found something. */
export function MonitoringWord({ status }: { status: AutomationStatus | null }) {
  if (status === "failing") {
    return <StatusPill kind="inline" status="danger" label="Failing" />;
  }
  if (status === "passing") {
    return <StatusPill kind="inline" status="success" label="Passing" />;
  }
  if (status === "error") {
    return <StatusPill kind="inline" status="warning" label="Could not check" />;
  }
  return null;
}
