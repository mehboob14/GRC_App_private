import { Avatar, StatusPill } from "@/components/ui";
import { cn } from "@/lib/cn";

type MfaStatus = "Enabled" | "No MFA" | "Unknown";
type BgStatus = "Cleared" | "Missing" | "In progress" | "Unknown";
type PolicyStatus = { kind: "all" } | { kind: "pending"; count: number } | { kind: "unknown" };

type PersonRow = {
  id: string;
  full_name: string;
  email: string;
  role: string;
  group: string;
  mfa: MfaStatus;
  background: BgStatus;
  policies: PolicyStatus;
  last_active: string;
  last_active_stale?: boolean;
};

const PEOPLE: PersonRow[] = [
  {
    id: "1",
    full_name: "Marcus Bell",
    email: "marcus.bell@northwind.cloud",
    role: "Admin",
    group: "Engineering",
    mfa: "No MFA",
    background: "Cleared",
    policies: { kind: "pending", count: 2 },
    last_active: "3h ago",
  },
  {
    id: "2",
    full_name: "Tom Fletcher",
    email: "tom.fletcher@contractor.io",
    role: "Contributor",
    group: "Contractors",
    mfa: "Enabled",
    background: "Missing",
    policies: { kind: "pending", count: 5 },
    last_active: "98 days ago",
    last_active_stale: true,
  },
  {
    id: "3",
    full_name: "Owen Brooks",
    email: "owen.brooks@northwind.cloud",
    role: "Contributor",
    group: "Engineering",
    mfa: "Unknown",
    background: "Unknown",
    policies: { kind: "unknown" },
    last_active: "124 days ago",
    last_active_stale: true,
  },
  {
    id: "4",
    full_name: "Ahmed Hassan",
    email: "ahmed.hassan@northwind.cloud",
    role: "Contributor",
    group: "Sales",
    mfa: "No MFA",
    background: "Cleared",
    policies: { kind: "all" },
    last_active: "1d ago",
  },
  {
    id: "5",
    full_name: "Priya Nair",
    email: "priya.nair@northwind.cloud",
    role: "Workspace Manager",
    group: "Engineering",
    mfa: "Enabled",
    background: "In progress",
    policies: { kind: "all" },
    last_active: "Today",
  },
  {
    id: "6",
    full_name: "Alex Okafor",
    email: "alex.okafor@northwind.cloud",
    role: "Admin",
    group: "Security",
    mfa: "Enabled",
    background: "Cleared",
    policies: { kind: "all" },
    last_active: "Today",
  },
  {
    id: "7",
    full_name: "Riya Mehta",
    email: "riya.mehta@northwind.cloud",
    role: "Control Manager",
    group: "Security",
    mfa: "Enabled",
    background: "Cleared",
    policies: { kind: "all" },
    last_active: "Today",
  },
  {
    id: "8",
    full_name: "Jordan Park",
    email: "jordan.park@northwind.cloud",
    role: "Dev Ops Engineer",
    group: "Engineering",
    mfa: "Enabled",
    background: "Cleared",
    policies: { kind: "all" },
    last_active: "2h ago",
  },
  {
    id: "9",
    full_name: "Lena Cho",
    email: "lena.cho@northwind.cloud",
    role: "Policy Manager",
    group: "Legal",
    mfa: "Enabled",
    background: "Cleared",
    policies: { kind: "all" },
    last_active: "5h ago",
  },
];

function mfaTone(status: MfaStatus) {
  if (status === "Enabled") return "pass" as const;
  if (status === "No MFA") return "fail" as const;
  return "na" as const;
}

function bgTone(status: BgStatus) {
  if (status === "Cleared") return "pass" as const;
  if (status === "Missing") return "fail" as const;
  if (status === "In progress") return "review" as const;
  return "na" as const;
}

/** Figma A3 · Users (121:6208) — People directory. */
export function PeoplePage() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-[28px] font-extrabold leading-8 tracking-[-0.56px] text-text">
        People
      </h1>
      <p className="mt-2 text-[14px] leading-5 text-text-muted">
        One view: role, access, and compliance state inline.
      </p>

      <div className="mt-5 flex items-stretch gap-8 rounded-xl border border-border bg-bg-elevated px-5 py-4">
        <Stat value="51" label="people" />
        <Stat value="5" label="need attention" tone="fail" />
        <Stat value="2" label="privileged with gaps" tone="fail" />
        <Stat value="3" label="pending offboarding" tone="review" />
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-border bg-bg-elevated">
        <table className="w-full min-w-[980px] border-collapse text-left">
          <thead>
            <tr className="border-b border-border">
              {[
                "Person",
                "Role",
                "Groups",
                "MFA",
                "Background",
                "Policies",
                "Last active",
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 type-overline text-text-faint first:pl-[18px]"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {PEOPLE.map((person) => (
              <tr key={person.id} className="hover:bg-bg-sunken/60">
                <td className="px-4 py-3.5 first:pl-[18px]">
                  <div className="flex items-center gap-2.5">
                    <Avatar name={person.full_name} seed={person.email} size="sm" />
                    <div>
                      <p className="text-[13px] font-semibold text-text">
                        {person.full_name}
                      </p>
                      <p className="text-[12px] text-text-faint">{person.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3.5 text-[13px] text-text">{person.role}</td>
                <td className="px-4 py-3.5 text-[13px] text-text-muted">
                  {person.group}
                </td>
                <td className="px-4 py-3.5">
                  <StatusPill label={person.mfa} tone={mfaTone(person.mfa)} />
                </td>
                <td className="px-4 py-3.5">
                  <StatusPill
                    label={person.background}
                    tone={bgTone(person.background)}
                  />
                </td>
                <td className="px-4 py-3.5 text-[13px]">
                  {person.policies.kind === "all" ? (
                    <span className="text-text-muted">All signed</span>
                  ) : person.policies.kind === "pending" ? (
                    <span className="font-medium text-fail-fg">
                      {person.policies.count} pending
                    </span>
                  ) : (
                    <span className="text-fail-fg">Unknown</span>
                  )}
                </td>
                <td
                  className={cn(
                    "px-4 py-3.5 text-[13px]",
                    person.last_active_stale
                      ? "font-medium text-fail-fg"
                      : "text-text-muted",
                  )}
                >
                  {person.last_active}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({
  value,
  label,
  tone,
}: {
  value: string;
  label: string;
  tone?: "fail" | "review";
}) {
  return (
    <div>
      <p
        className={cn(
          "font-display text-[24px] font-bold leading-7",
          tone === "fail" && "text-fail-fg",
          tone === "review" && "text-review-fg",
          !tone && "text-text",
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-[12px] text-text-faint">{label}</p>
    </div>
  );
}
