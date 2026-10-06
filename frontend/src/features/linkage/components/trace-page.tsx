import { useMemo, type KeyboardEvent, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Badge,
  DetailHeader,
  EmptyState,
  ErrorState,
  Icon,
  PageHeader,
  SegmentedControl,
  Skeleton,
  StatusPill,
  statusFamilyFor,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { TRACE_MAX_DEPTH, type LinkType, type TraceNode } from "../api";
import { useTrace } from "../hooks";
import { humanize, isLinkType, LINK_META } from "../meta";

const DEPTHS = Array.from({ length: TRACE_MAX_DEPTH }, (_, i) => ({
  id: String(i + 1),
  label: String(i + 1),
}));

/** Evidence has no plural, so its sentence needs a different verb. */
const UNCOUNTABLE: ReadonlySet<LinkType> = new Set(["evidence"]);

function readDepth(raw: string | null): number {
  const depth = Number.parseInt(raw ?? "", 10);
  return depth >= 1 && depth <= TRACE_MAX_DEPTH ? depth : TRACE_MAX_DEPTH;
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

const statusFamily = (status: string) =>
  statusFamilyFor(humanize(status)) ?? "neutral";

/**
 * Everything connected to one record, hop by hop.
 *
 * The record the trace starts from is the header; the tree below is one level
 * per hop, each record once under the shortest path that reaches it. What the
 * signed in person may not read is not shown and not walked through, and the
 * page says so rather than looking complete.
 */
export function TracePage() {
  const { type = "", id = "" } = useParams();

  if (!isLinkType(type)) {
    return (
      <>
        <PageHeader title="Trace" />
        <ErrorState
          title="Not found"
          description="That kind of record cannot be traced."
        />
      </>
    );
  }
  return <TraceView type={type} id={id} />;
}

function TraceView({ type, id }: { type: LinkType; id: string }) {
  const [params, setParams] = useSearchParams();
  const depth = readDepth(params.get("depth"));
  const query = useTrace(type, id, depth);
  const meta = LINK_META[type];
  const data = query.data;

  const childrenOf = useMemo(() => {
    const map = new Map<string, TraceNode[]>();
    for (const node of data?.nodes ?? []) {
      const key = node.parent_key ?? "";
      const siblings = map.get(key);
      if (siblings) siblings.push(node);
      else map.set(key, [node]);
    }
    return map;
  }, [data]);

  const setDepth = (next: string) =>
    setParams(next === String(TRACE_MAX_DEPTH) ? {} : { depth: next }, {
      replace: true,
    });

  let body: ReactNode;
  if (query.isLoading) {
    body = <TraceSkeleton />;
  } else if (query.isError || !data) {
    const error = describeError(query.error, "record");
    body = (
      <ErrorState
        title={error.title}
        description={error.message}
        onRetry={error.retryable ? () => void query.refetch() : undefined}
      />
    );
  } else {
    const start = data.start;
    const roots = childrenOf.get(start.key) ?? [];
    const count = data.nodes.length;
    // Records the person cannot read may be linked, so "nothing linked" would be a guess.
    const nothing =
      data.hidden_types.length > 0 ? "Nothing to show" : "Nothing linked yet";
    body = (
      <>
        <DetailHeader
          backTo={meta.href(id)}
          backLabel={`Back to ${meta.label.toLowerCase()}`}
          icon={meta.icon}
          title={start.title}
          chips={
            <>
              {start.code ? <Badge variant="neutral">{start.code}</Badge> : null}
              <StatusPill
                status={statusFamily(start.status)}
                label={humanize(start.status)}
                kind="inline"
              />
            </>
          }
          meta={
            <span>
              {meta.label} trace, up to {depth} {depth === 1 ? "hop" : "hops"}{" "}
              away
            </span>
          }
          actions={
            <div className="flex items-center gap-2">
              <span className="text-caption text-text-subtle">Depth</span>
              <SegmentedControl
                label="Trace depth"
                items={DEPTHS}
                value={String(depth)}
                onChange={setDepth}
              />
            </div>
          }
        />

        <section className="rounded-lg border border-border bg-surface-primary">
          <header className="border-b border-border px-5 py-4">
            <h2 className="font-display text-title-md text-text-primary">
              Connected records
            </h2>
            <p className="text-caption text-text-subtle">
              {count === 0
                ? nothing
                : `${count} ${count === 1 ? "record" : "records"}`}
            </p>
          </header>

          <div className="space-y-4 p-5">
            {data.hidden_types.map((hidden) => (
              <Note key={hidden}>
                {LINK_META[hidden].plural}{" "}
                {UNCOUNTABLE.has(hidden) ? "is" : "are"} not shown because you
                do not have access to {UNCOUNTABLE.has(hidden) ? "it" : "them"}.
              </Note>
            ))}
            {data.truncated ? (
              <Note>
                Not every record is shown. A record lists up to{" "}
                {data.neighbour_limit} of a kind, and a trace stops at{" "}
                {data.node_limit} records.
              </Note>
            ) : null}

            {roots.length === 0 ? (
              <EmptyState
                icon="link"
                title={nothing}
                description={`Records linked to this ${meta.label.toLowerCase()} show here, one level for each hop.`}
              />
            ) : (
              <Tree
                nodes={roots}
                childrenOf={childrenOf}
                label={`Records connected to ${start.title}`}
              />
            )}
          </div>
        </section>
      </>
    );
  }

  return (
    <div>
      <PageHeader title="Trace" />
      {body}
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return (
    <p
      role="note"
      className="rounded-md bg-surface-sunken px-3 py-2.5 text-body-sm text-text-subtle"
    >
      {children}
    </p>
  );
}

/** Up and down move between the records, Home and End jump to the first and last. */
function moveFocus(event: KeyboardEvent<HTMLUListElement>) {
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
  const links = Array.from(
    event.currentTarget.querySelectorAll<HTMLAnchorElement>("a[data-trace-link]"),
  );
  if (links.length === 0) return;
  const current = links.findIndex((link) => link === document.activeElement);
  const last = links.length - 1;
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? last
        : Math.min(Math.max(current + (event.key === "ArrowDown" ? 1 : -1), 0), last);
  event.preventDefault();
  links[next].focus();
}

function Tree({
  nodes,
  childrenOf,
  label,
}: {
  nodes: TraceNode[];
  childrenOf: Map<string, TraceNode[]>;
  label: string;
}) {
  return (
    <ul
      role="tree"
      aria-label={label}
      onKeyDown={moveFocus}
      className="space-y-1"
    >
      {nodes.map((node) => (
        <Branch key={node.key} node={node} childrenOf={childrenOf} nested={false} />
      ))}
    </ul>
  );
}

/**
 * One record and what hangs off it. The elbow joins a record to the line down
 * its parent; the line carries on to the next sibling unless this is the last.
 * Rows are a fixed 2.5rem tall, so the elbow always lands on the row's middle.
 */
function Branch({
  node,
  childrenOf,
  nested,
}: {
  node: TraceNode;
  childrenOf: Map<string, TraceNode[]>;
  nested: boolean;
}) {
  const children = childrenOf.get(node.key) ?? [];
  return (
    <li
      role="treeitem"
      aria-level={node.depth}
      aria-labelledby={rowId(node)}
      className={cn(
        nested &&
          "relative pl-5 before:absolute before:left-0 before:top-0 before:h-5 before:w-5 before:rounded-bl-md before:border-b before:border-l before:border-border-strong before:content-[''] after:absolute after:bottom-0 after:left-0 after:top-5 after:border-l after:border-border-strong after:content-[''] last:after:hidden",
      )}
    >
      <Row node={node} />
      {children.length > 0 ? (
        <ul role="group" className="ml-[22px]">
          {children.map((child) => (
            <Branch key={child.key} node={child} childrenOf={childrenOf} nested />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** A record's row names its tree item, so a parent is not read out with everything under it. */
const rowId = (node: TraceNode) => `trace-${node.key}`;

function Row({ node }: { node: TraceNode }) {
  const meta = LINK_META[node.type];
  return (
    <div
      id={rowId(node)}
      className="flex h-10 items-center gap-3 rounded-md px-2 transition-colors hover:bg-surface-hover"
    >
      <span className="grid size-7 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-subtle">
        <Icon name={meta.icon} className="size-4" />
      </span>
      <Link
        to={meta.href(node.id)}
        data-trace-link
        className="min-w-0 flex-1 truncate rounded-sm text-body-sm font-medium text-text-primary hover:text-text-link focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
      >
        <span className="sr-only">{meta.label} </span>
        {node.code ? (
          <span className="mr-1.5 font-mono text-caption font-semibold text-text-subtle">
            {node.code}
          </span>
        ) : null}
        {node.title}
      </Link>
      <StatusPill
        status={statusFamily(node.status)}
        label={humanize(node.status)}
        kind="inline"
        className="shrink-0"
      />
      {node.relation ? (
        <span className="hidden shrink-0 text-caption text-text-subtle sm:inline">
          {node.relation}
        </span>
      ) : null}
      {node.linked_at ? (
        <span
          title={node.linked_by ? `Linked by ${node.linked_by}` : undefined}
          className="tabular hidden shrink-0 text-caption text-text-subtle md:inline"
        >
          linked {fmtDate(node.linked_at)}
        </span>
      ) : null}
    </div>
  );
}

function TraceSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <Skeleton className="h-16 w-full" />
      <div className="space-y-2 rounded-lg border border-border bg-surface-primary p-5">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className={cn("h-10", i % 3 !== 0 && "ml-8")} />
        ))}
      </div>
    </div>
  );
}
