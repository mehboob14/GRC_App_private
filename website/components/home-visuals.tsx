export function ComplianceVisual() {
  return <div className="product-visual compliance-visual" role="img" aria-label="Illustrative control detail linking a SOC 2 requirement, owner, evidence, and review history">
    <div className="visual-bar"><span className="visual-brand">verity<span>.</span></span><span>Compliance / Controls</span><span className="visual-example">Example workspace</span></div>
    <div className="visual-body">
      <div className="visual-kicker">CONTROL RECORD <span className="status-pill status-active">In progress</span></div>
      <h3>Logical access review</h3><p>Confirm that access is appropriate for each role and approved by an accountable owner.</p>
      <div className="control-mapping"><div><small>FRAMEWORK</small><strong>SOC 2</strong><span>CC6.1 · Logical access</span></div><div><small>OWNER</small><strong>Security team</strong><span>Quarterly review</span></div></div>
      <div className="visual-list-heading">Linked work <span>3 records</span></div>
      <div className="visual-record"><span className="record-icon">01</span><div><strong>Q3 access review</strong><small>Evidence · Reviewed</small></div><span className="record-indicator ready">Reviewed</span></div>
      <div className="visual-record"><span className="record-icon">02</span><div><strong>Identity provider</strong><small>Asset · In scope</small></div><span className="record-indicator">Tracked</span></div>
      <div className="visual-record"><span className="record-icon">03</span><div><strong>Privilege drift</strong><small>Risk · Treatment open</small></div><span className="record-indicator attention">Open</span></div>
      <div className="visual-timeline"><i /><span>Review decision recorded with owner and date</span></div>
    </div>
  </div>;
}

const findings = [
  { asset: "Customer portal", finding: "Outdated dependency", severity: "High", owner: "Application team", status: "In progress" },
  { asset: "Identity provider", finding: "Privileged role review", severity: "Medium", owner: "Security team", status: "Assigned" },
  { asset: "Build service", finding: "Patch verification", severity: "Low", owner: "Platform team", status: "Review" },
];

export function SecurityVisual() {
  return <div className="product-visual security-visual" role="img" aria-label="Illustrative vulnerability register with linked assets, severity, owners, and remediation states">
    <div className="visual-bar"><span className="visual-brand">verity<span>.</span></span><span>Security / Vulnerabilities</span><span className="visual-example">Example workspace</span></div>
    <div className="visual-body"><div className="visual-kicker">VULNERABILITY REGISTER</div><h3>Findings with an owner</h3><p>See the affected asset and the next remediation step in one view.</p>
      <div className="severity-summary"><div><span>High</span><strong>2</strong><i className="severity-high" /></div><div><span>Medium</span><strong>5</strong><i className="severity-medium" /></div><div><span>Low</span><strong>9</strong><i className="severity-low" /></div></div>
      <div className="finding-table"><div className="finding-head"><span>Asset / finding</span><span>Severity</span><span>Owner</span><span>Status</span></div>{findings.map((row) => <div className="finding-row" key={row.asset}><span><strong>{row.asset}</strong><small>{row.finding}</small></span><span><b className={`severity-label ${row.severity.toLowerCase()}`}>{row.severity}</b></span><span>{row.owner}</span><span>{row.status}</span></div>)}</div>
    </div>
  </div>;
}

export function VendorVisual() {
  return <div className="product-visual vendor-visual" role="img" aria-label="Illustrative vendor engagement showing assessment, findings, decision, and retained review history">
    <div className="visual-bar"><span className="visual-brand">verity<span>.</span></span><span>Risk / Vendors</span><span className="visual-example">Example workspace</span></div>
    <div className="visual-body"><div className="visual-kicker">VENDOR ENGAGEMENT <span className="status-pill status-review">Review in progress</span></div><h3>Cloud service review</h3><p>Bring the assessment, issues, and decision into the same engagement.</p>
      <div className="vendor-stages"><div className="completed"><i>1</i><span>Intake</span></div><div className="completed"><i>2</i><span>Assessment</span></div><div className="current"><i>3</i><span>Decision</span></div><div><i>4</i><span>Monitoring</span></div></div>
      <div className="vendor-panels"><div><small>ASSESSMENT</small><strong>Security questionnaire</strong><p>Responses and supporting documents stay with the engagement.</p><span className="record-indicator ready">Reviewed</span></div><div><small>DECISION</small><strong>Approval pending</strong><p>The decision maker can review findings and record the reason.</p><span className="record-indicator attention">Needs owner</span></div></div>
      <div className="vendor-history"><span>Activity history</span><strong>Assessment reviewed</strong><small>Recorded by the risk team</small></div>
    </div>
  </div>;
}
