type Scene = "controls" | "evidence" | "risk" | "assets" | "vulnerabilities" | "vendors";

const sceneNames: Record<Scene, string> = {
  controls: "Controls",
  evidence: "Evidence",
  risk: "Risks",
  assets: "Assets",
  vulnerabilities: "Vulnerabilities",
  vendors: "Vendors",
};

function SceneSidebar({ scene }: { scene: Scene }) {
  return (
    <div className="sample-sidebar" aria-hidden="true">
      <div className="sample-sidebar-brand"><span className="sample-brand-mark">✓</span><strong>verity<span>.</span></strong></div>
      <div className="sample-workspace-name">Example workspace</div>
      <div className="sample-nav-label">WORKSPACE</div>
      <div className="sample-nav-item">Overview</div>
      <div className="sample-nav-item">Tasks</div>
      <div className="sample-nav-label">COMPLIANCE</div>
      <div className={`sample-nav-item ${scene === "controls" ? "selected" : ""}`}>Controls</div>
      <div className={`sample-nav-item ${scene === "evidence" ? "selected" : ""}`}>Evidence</div>
      <div className="sample-nav-item">Policies</div>
      <div className="sample-nav-label">RISK</div>
      <div className={`sample-nav-item ${scene === "risk" ? "selected" : ""}`}>Risks</div>
      <div className={`sample-nav-item ${scene === "vendors" ? "selected" : ""}`}>Vendors</div>
      <div className={`sample-nav-item ${scene === "assets" ? "selected" : ""}`}>Assets</div>
      <div className={`sample-nav-item ${scene === "vulnerabilities" ? "selected" : ""}`}>Vulnerabilities</div>
    </div>
  );
}

function SceneHeader({ scene }: { scene: Scene }) {
  return (
    <div className="sample-topbar" aria-hidden="true">
      <span>Workspace <span className="sample-crumb">/</span> {sceneNames[scene]}</span>
      <span className="sample-topbar-right"><span className="sample-topbar-dot" /> Example workspace</span>
    </div>
  );
}

function ControlsScene() {
  return (
    <div className="sample-content" aria-hidden="true">
      <div className="sample-title-row">
        <div><span className="sample-overline">CONTROL RECORD</span><h3>Access reviews</h3><p>Review who can access production systems each quarter.</p></div>
        <span className="sample-status amber">In progress</span>
      </div>
      <div className="sample-subnav"><span className="active">Overview</span><span>Evidence</span><span>Requirements</span><span>History</span></div>
      <div className="sample-detail-grid">
        <div className="sample-paper">
          <span className="sample-paper-label">CONTROL STATEMENT</span>
          <p>Privileged access is reviewed at least quarterly. Changes are recorded and exceptions are followed up.</p>
          <div className="sample-divider" />
          <div className="sample-fields"><span>Owner<strong>Security team</strong></span><span>Framework<strong>SOC 2 · CC6.3</strong></span></div>
        </div>
        <div className="sample-paper sample-side-paper">
          <span className="sample-paper-label">WORK TO COMPLETE</span>
          <div className="sample-check-row"><span className="sample-check done">✓</span><span>Owner assigned</span></div>
          <div className="sample-check-row"><span className="sample-check done">✓</span><span>Requirement mapped</span></div>
          <div className="sample-check-row"><span className="sample-check" /><span>Evidence review pending</span></div>
        </div>
      </div>
      <div className="sample-linked"><span className="sample-paper-label">LINKED EVIDENCE</span><strong>Quarterly access review</strong><span className="sample-status violet">In review</span></div>
    </div>
  );
}

function EvidenceScene() {
  return (
    <div className="sample-content" aria-hidden="true">
      <div className="sample-title-row">
        <div><span className="sample-overline">EVIDENCE RECORD</span><h3>Quarterly access review</h3><p>Proof stays linked to the control it supports.</p></div>
        <span className="sample-status violet">In review</span>
      </div>
      <div className="sample-subnav"><span className="active">Overview</span><span>Controls</span><span>Activity</span></div>
      <div className="sample-detail-grid evidence-grid">
        <div className="sample-paper sample-file-paper">
          <div className="sample-file-icon"><span /><span /><span /></div>
          <strong>access-review-q3.pdf</strong>
          <small>Uploaded file · Example record</small>
        </div>
        <div className="sample-paper sample-side-paper">
          <span className="sample-paper-label">REVIEW</span>
          <div className="sample-review-line"><span>Status</span><strong>Pending decision</strong></div>
          <div className="sample-review-line"><span>Linked control</span><strong>Access reviews</strong></div>
          <div className="sample-review-line"><span>Valid until</span><strong>Next review cycle</strong></div>
          <div className="sample-review-note">The reviewer can approve or return the record with a reason.</div>
        </div>
      </div>
      <div className="sample-linked"><span className="sample-paper-label">CONTROL LINK</span><strong>Access reviews</strong><span className="sample-status blue">SOC 2 · CC6.3</span></div>
    </div>
  );
}

function RiskScene() {
  return (
    <div className="sample-content" aria-hidden="true">
      <div className="sample-title-row">
        <div><span className="sample-overline">RISK REGISTER</span><h3>Risks that need a decision</h3><p>Scope, ownership, and treatment remain visible.</p></div>
        <span className="sample-status blue">Register view</span>
      </div>
      <div className="sample-risk-table">
        <div className="sample-risk-head"><span>Risk</span><span>Severity</span><span>Owner</span><span>Status</span></div>
        <div className="sample-risk-row"><strong>Third-party access to systems<small>Vendor risk</small></strong><span className="sample-severity high">High</span><span>Security team</span><span className="sample-state">In treatment</span></div>
        <div className="sample-risk-row"><strong>Missed access review<small>Operational risk</small></strong><span className="sample-severity medium">Medium</span><span>IT team</span><span className="sample-state">Open</span></div>
        <div className="sample-risk-row"><strong>Unpatched critical asset<small>Technology risk</small></strong><span className="sample-severity high">High</span><span>Engineering</span><span className="sample-state">In treatment</span></div>
      </div>
      <div className="sample-risk-bottom"><span className="sample-paper-label">TREATMENT RECORD</span><strong>Owner, due date, linked controls, and decision history</strong></div>
    </div>
  );
}

function AssetsScene() {
  return <div className="sample-content" aria-hidden="true">
    <div className="sample-title-row"><div><span className="sample-overline">ASSET RECORD</span><h3>Payments API gateway</h3><p>An application with a named owner and business context.</p></div><span className="sample-status amber">High criticality</span></div>
    <div className="sample-subnav"><span className="active">Overview</span><span>Dependencies</span><span>Vulnerabilities</span><span>History</span></div>
    <div className="sample-detail-grid">
      <div className="sample-paper"><span className="sample-paper-label">BUSINESS CONTEXT</span><p>Processes customer payments and supports the checkout service. Affected findings and related risks can be reviewed from this record.</p><div className="sample-divider" /><div className="sample-fields"><span>Type<strong>Application</strong></span><span>Owner<strong>Platform engineering</strong></span></div></div>
      <div className="sample-paper sample-side-paper"><span className="sample-paper-label">INVENTORY HEALTH</span><div className="sample-review-line"><span>Criticality</span><strong>High</strong></div><div className="sample-review-line"><span>Data classification</span><strong>Restricted</strong></div><div className="sample-review-line"><span>Review</span><strong>Due this quarter</strong></div></div>
    </div>
    <div className="sample-linked"><span className="sample-paper-label">RELATED WORK</span><strong>Vulnerability findings on this asset</strong><span className="sample-status blue">Review findings</span></div>
  </div>;
}

function VulnerabilitiesScene() {
  return <div className="sample-content" aria-hidden="true">
    <div className="sample-title-row"><div><span className="sample-overline">VULNERABILITY REGISTER</span><h3>Findings on your assets</h3><p>Prioritize by weakness and the asset it affects.</p></div><span className="sample-status blue">Register view</span></div>
    <div className="sample-risk-table"><div className="sample-risk-head"><span>Finding</span><span>Priority</span><span>Asset</span><span>Status</span></div>
      <div className="sample-risk-row"><strong>Exposed administration port<small>Network finding</small></strong><span className="sample-severity high">High</span><span>Payments gateway</span><span className="sample-state">In progress</span></div>
      <div className="sample-risk-row"><strong>Outdated dependency<small>Application finding</small></strong><span className="sample-severity medium">Medium</span><span>Customer portal</span><span className="sample-state">New</span></div>
      <div className="sample-risk-row"><strong>Missing security update<small>Host finding</small></strong><span className="sample-severity high">High</span><span>Production host</span><span className="sample-state">Pending retest</span></div>
    </div><div className="sample-risk-bottom"><span className="sample-paper-label">EACH FINDING</span><strong>Asset, owner, due date, treatment, and verification history</strong></div>
  </div>;
}

function VendorsScene() {
  return <div className="sample-content" aria-hidden="true">
    <div className="sample-title-row"><div><span className="sample-overline">VENDOR ENGAGEMENT</span><h3>Cloud hosting service</h3><p>One service relationship, assessed on its own terms.</p></div><span className="sample-status violet">Monitoring</span></div>
    <div className="sample-subnav"><span className="active">Overview</span><span>Assessment</span><span>Findings</span><span>Documents</span></div>
    <div className="sample-detail-grid"><div className="sample-paper"><span className="sample-paper-label">ENGAGEMENT</span><p>Hosting for production applications. The intake decision, diligence, questionnaire, findings, and approval stay with this engagement.</p><div className="sample-divider" /><div className="sample-fields"><span>Owner<strong>IT operations</strong></span><span>Tier<strong>High</strong></span></div></div>
      <div className="sample-paper sample-side-paper"><span className="sample-paper-label">NEXT ATTENTION</span><div className="sample-review-line"><span>Stage</span><strong>Monitoring</strong></div><div className="sample-review-line"><span>Finding</span><strong>Access review due</strong></div><div className="sample-review-line"><span>Reassessment</span><strong>Scheduled</strong></div></div></div>
    <div className="sample-linked"><span className="sample-paper-label">DECISION RECORD</span><strong>Approval and follow-up remain visible</strong><span className="sample-status blue">Review history</span></div>
  </div>;
}

export function ProductScene({ scene, compact = false }: { scene: Scene; compact?: boolean }) {
  const description = {
    controls: "Illustrative Verity control record showing an owner, SOC 2 requirement, linked evidence, and work status",
    evidence: "Illustrative Verity evidence record showing its control link and pending human review",
    risk: "Illustrative Verity risk register showing severity, owner, and treatment status",
    assets: "Illustrative Verity asset record showing business context, owner, criticality, and related work",
    vulnerabilities: "Illustrative Verity vulnerability register showing findings, priorities, affected assets, and statuses",
    vendors: "Illustrative Verity vendor engagement showing lifecycle stage, owner, diligence, and follow-up",
  }[scene];

  return (
    <div className={`sample-window ${compact ? "sample-window-compact" : ""}`} role="img" aria-label={description}>
      <SceneSidebar scene={scene} />
      <div className="sample-main">
        <SceneHeader scene={scene} />
        {scene === "controls" && <ControlsScene />}
        {scene === "evidence" && <EvidenceScene />}
        {scene === "risk" && <RiskScene />}
        {scene === "assets" && <AssetsScene />}
        {scene === "vulnerabilities" && <VulnerabilitiesScene />}
        {scene === "vendors" && <VendorsScene />}
      </div>
    </div>
  );
}

export type { Scene };
