import { useId, useState } from "react";
import { Checkbox, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { PermissionKey } from "@/lib/api/types";

/**
 * Every permission the backend knows, grouped by the thing it acts on.
 *
 * This list must stay exhaustive over `PERMISSION_KEYS`: the PATCH sends
 * `permission_keys` as a full replacement set, so a key missing from this
 * editor would be silently stripped from any role someone edits. The
 * `_exhaustive` check below fails the build if a new key is added upstream and
 * not listed here.
 */
const PERMISSION_GROUPS = [
  {
    group: "Workspace",
    summary: "Company profile, security policy and the audit log.",
    items: [
      { key: "tenant:read", label: "Read workspace" },
      { key: "tenant:manage", label: "Manage company profile" },
      { key: "security:manage", label: "Manage security policy" },
      { key: "audit:read", label: "Read audit log" },
    ],
  },
  {
    group: "People",
    summary: "Who can see, invite and disable members.",
    items: [
      { key: "members:read", label: "View members" },
      { key: "members:invite", label: "Invite members" },
      { key: "members:disable", label: "Disable members" },
      { key: "members:manage", label: "Edit member details" },
    ],
  },
  {
    group: "Access",
    summary: "Groups, roles and what they grant.",
    items: [
      { key: "groups:read", label: "View groups" },
      { key: "groups:manage", label: "Manage groups" },
      { key: "roles:read", label: "View roles" },
      {
        key: "roles:manage",
        label: "Manage roles",
        hint: "At least one role with members must keep this.",
      },
    ],
  },
  {
    group: "Compliance",
    summary: "Frameworks, controls and evidence.",
    items: [
      { key: "frameworks:read", label: "View frameworks" },
      { key: "controls:manage", label: "Manage controls" },
      { key: "evidence:read", label: "View evidence" },
      { key: "evidence:manage", label: "Manage evidence" },
    ],
  },
] as const satisfies readonly {
  group: string;
  summary: string;
  items: readonly { key: PermissionKey; label: string; hint?: string }[];
}[];

type ListedKey = (typeof PERMISSION_GROUPS)[number]["items"][number]["key"];

/**
 * Compile error naming any `PermissionKey` this editor forgot.
 *
 * The previous version of this built a `Record<PermissionKey, true>` from the
 * listed keys and cast it — which type-checks whatever is in the list, so it
 * never caught anything. `members:manage` was added upstream and slipped
 * through exactly that hole. Keep it as a type relation, not a value cast.
 */
type MissingPermission = Exclude<PermissionKey, ListedKey>;
const _allPermissionsListed: [MissingPermission] extends [never]
  ? true
  : { error: "add these to PERMISSION_GROUPS"; missing: MissingPermission } = true;
void _allPermissionsListed;

type Props = {
  value: PermissionKey[];
  onChange: (next: PermissionKey[]) => void;
};

/**
 * Grouped permission editor. Every group starts collapsed — fifteen checkboxes
 * open at once is a wall, and the answer to "what does this role do?" is the
 * group summary, not the individual keys.
 *
 * Collapsing only works if the closed row still answers "is anything set in
 * here?", so each header carries a selected count and names what is ticked. A
 * disclosure that hides state is worse than no disclosure.
 */
export function PermissionPicker({ value, onChange }: Props) {
  const [expanded, setExpanded] = useState<string[]>([]);

  const toggleKey = (key: PermissionKey, checked: boolean) =>
    onChange(checked ? [...value, key] : value.filter((k) => k !== key));

  return (
    <div className="divide-y divide-border rounded-lg border border-border">
      {PERMISSION_GROUPS.map((section) => (
        <PermissionGroup
          key={section.group}
          section={section}
          value={value}
          open={expanded.includes(section.group)}
          onOpenChange={(next) =>
            setExpanded((prev) =>
              next
                ? [...prev, section.group]
                : prev.filter((g) => g !== section.group),
            )
          }
          onToggleKey={toggleKey}
        />
      ))}
    </div>
  );
}

function PermissionGroup({
  section,
  value,
  open,
  onOpenChange,
  onToggleKey,
}: {
  section: (typeof PERMISSION_GROUPS)[number];
  value: PermissionKey[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onToggleKey: (key: PermissionKey, checked: boolean) => void;
}) {
  const panelId = useId();
  const selected = section.items.filter((i) => value.includes(i.key));

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onOpenChange(!open)}
        className={cn(
          "flex w-full items-center gap-3 px-3 py-3 text-left",
          // No focus ring here: tokens.css F9 gives every :focus-visible a 2px
          // action-accent outline globally.
          "hover:bg-surface-hover",
          open ? "rounded-t-lg" : "rounded-lg",
        )}
      >
        <Icon
          name="chevr"
          aria-hidden
          className={cn(
            "size-4 shrink-0 text-text-subtle transition-transform duration-150",
            open && "rotate-90",
          )}
        />
        <span className="min-w-0 flex-1">
          <span className="block font-sans text-label-md font-semibold text-text-primary">
            {section.group}
          </span>
          {/* Closed rows must still say what is set — otherwise collapsing
              hides the answer the reader came for. */}
          <span className="block truncate text-body-sm text-text-secondary">
            {selected.length === 0
              ? section.summary
              : selected.map((i) => i.label).join(", ")}
          </span>
        </span>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 font-sans text-label-sm tabular-nums",
            selected.length > 0
              ? "bg-action-accent-tint text-action-accent"
              : "bg-surface-sunken text-text-subtle",
          )}
        >
          {selected.length}/{section.items.length}
        </span>
      </button>

      {open ? (
        <div
          id={panelId}
          // grid-cols-1 is load-bearing, not decoration: without an explicit
          // base the implicit track sizes to max-content and the longest label
          // pushes the panel wider than the dialog on a narrow screen.
          className="grid grid-cols-1 gap-x-4 gap-y-2.5 px-3 pb-3 pl-10 sm:grid-cols-2"
        >
          {section.items.map((perm) => {
            // `as const` narrows each item exactly, so members without a hint
            // have no such property to read — ask before reaching for it.
            const hint = "hint" in perm ? perm.hint : undefined;
            return (
            <label
              key={perm.key}
              className="flex items-start gap-2 text-body-md text-text-primary"
            >
              <Checkbox
                className="mt-0.5 shrink-0"
                checked={value.includes(perm.key)}
                onCheckedChange={(checked) => onToggleKey(perm.key, !!checked)}
              />
              <span className="min-w-0">
                {perm.label}
                {hint ? (
                  <span className="block text-body-sm text-text-secondary">
                    {hint}
                  </span>
                ) : null}
              </span>
            </label>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
