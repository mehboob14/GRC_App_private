"use client";

import Link from "next/link";
import { useState } from "react";

export type PlatformArea = "compliance" | "risk" | "vendors" | "audits" | "assets" | "policies";

const areas: { key: PlatformArea; title: string; lines: string[]; detail: string; href: string; x: number; y: number }[] = [
  { key: "compliance", title: "Compliance", lines: ["Requirements", "Controls", "Evidence"], detail: "Map a requirement to an owned control, then review the evidence that supports it.", href: "/docs/03-frameworks-and-controls/", x: 350, y: 62 },
  { key: "risk", title: "Risk", lines: ["Identify", "Treat", "Monitor"], detail: "Assess a risk, assign treatment, and keep the decision with its record.", href: "/docs/07-risks/", x: 578, y: 157 },
  { key: "vendors", title: "Vendors", lines: ["Intake", "Assess", "Monitor"], detail: "Carry a third party from intake through assessment, approval, and monitoring.", href: "/docs/08-vendors/", x: 578, y: 375 },
  { key: "audits", title: "Audits", lines: ["Review", "Evidence", "Findings"], detail: "Follow control reviews, evidence decisions, and findings through the record history.", href: "/docs/04-evidence/", x: 350, y: 472 },
  { key: "assets", title: "Assets", lines: ["Inventory", "Vulnerabilities", "Ownership"], detail: "Connect an asset to its owner, affected findings, and remediation work.", href: "/docs/09-assets/", x: 122, y: 375 },
  { key: "policies", title: "Policies", lines: ["Draft", "Approve", "Publish"], detail: "Manage policy versions, approvals, acknowledgements, and control mappings.", href: "/docs/05-policies-and-documents/", x: 122, y: 157 },
];

export function ModuleIcon({ area }: { area: PlatformArea }) {
  const common = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true as const };
  if (area === "compliance") return <svg {...common}><path d="M12 2.5 20 6v6c0 5-3.2 8.2-8 9.5C7.2 20.2 4 17 4 12V6l8-3.5Z"/><path d="m8.5 12 2.4 2.4 4.8-5"/></svg>;
  if (area === "risk") return <svg {...common}><path d="M10.3 4.2 2.7 17.5a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/><path d="M12 9v5m0 3h.01"/></svg>;
  if (area === "vendors") return <svg {...common}><circle cx="9" cy="8" r="3"/><path d="M3.5 19v-2a5.5 5.5 0 0 1 11 0v2H3.5Zm12-13.5a3 3 0 0 1 0 5.8M17 13a5 5 0 0 1 3.5 4.8V19H18"/></svg>;
  if (area === "audits") return <svg {...common}><path d="M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M14 3v5h4M9 12h6m-6 4h6"/></svg>;
  if (area === "assets") return <svg {...common}><rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M6.5 7.5h.01M6.5 16.5h.01M10 7.5h7M10 16.5h7"/></svg>;
  return <svg {...common}><path d="M7 3h8l4 4v13a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M15 3v5h4M9 12h6m-6 4h5"/></svg>;
}

export function HeroGraph() {
  const [selected, setSelected] = useState<PlatformArea>("compliance");
  const active = areas.find((area) => area.key === selected) ?? areas[0];

  return <div className="hero-graph" aria-label="Explore the connected Verity platform">
    <div className="hero-graph-map">
      <svg className="graph-links" viewBox="0 0 700 535" preserveAspectRatio="none" aria-hidden="true">
        <circle cx="350" cy="268" r="173" className="graph-orbit" />
        {areas.map((area) => <line key={area.key} className={selected === area.key ? "graph-link selected" : "graph-link"} x1="350" y1="268" x2={area.x} y2={area.y} />)}
        <circle className="graph-pulse" r="5"><animateMotion key={selected} dur="2.8s" repeatCount="indefinite" path={`M ${active.x} ${active.y} L 350 268`} /></circle>
      </svg>
      <div className="graph-core"><span className="graph-core-mark" aria-hidden="true"><span /></span><strong>Your GRC<br/>platform</strong></div>
      {areas.map((area) => <button type="button" key={area.key} className={`graph-area graph-area-${area.key}${selected === area.key ? " selected" : ""}`} style={{ left: `${area.x / 7}%`, top: `${area.y / 5.35}%` }} aria-pressed={selected === area.key} onClick={() => setSelected(area.key)}><span className="graph-area-icon"><ModuleIcon area={area.key} /></span><span className="graph-area-copy"><strong>{area.title}</strong><small>{area.lines.map((line) => <span key={line}>{line}</span>)}</small></span></button>)}
    </div>
    <div className="hero-graph-detail" aria-live="polite"><span className={`graph-detail-icon graph-area-${active.key}`}><ModuleIcon area={active.key} /></span><p><strong>{active.title}</strong>{active.detail}</p><Link href={active.href}>Read the guide<span className="graph-sr-only"> for {active.title.toLowerCase()}</span></Link></div>
  </div>;
}
