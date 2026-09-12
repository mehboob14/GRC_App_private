import { Badge, Icon, StatusPill } from "@/components/ui";
import type { VendorDetail } from "../types";
import { daysUntil, fmtCountdown, fmtDate, TIER_META } from "../tokens";
import { NotConnected, Panel } from "./panel";

/**
 * Continuous monitoring, and an honest account of how much of it is running.
 *
 * Three of the four things this tab would show need a data source nobody has
 * connected: breach and news signals, an external security scorecard, and the
 * discovered-app feed. Each says so in its own words rather than rendering an
 * empty table, because an empty table is a claim — it reads as "we looked and
 * there is nothing", which about a vendor's breach history is a dangerous thing
 * to say by accident.
 *
 * The fourth is real: the reassessment clock is derived from the tier and runs
 * whether or not anything is connected.
 */
export function MonitoringPanel({ vendor }: { vendor: VendorDetail }) {
  const due = daysUntil(vendor.next_reassessment_on);
  const overdue = due !== null && due < 0;
  const soon = due !== null && due >= 0 && due <= 30;

  return (
    <div className="space-y-4">
      <Panel
        title="Reassessment clock"
        description="Derived from the tier. Critical vendors come back every six months, low ones every three years."
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
            No date yet. The clock starts when the engagement is tiered.
          </p>
        )}
      </Panel>

      <Panel
        title="Signals"
        description="Breach disclosures, outage notices and news that should reopen a review."
      >
        <NotConnected
          what="No data source connected"
          why="Signals arrive from a breach-intelligence feed. Nothing is connected, so nothing has been checked — this is not a clean bill of health."
        />
      </Panel>

      <Panel
        title="Security scorecard"
        description="An outside-in rating of the vendor's public security posture."
      >
        <NotConnected
          what="No scorecard provider connected"
          why="A scorecard is bought, not computed. Until one is connected, this vendor's residual grade is based only on what they told us in the questionnaire."
        />
      </Panel>

      <Panel
        title="Shadow IT"
        description="Vendors discovered in use that nobody put through intake."
      >
        <NotConnected
          what="No discovery source connected"
          why="Discovered apps come from an identity provider or a CASB. Without one, the register shows only what people remembered to register."
        />
        <p className="mt-3 flex items-start gap-1.5 text-caption text-text-subtle">
          <Icon name="info" className="mt-px size-3.5 shrink-0" />
          Anyone with read access can raise an intake request from the register, which is the manual
          version of the same thing.
        </p>
      </Panel>
    </div>
  );
}
