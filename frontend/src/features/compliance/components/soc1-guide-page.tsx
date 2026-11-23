import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader, Skeleton, StatusPill } from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * SOC 1 guidance (guided onboarding S1-1 to S1-3, part 5 section 9). Guidance only: no SOC 1
 * engagement, readiness figure or generated objective exists. Lists the controls you already
 * run that a SOC 1 auditor will treat as general IT controls.
 */

const AREAS: { area: string; codes: string[] }[] = [
  {
    area: "Access to programs and data",
    codes: ["IAM-01", "IAM-02", "IAM-03", "IAM-04", "IAM-06", "IAM-07", "IAM-08", "IAM-09", "IAM-10", "IAM-12", "HR-05"],
  },
  { area: "Program change", codes: ["SD-01", "SD-02", "SD-04", "SD-06", "SD-10", "SD-12", "SD-13", "SD-14"] },
  { area: "Computer operations", codes: ["BC-01", "BC-02", "BC-04", "LM-02", "LM-04", "LM-06", "LM-07", "SD-08"] },
  { area: "Physical and environmental", codes: ["PE-01", "PE-02", "PE-03"] },
  { area: "Entity level", codes: ["GOV-14", "GOV-02", "GOV-04", "GOV-12", "GOV-18", "GOV-21", "HR-01", "HR-08"] },
  { area: "Subservice organisations", codes: ["BC-07", "BC-08", "PE-01"] },
];

type Control = { id: string; code: string; name: string; status: string };

const STATE: Record<string, { family: StatusFamily; label: string }> = {
  implemented: { family: "success", label: "Implemented" },
  in_progress: { family: "progress", label: "In progress" },
  not_started: { family: "neutral", label: "Not started" },
  not_applicable: { family: "neutral", label: "Not applicable" },
};

export function Soc1GuidePage() {
  const { principal } = useAuth();
  const controls = useQuery({
    queryKey: ["controls", principal?.tenant_id, "soc1"],
    queryFn: () => apiFetch<Control[]>("/controls"),
  });
  const byCode = new Map((controls.data ?? []).map((c) => [c.code, c]));

  return (
    <div className="mx-auto w-full max-w-[900px]">
      <PageHeader title="SOC 1" />
      <div className="mt-3 space-y-2 text-body-md text-text-secondary">
        <p>
          A SOC 1 report is for customers whose financial statements depend on your service. It is
          not a step before SOC 2: the two answer different questions.
        </p>
        <p>
          There is no fixed list of requirements. You write control objectives with your audit firm,
          and they judge them before testing. Plan for the extra time that takes.
        </p>
        <p>
          Verity gives guidance only here. The controls below are ones a SOC 1 auditor usually treats
          as general IT controls, with where they stand in your workspace.
        </p>
      </div>
      {controls.isLoading ? (
        <Skeleton className="mt-4 h-64 w-full rounded-lg" />
      ) : (
        <div className="mt-4 space-y-3">
          {AREAS.map((a) => (
            <section key={a.area} className="rounded-lg border border-border bg-surface-primary">
              <h2 className="border-b border-border px-5 py-3 font-display text-title-md text-text-primary">
                {a.area}
              </h2>
              {a.codes.map((code) => {
                const c = byCode.get(code);
                const state = c ? STATE[c.status] : undefined;
                return (
                  <div key={code} className="flex items-center gap-3 border-t border-border px-5 py-2.5 first:border-t-0">
                    <span className="min-w-[72px] font-mono text-body-sm text-text-primary">{code}</span>
                    <span className="flex-1 text-body-sm text-text-secondary">
                      {c ? (
                        <Link to={`/controls/${c.id}`} className="text-text-link">
                          {c.name}
                        </Link>
                      ) : (
                        "Not in your workspace"
                      )}
                    </span>
                    {state ? <StatusPill status={state.family} label={state.label} /> : null}
                  </div>
                );
              })}
            </section>
          ))}
        </div>
      )}
      <p className="mt-4 text-body-sm text-text-secondary">
        Three areas a SOC 1 auditor always tests are not in the library yet: direct changes to
        production data, job scheduling with failed job handling, and the accuracy of reports your
        controls rely on. Raise them with your audit firm.
      </p>
    </div>
  );
}
