import { Badge, Icon, StatusPill } from "@/components/ui";
import type { VendorDetail } from "../types";
import { daysUntil, fmtCountdown, fmtDate, TIER_META } from "../tokens";
import { NotConnected, Panel } from "./panel";
import { SignalsPanel } from "./signals-panel";

/**
 * Continuous monitoring, and an honest account of how much of it is running.
 *
 * Two of these are real: the reassessment clock, which the tier drives, and
 * signals, which people record by hand until the feeds land. The other two need
 * a data source nobody has connected, and each says so in its own words rather
 * than rendering an empty table: an empty table is a claim, and "we looked and
 * there is nothing" about a vendor's breach history is a dangerous thing to say
 * by accident.
 */
export function MonitoringPanel({
  vendor,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const due = daysUntil(vendor.next_reassessment_on);
  const overdue = due !== null && due < 0;
  const soon = due !== null && due >= 0 && due <= 30;

  return (
    <div className="space-y-4">
      <Panel
        title="Reassessment clock"
        description="By tier: critical 6 months, low 3 years."
      >
        {vendor.next_reassessment_on ? (
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill
              status={overdue ? "danger" : soon ? "warning" : "success"}
              label={
                overdue
                  ? `Overdue ${fmtCountdown(due)}`
                  : soon
                    ? `Due ${fmtCountdown(due)}`
                    : `Due ${fmtCountdown(due)}`
              }
            />
            <span className="tabular text-body-sm text-text-secondary">
              {fmtDate(vendor.next_reassessment_on)}
            </span>
            {vendor.tier ? (
              <Badge variant="neutral">
                {TIER_META[vendor.tier]?.label ?? vendor.tier} cadence
              </Badge>
            ) : null}
          </div>
        ) : (
          <p className="text-body-sm text-text-subtle">
            No date until the engagement is tiered.
          </p>
        )}
      </Panel>

      <SignalsPanel vendor={vendor} canManage={canManage} onApply={onApply} />

      <Panel title="Security scorecard">
        <NotConnected
          what="No scorecard provider connected"
          why="The residual grade uses questionnaire answers and recorded signals only."
        />
      </Panel>

      <Panel title="Shadow IT" description="Apps in use that skipped intake.">
        <NotConnected
          what="No discovery source connected"
          why="Connect an identity provider or CASB to discover apps."
        />
        <p className="mt-3 flex items-start gap-1.5 text-caption text-text-subtle">
          <Icon name="info" className="mt-px size-3.5 shrink-0" />
          Anyone with read access can raise intake requests from the register.
        </p>
      </Panel>
    </div>
  );
}
