"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

const productLinks = [
  { title: "Compliance management", description: "Frameworks, controls, evidence, and policy work.", href: "/#compliance", tag: "Controls · Evidence" },
  { title: "Security operations", description: "Assets, vulnerability findings, and remediation ownership.", href: "/#security", tag: "Assets · Vulnerabilities" },
  { title: "Risk and third parties", description: "Risk decisions and vendor engagement reviews.", href: "/#risk", tag: "Risk · Vendors" },
];

export function SiteNavigation({ signInUrl, trialUrl }: { signInUrl: string; trialUrl: string }) {
  const [open, setOpen] = useState<"platform" | "resources" | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open && !mobileOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setOpen(null); setMobileOpen(false); }
    };
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) { setOpen(null); setMobileOpen(false); }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => { document.removeEventListener("keydown", onKey); document.removeEventListener("pointerdown", onPointer); };
  }, [open, mobileOpen]);

  const close = () => { setOpen(null); setMobileOpen(false); };

  return <div className="navigation-root" ref={root}>
    <nav className="desktop-nav" aria-label="Main navigation">
      <button type="button" aria-expanded={open === "platform"} aria-controls="platform-menu" onClick={() => setOpen(open === "platform" ? null : "platform")}>Platform <span className="nav-chevron" aria-hidden="true" /></button>
      <Link href="/#approach" onClick={close}>Why Verity</Link>
      <Link href="/#trust" onClick={close}>Trust and control</Link>
      <button type="button" aria-expanded={open === "resources"} aria-controls="resources-menu" onClick={() => setOpen(open === "resources" ? null : "resources")}>Resources <span className="nav-chevron" aria-hidden="true" /></button>
    </nav>
    <div className="header-actions">
      <a className="sign-in-link" href={signInUrl}>Sign in</a>
      <Link className="button button-small button-outline" href="/#request-demo" onClick={close}>See a demo</Link>
      <a className="button button-small button-dark" href={trialUrl}>Start trial</a>
    </div>
    <button className="mobile-menu-button" type="button" aria-label={mobileOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileOpen} aria-controls="mobile-site-menu" onClick={() => { setMobileOpen(!mobileOpen); setOpen(null); }}><span /><span /><span /></button>
    <div id="platform-menu" className="mega-menu" hidden={open !== "platform"}>
      <div className="mega-intro"><span className="mega-label">VERITY PLATFORM</span><h2>Run your program from the work itself.</h2><p>Connected records make ownership, proof, and decisions easier to follow.</p><Link href="/#approach" onClick={close}>Explore the platform</Link></div>
      <div className="mega-grid">{productLinks.map((item) => <Link className="mega-card" href={item.href} key={item.href} onClick={close}><span className="mega-card-mark" aria-hidden="true"><i /><i /><i /></span><strong>{item.title}</strong><span>{item.description}</span><small>{item.tag}</small></Link>)}</div>
      <div className="mega-bottom"><span>Currently available: SOC 2 content library</span><span>Additional frameworks and business continuity are planned.</span></div>
    </div>
    <div id="resources-menu" className="mega-menu resource-menu" hidden={open !== "resources"}>
      <div><span className="mega-label">LEARN</span><h2>Find your way through Verity.</h2><p>Public documentation is built from the same guide used by workspace teams.</p></div>
      <div className="resource-links"><Link href="/docs/" onClick={close}>User guide<span>Set up a workspace and learn the core workflows.</span></Link><Link href="/docs/03-frameworks-and-controls/" onClick={close}>Controls and frameworks<span>Adopt controls and map requirements.</span></Link><Link href="/docs/04-evidence/" onClick={close}>Evidence reviews<span>Collect, link, and review proof.</span></Link><Link href="/docs/08-vendors/" onClick={close}>Vendor engagements<span>Follow assessments and decisions.</span></Link></div>
    </div>
    <nav id="mobile-site-menu" className="mobile-site-menu" aria-label="Mobile navigation" hidden={!mobileOpen}>
      <details><summary>Platform</summary><div>{productLinks.map((item) => <Link href={item.href} key={item.href} onClick={close}>{item.title}</Link>)}</div></details>
      <Link href="/#approach" onClick={close}>Why Verity</Link><Link href="/#trust" onClick={close}>Trust and control</Link>
      <details><summary>Resources</summary><div><Link href="/docs/" onClick={close}>User guide</Link><Link href="/docs/03-frameworks-and-controls/" onClick={close}>Controls and frameworks</Link><Link href="/docs/08-vendors/" onClick={close}>Vendor engagements</Link></div></details>
      <div className="mobile-menu-actions"><Link className="button button-outline" href="/#request-demo" onClick={close}>See a demo</Link><a className="button button-dark" href={trialUrl}>Start trial</a><a href={signInUrl}>Sign in</a></div>
    </nav>
  </div>;
}
