import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  SearchInput,
  Skeleton,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { Member } from "@/lib/api/types";

/** Stable identity so the filter memo doesn't re-run on every render. */
const EMPTY_MEMBERS: Member[] = [];

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  /** Memberships already selected — pre-ticked, and the baseline for the diff. */
  initialSelected: string[];
  saving?: boolean;
  error?: string | null;
  /**
   * Called with the diff, not the whole selection: the two callers both write
   * per-person (assign one role, add/remove one group member), so replaying the
   * unchanged rows would be pointless writes and pointless audit noise.
   */
  onConfirm: (change: { added: string[]; removed: string[] }) => void;
};

export function MemberPickerDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  initialSelected,
  saving = false,
  error = null,
  onConfirm,
}: Props) {
  const { principal } = useAuth();
  const [selected, setSelected] = useState<string[]>(initialSelected);
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["members", principal?.tenant_id],
    queryFn: () => iamApi.listMembers(),
    enabled: open,
  });

  // Re-seed each time the dialog opens so a cancelled edit doesn't leak into
  // the next one.
  useEffect(() => {
    if (open) {
      setSelected(initialSelected);
      setSearch("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-seed on open only
  }, [open]);

  const { data: members = EMPTY_MEMBERS } = query;
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return members;
    return members.filter(
      (m) =>
        m.full_name.toLowerCase().includes(needle) ||
        m.email.toLowerCase().includes(needle),
    );
  }, [members, search]);

  const added = selected.filter((id) => !initialSelected.includes(id));
  const removed = initialSelected.filter((id) => !selected.includes(id));
  const dirty = added.length > 0 || removed.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md" scrollBody>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <DialogBody className="flex min-h-0 flex-col gap-3">
          {error ? (
            <ErrorBanner title="Couldn't save">{error}</ErrorBanner>
          ) : null}

          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search people by name or email"
            aria-label="Search people"
          />

          <div className="max-h-[46vh] min-h-0 overflow-y-auto rounded-md border border-border">
            {query.isLoading ? (
              <div className="space-y-2 p-3">
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </div>
            ) : query.isError ? (
              // Never render "nobody is here" for a request that failed — an
              // admin acting on that would draw the wrong conclusion.
              <div className="p-4">
                <p className="text-body-md text-text-primary">
                  Couldn’t load people.
                </p>
                <p className="mt-1 text-body-sm text-text-secondary">
                  {query.error instanceof ApiError
                    ? query.error.message
                    : "The request failed."}
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  className="mt-3"
                  onClick={() => void query.refetch()}
                >
                  Retry
                </Button>
              </div>
            ) : visible.length === 0 ? (
              <p className="p-4 text-body-md text-text-secondary">
                {members.length === 0
                  ? "No one has joined this workspace yet."
                  : `No one matches “${search.trim()}”.`}
              </p>
            ) : (
              <ul>
                {visible.map((member) => {
                  const checked = selected.includes(member.membership_id);
                  return (
                    <li
                      key={member.membership_id}
                      className="border-b border-border last:border-b-0"
                    >
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-surface-hover">
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(value) =>
                            setSelected((prev) =>
                              value
                                ? [...prev, member.membership_id]
                                : prev.filter(
                                    (id) => id !== member.membership_id,
                                  ),
                            )
                          }
                        />
                        <span className="min-w-0">
                          <span className="block truncate text-body-md font-semibold text-text-primary">
                            {member.full_name}
                          </span>
                          <span className="block truncate text-body-sm text-text-secondary">
                            {member.email}
                            {member.status !== "active"
                              ? ` · ${member.status}`
                              : ""}
                          </span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <p className="text-body-sm text-text-secondary" aria-live="polite">
            {added.length > 0 || removed.length > 0
              ? [
                  added.length > 0 ? `${added.length} to add` : null,
                  removed.length > 0 ? `${removed.length} to remove` : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : `${selected.length} selected`}
          </p>
        </DialogBody>

        <DialogFooter>
          <Button
            type="button"
            variant="secondary"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            loading={saving}
            disabled={!dirty}
            onClick={() => onConfirm({ added, removed })}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
