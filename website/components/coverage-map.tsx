"use client";

import { useState } from "react";

const views = [
  { key: "control", label: "Control coverage", nodes: ["SOC 2 requirement", "Access review control", "Q3 review evidence", "Identity provider", "Review decision"], note: "Start at the requirement, then inspect the control and reviewed evidence that support it." },
  { key: "security", label: "Security exposure", nodes: ["Asset inventory", "Customer portal", "Dependency finding", "Remediation task", "Verification"], note: "Start at an asset, then follow a finding through ownership and verification." },
  { key: "vendor", label: "Third-party review", nodes: ["Vendor engagement", "Questionnaire", "Finding", "Risk treatment", "Approval decision"], note: "Start at an engagement, then follow the assessment and the person who decides." },
];

export function CoverageMap() {
  const [selected, setSelected] = useState(0);
  const view = views[selected];
  return <div className="coverage-map">
    <div className="coverage-map-tabs" role="tablist" aria-label="Relationship example">{views.map((item, index) => <button key={item.key} type="button" role="tab" tabIndex={selected === index ? 0 : -1} aria-selected={selected === index} aria-controls="coverage-panel" id={`coverage-tab-${index}`} onClick={() => setSelected(index)} onKeyDown={(event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const next = (index + (event.key === "ArrowRight" ? 1 : -1) + views.length) % views.length;
      setSelected(next);
      document.getElementById(`coverage-tab-${next}`)?.focus();
    }}>{item.label}</button>)}</div>
    <div className="coverage-map-body" id="coverage-panel" role="tabpanel" aria-labelledby={`coverage-tab-${selected}`} key={view.key}>
      <div className="coverage-map-graph"><svg viewBox="0 0 720 370" fill="none" aria-hidden="true"><path d="M92 185H235L360 78 486 185 624 185M360 78V300L486 185M235 185 360 300 624 185" stroke="#b8d2df" strokeWidth="2" strokeDasharray="5 7" /><path className="coverage-trace" d="M92 185H235L360 78 486 185 624 185" stroke="#0783bb" strokeWidth="3" /></svg>{view.nodes.map((node, index) => <div key={node} className={`coverage-node coverage-node-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{node}</strong></div>)}</div>
      <div className="coverage-map-detail"><span className="v2-eyebrow">EXAMPLE RELATIONSHIP</span><h3>{view.label}</h3><p>{view.note}</p><div><strong>Why it matters</strong><p>People can move from a status to the underlying record, owner, and history.</p></div></div>
    </div>
  </div>;
}
