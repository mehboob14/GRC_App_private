import { useQuery } from "@tanstack/react-query";
import { Avatar, SearchableSelect } from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Assign a person — searchable, because a workspace has more members than a
 * plain select can be scanned for. One picker for every "who owns this?" field
 * so the same people, in the same order, appear everywhere.
 *
 * Membership ids, never user ids (rule 3): an owner is a member of *this*
 * tenant. Invited members are offered too — you can hand someone a control
 * before they have accepted, which is how onboarding actually runs.
 */
function useAssignableMembers() {
  const { principal } = useAuth();
  const canReadMembers = Boolean(principal?.permissions.includes("members:read"));

  const membersQuery = useQuery({
    queryKey: ["members"],
    queryFn: () => iamApi.listMembers(),
    enabled: canReadMembers,
  });

  // Without members:read the picker still works, offering the signed-in user
  // rather than 403-ing on a list they are not allowed to see.
  //
  // Invited members are kept — handing someone a control before they accept is
  // normal onboarding — but disabled ones are dropped: /members returns every
  // status, and a disabled account cannot answer for a control.
  const members = canReadMembers
    ? (membersQuery.data ?? [])
        .filter((member) => member.status !== "disabled")
        .map((member) => ({
          membership_id: member.membership_id,
          full_name: member.full_name,
          email: member.status === "invited" ? `${member.email} · invited` : member.email,
        }))
    : principal
      ? [
          {
            membership_id: principal.membership_id,
            full_name: principal.user.full_name,
            email: principal.user.email,
          },
        ]
      : [];

  return { members, isLoading: membersQuery.isLoading && canReadMembers };
}

export function OwnerSelect({
  value,
  onChange,
  disabled,
  className,
  placeholder = "Unassigned",
}: {
  value: string | null;
  onChange: (membershipId: string | null) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}) {
  const { members } = useAssignableMembers();

  const options = members.map((member) => ({
    value: member.membership_id,
    label: member.full_name,
    sublabel: member.email,
  }));

  return (
    <SearchableSelect
      options={options}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className={className}
      aria-label="Owner"
      placeholder={placeholder}
      searchPlaceholder="Search people…"
      clearLabel="Unassigned"
      renderValue={(option) =>
        option ? (
          <>
            <Avatar name={option.label} size="sm" />
            <span className="truncate">{option.label}</span>
          </>
        ) : (
          <span className="text-text-faint">{placeholder}</span>
        )
      }
      renderOption={(option) => (
        <>
          <Avatar name={option.label} size="sm" />
          <span className="min-w-0 flex-1">
            <span className="block truncate">{option.label}</span>
            {option.sublabel ? (
              <span className="block truncate text-caption text-text-subtle">
                {option.sublabel}
              </span>
            ) : null}
          </span>
        </>
      )}
    />
  );
}
