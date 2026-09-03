import { useQuery } from "@tanstack/react-query";
import { Avatar, SearchableSelect } from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
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

  return {
    members,
    isLoading: membersQuery.isLoading && canReadMembers,
    // A picker offering nobody looks like an empty workspace. When the list
    // failed to load, say so instead of letting it read that way.
    loadError:
      canReadMembers && membersQuery.isError
        ? describeError(membersQuery.error, "people list").message
        : null,
  };
}

export function OwnerSelect({
  value,
  valueLabel,
  onChange,
  disabled,
  className,
  placeholder = "Unassigned",
}: {
  value: string | null;
  /** The owner's name as the server reports it — see the fallback below. */
  valueLabel?: string | null;
  onChange: (membershipId: string | null) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}) {
  const { members, loadError } = useAssignableMembers();

  const options = members.map((member) => ({
    value: member.membership_id,
    label: member.full_name,
    sublabel: member.email,
  }));

  // A picker that cannot represent its own current value would render a real
  // owner as "Unassigned" — which happens when that person's membership was
  // later disabled, or when the viewer cannot read the member list at all. The
  // control still has an owner and the server still names them, so carry the
  // value as its own option rather than silently reporting the opposite.
  if (value && !options.some((option) => option.value === value)) {
    options.unshift({
      value,
      label: valueLabel ?? "Current owner",
      sublabel: "no longer an active member",
    });
  }

  return (
    <>
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
    {loadError ? (
      <p className="mt-1 text-body-sm text-status-danger-text">{loadError}</p>
    ) : null}
    </>
  );
}
