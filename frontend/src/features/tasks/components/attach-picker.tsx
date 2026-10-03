import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Checkbox, Icon, SearchInput, StatusPill } from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { listEvidenceOptions } from "../api";
import { EVIDENCE_FRESHNESS } from "../tokens";
import { useAttachAccess, type AttachSelection } from "./attach-selection";

// Picker hint only: the store's magic-byte allow-list is the real gate, and a file it
// refuses comes back as the API's own message.
const FILE_ACCEPT = ".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.xlsx,.pptx,.txt,.csv,.log,.md,.json";

const humanType = (t: string) => t.replace(/_/g, " ");

/**
 * Choose evidence for a task: tick items from the library, and/or add files. Nothing is sent
 * from here; the caller sends the selection with its own request, so a refused file stops that
 * request rather than leaving it half done.
 */
export function AttachPicker({
  value,
  onChange,
  alreadyAttached = [],
}: {
  value: AttachSelection;
  onChange: (next: AttachSelection) => void;
  /** Evidence ids already on the task, left out of the list. */
  alreadyAttached?: readonly string[];
}) {
  const { canPick, canUpload } = useAttachAccess();
  const [search, setSearch] = useState("");
  const query = useQuery({ queryKey: ["task-evidence-options"], queryFn: listEvidenceOptions, enabled: canPick });

  const options = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (query.data ?? [])
      .filter((e) => !alreadyAttached.includes(e.id))
      .filter((e) => needle === "" || e.title.toLowerCase().includes(needle));
  }, [query.data, search, alreadyAttached]);

  const toggle = (id: string, on: boolean) =>
    onChange({
      ...value,
      evidenceIds: on ? [...value.evidenceIds, id] : value.evidenceIds.filter((x) => x !== id),
    });

  return (
    <div className="space-y-3">
      {canPick ? (
        <div>
          <p className="mb-1.5 font-sans text-label-sm text-text-secondary">From the evidence library</p>
          <SearchInput value={search} onChange={setSearch} placeholder="Search evidence…" aria-label="Search evidence" />
          <div className="mt-2 max-h-44 overflow-y-auto rounded-sm border border-border">
            {query.isLoading ? (
              <p className="px-3 py-3 text-body-sm text-text-subtle">Loading…</p>
            ) : query.isError ? (
              <p className="px-3 py-3 text-body-sm text-status-danger-text">
                {describeError(query.error, "evidence library").message}
              </p>
            ) : options.length === 0 ? (
              <p className="px-3 py-3 text-body-sm text-text-subtle">
                {search ? "Nothing matches that search." : "No evidence to attach."}
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {options.map((e) => {
                  const checked = value.evidenceIds.includes(e.id);
                  const freshness = EVIDENCE_FRESHNESS[e.freshness];
                  return (
                    <li key={e.id}>
                      <label className="flex cursor-pointer items-center gap-2.5 px-3 py-2 hover:bg-surface-hover">
                        <Checkbox checked={checked} onCheckedChange={(on) => toggle(e.id, on)} aria-label={e.title} />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-body-sm text-text-primary">{e.title}</span>
                          <span className="block text-caption text-text-subtle">
                            {humanType(e.evidence_type)} · {e.kind === "link" ? "Link" : "File"}
                          </span>
                        </span>
                        {freshness.show ? (
                          <StatusPill kind="inline" status={freshness.family} label={freshness.label} />
                        ) : null}
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      ) : null}

      {canUpload ? (
        <div>
          <label htmlFor="task-attach-files" className="mb-1.5 block font-sans text-label-sm text-text-secondary">
            Upload files
          </label>
          <input
            id="task-attach-files"
            type="file"
            multiple
            accept={FILE_ACCEPT}
            onChange={(e) => {
              const picked = Array.from(e.target.files ?? []);
              if (picked.length > 0) onChange({ ...value, files: [...value.files, ...picked] });
              e.target.value = "";
            }}
            className="block w-full rounded-sm border border-border bg-surface-primary py-2 pr-3 text-body-sm text-text-secondary file:mr-3 file:h-9 file:border-0 file:border-r file:border-border file:bg-surface-sunken file:px-3 file:text-label-sm file:text-text-primary"
          />
          <p className="mt-1.5 text-caption text-text-subtle">
            PDF, images, Office files, CSV or text. Each becomes an evidence item.
          </p>
          {value.files.length > 0 ? (
            <ul className="mt-2 space-y-1.5">
              {value.files.map((f, i) => (
                <li
                  key={`${f.name}-${i}`}
                  className="flex items-center gap-2 rounded-sm border border-border px-3 py-1.5"
                >
                  <Icon name="paperclip" className="size-4 shrink-0 text-text-subtle" />
                  <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">{f.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Remove ${f.name}`}
                    onClick={() => onChange({ ...value, files: value.files.filter((_, j) => j !== i) })}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
