"use client";

import { useState } from "react";
import Link from "next/link";
import { ProductScene, type Scene } from "./product-scene";

const areas: { scene: Scene; title: string; summary: string; href: string }[] = [
  { scene: "assets", title: "Assets", summary: "Know what you run, how critical it is, and who owns it.", href: "/docs/09-assets/" },
  { scene: "vulnerabilities", title: "Vulnerabilities", summary: "Work findings in the context of the assets they affect.", href: "/docs/10-vulnerabilities/" },
  { scene: "vendors", title: "Third-party risk", summary: "Follow each engagement from intake to monitoring.", href: "/docs/08-vendors/" },
];

function AreaIcon({ scene }: { scene: Scene }) {
  return <svg className="area-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {scene === "assets" && <><rect x="8" y="8" width="32" height="32" rx="6" /><rect x="15" y="15" width="18" height="12" rx="2" /><path d="M18 34h12M24 27v7" /></>}
    {scene === "vulnerabilities" && <><path d="M24 6 40 12v12c0 10-6.5 16-16 20C14.5 40 8 34 8 24V12L24 6Z" /><path d="M24 15v12m0 6h.01" /></>}
    {scene === "vendors" && <><rect x="6" y="16" width="16" height="25" rx="2" /><rect x="27" y="8" width="15" height="33" rx="2" /><path d="M22 23h5M12 22h4m-4 7h4m17-13h4m-4 7h4m-4 7h4M6 41h36" /></>}
  </svg>;
}

export function OperationalPreview() {
  const [active, setActive] = useState(0);
  const current = areas[active];

  return <section id="coverage" className="operations-section" aria-labelledby="coverage-title">
    <div className="site-container">
      <div className="operations-heading reveal-block"><span className="story-eyebrow">Operational coverage</span><h2 id="coverage-title">Know the estate. Work the exposure.</h2><p>Compliance needs more than a control list. Verity gives the assets, findings, and third parties behind your risk their own records and owners.</p></div>
      <div className="operations-layout">
        <div className="operations-choices" role="group" aria-label="Explore operational workflows">
          {areas.map((area, index) => <button type="button" key={area.scene} className={`operations-choice ${active === index ? "active" : ""}`} aria-pressed={active === index} onClick={() => setActive(index)}>
            <span className="area-icon-wrap"><AreaIcon scene={area.scene} /></span><span className="operations-choice-copy"><strong>{area.title}</strong><span>{area.summary}</span></span><span className="choice-indicator" aria-hidden="true" />
          </button>)}
        </div>
        <div className="operations-visual"><div key={current.scene} className="scene-enter"><ProductScene scene={current.scene} compact /></div><div className="operations-visual-foot"><span>Example workspace view</span><Link className="plain-link" href={current.href}>Explore {current.title.toLowerCase()} in the guide</Link></div></div>
      </div>
      <div className="operations-secondary reveal-block"><div><strong>Risk and treatment</strong><p>Assign an owner, score the exposure, and record the decision.</p><Link href="/docs/07-risks/">Read about risk</Link></div><div><strong>Policies and tasks</strong><p>Keep approvals, acknowledgements, and follow-up work accountable.</p><Link href="/docs/05-policies-and-documents/">Read about policies</Link></div><div><strong>Frameworks</strong><p>Adopt controls and map them to requirements. The current library is SOC 2.</p><Link href="/docs/03-frameworks-and-controls/">Read about controls</Link></div></div>
      <p className="framework-note">ISO 27001 and other framework libraries, along with business continuity workflows, are planned. VantageMDM is separate software and is not part of the Verity workspace.</p>
    </div>
  </section>;
}
