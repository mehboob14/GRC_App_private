import Link from "next/link";
import { getSiteConfig } from "@/lib/site-config";
import { footerColumns } from "@/content/navigation";
import { Brand } from "./brand";
import { DemoButton } from "./demo-button";

export function SiteFooter() {
  const { trialUrl, signInUrl, privacyUrl, termsUrl } = getSiteConfig();
  return (
    <footer className="relative overflow-hidden border-t border-line bg-subtle">
      <div className="frame grid grid-cols-1 gap-12 pb-10 pt-16 lg:grid-cols-[1.25fr_3fr] lg:gap-16">
        <div className="max-w-sm">
          <Brand />
          <p className="mt-5 text-[15px] leading-relaxed text-dim">The compliance and security platform for organisations that have to prove it: frameworks, evidence, policies, risk, vendors, assets and vulnerabilities in one place.</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <DemoButton variant="outline" className="btn-sm" source="footer">See a demo</DemoButton>
            <a href={trialUrl} className="btn btn-dark btn-sm">Start trial</a>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
          {footerColumns.map((column) => (
            <nav key={column.title} aria-label={`Footer: ${column.title}`}>
              <h2 className="eyebrow mb-4">{column.title}</h2>
              <ul className="space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.href}><Link href={link.href} className="text-[14px] text-body transition-colors hover:text-ink">{link.title}</Link></li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
      </div>
      <div className="frame flex flex-col gap-3 border-t border-line py-6 text-[13px] text-dim sm:flex-row sm:items-center sm:justify-between">
        <p>© {new Date().getFullYear()} Verity. Product views on this site use demonstration data.</p>
        <ul className="flex flex-wrap gap-x-5 gap-y-2">
          <li><a href={signInUrl} className="hover:text-ink">Sign in</a></li>
          <li><Link href="/security/" className="hover:text-ink">Security</Link></li>
          {privacyUrl && <li><a href={privacyUrl} className="hover:text-ink">Privacy</a></li>}
          {termsUrl && <li><a href={termsUrl} className="hover:text-ink">Terms</a></li>}
        </ul>
      </div>
      <div aria-hidden="true" className="footer-wordmark pointer-events-none select-none overflow-hidden" />
    </footer>
  );
}
