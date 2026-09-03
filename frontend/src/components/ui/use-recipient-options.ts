import { useQuery } from "@tanstack/react-query";
import type { Person } from "@/components/ui/person-select";
import { describeError } from "@/lib/api/describe-error";
import { iamApi } from "@/lib/api/endpoints";
import type { RecipientSelection } from "@/components/ui/recipient-picker";

export const EMPTY_RECIPIENTS: RecipientSelection = {
  user_ids: [],
  role_ids: [],
  group_ids: [],
};

export const isEmptyRecipients = (s: RecipientSelection): boolean =>
  s.user_ids.length === 0 && s.role_ids.length === 0 && s.group_ids.length === 0;

/**
 * Members, roles and groups for a RecipientPicker, loaded once and shared by
 * every picker on a page. `error` is set when any of the three lists failed,
 * since a reviewer/approver picker with a partial list would silently let the
 * owner miss someone.
 */
export function useRecipientOptions() {
  const membersQuery = useQuery({ queryKey: ["members"], queryFn: () => iamApi.listMembers() });
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: () => iamApi.listRoles() });
  const groupsQuery = useQuery({ queryKey: ["groups"], queryFn: () => iamApi.listGroups() });

  const people: Person[] = (membersQuery.data ?? []).map((m) => ({
    id: m.membership_id,
    name: m.full_name,
    email: m.email,
  }));
  const roles: Person[] = (rolesQuery.data ?? []).map((r) => ({
    id: r.id,
    name: r.name,
    email: `${r.assignment_count} assigned`,
  }));
  const groups: Person[] = (groupsQuery.data ?? []).map((g) => ({
    id: g.id,
    name: g.name,
    email: `${g.member_count} members`,
  }));

  const failed = [membersQuery, rolesQuery, groupsQuery].find((q) => q.isError);
  const error = failed ? describeError(failed.error, "recipient list").message : null;

  return { people, roles, groups, error, isLoading: membersQuery.isLoading };
}
