import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, RadioGroup, RadioGroupItem, TextField, useToast } from "@/components/ui";
import { engagementApi } from "@/lib/api/endpoints";
import { errorToast } from "@/lib/api/describe-error";
import type { Engagement } from "@/lib/api/types";

/**
 * Who audits, and the dates the plan is worked back from (guided onboarding EN-2, EN-3).
 *
 * One card for every framework. Only the fields this card owns are sent; the rest of the
 * engagement is echoed back unchanged, and the server leaves anything not sent as stored.
 * "Still deciding" is a real answer. The product never suggests a firm.
 */
export function AuditDetailsCard({
  engagement,
  frameworkName,
  certification,
  canManage,
}: {
  engagement: Engagement;
  frameworkName: string;
  /** A certification framework (ISO 27001): a certification body and a go live date. */
  certification: boolean;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [assessor, setAssessor] = useState<"chosen" | "undecided">("undecided");
  const [firm, setFirm] = useState("");
  const [accreditation, setAccreditation] = useState("");
  const [contact, setContact] = useState("");
  const [engagedOn, setEngagedOn] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [driver, setDriver] = useState("");
  const [asOf, setAsOf] = useState("");
  const [liveDate, setLiveDate] = useState("");

  useEffect(() => {
    setAssessor(engagement.assessor === "chosen" ? "chosen" : "undecided");
    setFirm(engagement.certification_body ?? "");
    setAccreditation(engagement.assessor_accreditation_body ?? "");
    setContact(engagement.assessor_contact ?? "");
    setEngagedOn(engagement.assessor_engaged_on ?? "");
    setTargetDate(engagement.target_date ?? "");
    setDriver(engagement.driver ?? "");
    setAsOf(engagement.as_of_date ?? "");
    setLiveDate(engagement.live_date ?? "");
  }, [engagement]);

  const save = useMutation({
    mutationFn: () =>
      engagementApi.put({
        name: engagement.name,
        framework_version_id: engagement.framework_version_id,
        audit_type: engagement.audit_type,
        categories_in_scope: engagement.categories_in_scope,
        window_start: engagement.window_start,
        window_end: engagement.window_end,
        assessor,
        certification_body: assessor === "chosen" ? firm.trim() || null : null,
        assessor_accreditation_body: certification ? accreditation.trim() || null : null,
        assessor_contact: contact.trim() || null,
        assessor_engaged_on: engagedOn || null,
        target_date: targetDate || null,
        driver: driver.trim() || null,
        ...(engagement.audit_type === "type_1" ? { as_of_date: asOf || null } : {}),
        ...(certification ? { live_date: liveDate || null } : {}),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["engagement"] }),
        queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
      ]);
      toast({ title: "Audit details saved", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "audit details"), tone: "danger" }),
  });

  const partyLabel = certification ? "Certification body" : "Audit firm";
  const chosenWithoutName = assessor === "chosen" && !firm.trim();

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="font-display text-title-md text-text-primary">Audit details</h2>
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <fieldset className="space-y-3" disabled={!canManage}>
          <legend className="mb-2 font-sans text-label-sm text-text-secondary">
            Who audits your {frameworkName}
          </legend>
          <RadioGroup
            value={assessor}
            onValueChange={(v) => setAssessor(v === "chosen" ? "chosen" : "undecided")}
            className="flex-row flex-wrap gap-x-5"
          >
            <RadioGroupItem value="chosen" label="We have chosen" />
            <RadioGroupItem value="undecided" label="Still deciding" />
          </RadioGroup>
          {assessor === "chosen" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <TextField
                label={partyLabel}
                value={firm}
                onChange={(e) => setFirm(e.target.value)}
                error={chosenWithoutName ? `Add the ${partyLabel.toLowerCase()}'s name.` : undefined}
              />
              {certification ? (
                <TextField
                  label="Accredited by"
                  optional
                  placeholder="For example UKAS or ANAB"
                  value={accreditation}
                  onChange={(e) => setAccreditation(e.target.value)}
                />
              ) : null}
              <TextField
                label="Contact"
                optional
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              />
              <TextField
                label={certification ? "Contract signed" : "Engagement letter signed"}
                optional
                type="date"
                value={engagedOn}
                onChange={(e) => setEngagedOn(e.target.value)}
              />
            </div>
          ) : null}
        </fieldset>
        <fieldset className="grid gap-3 sm:grid-cols-2" disabled={!canManage}>
          <legend className="mb-2 font-sans text-label-sm text-text-secondary">Dates</legend>
          <TextField
            label="Needed by"
            optional
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
          />
          <TextField
            label="Who asked for it"
            optional
            placeholder="A customer, a tender, a regulator"
            value={driver}
            onChange={(e) => setDriver(e.target.value)}
          />
          {engagement.audit_type === "type_1" ? (
            <TextField
              label="Report as of"
              optional
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
            />
          ) : null}
          {certification ? (
            <TextField
              label="Management system live from"
              optional
              type="date"
              value={liveDate}
              onChange={(e) => setLiveDate(e.target.value)}
            />
          ) : null}
        </fieldset>
      </div>
      {canManage ? (
        <div className="mt-5 flex items-center gap-3 border-t border-border pt-4">
          <Button loading={save.isPending} disabled={chosenWithoutName} onClick={() => save.mutate()}>
            Save audit details
          </Button>
          <p className="text-body-sm text-text-subtle">Your auditor sets the real timeline.</p>
        </div>
      ) : null}
    </div>
  );
}
