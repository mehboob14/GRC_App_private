import Link from "next/link";
import { Brand } from "./brand";
import { getSiteConfig } from "@/lib/site-config";

export function SiteFooter() {
  const config = getSiteConfig();
  return (
    <footer className="site-footer">
      <div className="site-container footer-grid">
        <div className="footer-intro">
          <Brand />
          <p>Governance, risk, and compliance work in one workspace.</p>
        </div>
        <nav aria-label="Explore Verity"><h2>Explore</h2><Link href="/#platform">How it works</Link><Link href="/#coverage">What it covers</Link><Link href="/#trust">Security and history</Link><Link href="/#request-demo">Book a demo</Link></nav>
        <nav aria-label="Learn about Verity"><h2>Learn</h2><Link href="/docs/">User guide</Link><Link href="/docs/03-frameworks-and-controls/">Controls</Link><Link href="/docs/09-assets/">Assets</Link><Link href="/docs/08-vendors/">Third-party risk</Link></nav>
        <nav aria-label="Access Verity"><h2>Access</h2><a href={config.trialUrl}>Start trial</a><a href={config.signInUrl}>Sign in</a></nav>
      </div>
      <div className="site-container footer-bottom"><span>© {new Date().getFullYear()} Verity</span><span>Governance, risk, and compliance</span></div>
      <div className="footer-wordmark" aria-hidden="true">VERITY</div>
    </footer>
  );
}
