import { Icon } from "@/components/ui/icon";
import { PeopleSelect, type Person } from "@/components/ui/person-select";

/** A pick of people, roles and groups — the shape every assignment surface
 *  (document approval tiers, acknowledgement campaigns, vulnerability
 *  assignment) sends to its API. */
export type RecipientSelection = {
  user_ids: string[];
  role_ids: string[];
  group_ids: string[];
};


/**
 * People, roles and groups pickers for one target, e.g. reviewers, approvers,
 * or acknowledgement recipients. Shared by the tier-assignment card and the
 * acknowledgement campaign dialog, which both target a document the same way.
 * Pair with `useRecipientOptions` for the `people`/`roles`/`groups` lists.
 */
export function RecipientPicker({
  label,
  people,
  roles,
  groups,
  value,
  onChange,
}: {
  label: string;
  people: Person[];
  roles: Person[];
  groups: Person[];
  value: RecipientSelection;
  onChange: (next: RecipientSelection) => void;
}) {
  return (
    <fieldset className="space-y-3 rounded-md border border-border p-3">
      <legend className="px-1 text-label-md font-bold text-text-primary">{label}</legend>
      <div>
        <span className="mb-1 flex items-center gap-1.5 text-caption text-text-subtle">
          <Icon name="users" className="size-3.5" />
          People
        </span>
        <PeopleSelect
          people={people}
          values={value.user_ids}
          onChange={(user_ids) => onChange({ ...value, user_ids })}
          placeholder="Add people…"
        />
      </div>
      <div>
        <span className="mb-1 flex items-center gap-1.5 text-caption text-text-subtle">
          <Icon name="shield" className="size-3.5" />
          Roles
        </span>
        <PeopleSelect
          people={roles}
          values={value.role_ids}
          onChange={(role_ids) => onChange({ ...value, role_ids })}
          placeholder="Add roles…"
        />
      </div>
      <div>
        <span className="mb-1 flex items-center gap-1.5 text-caption text-text-subtle">
          <Icon name="layers" className="size-3.5" />
          Groups
        </span>
        <PeopleSelect
          people={groups}
          values={value.group_ids}
          onChange={(group_ids) => onChange({ ...value, group_ids })}
          placeholder="Add groups…"
        />
      </div>
    </fieldset>
  );
}
