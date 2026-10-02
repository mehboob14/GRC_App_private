import type { Metadata } from "next";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { getSiteConfig } from "@/lib/site-config";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "@fontsource/sora/latin-600.css";
import "@fontsource/sora/latin-700.css";
import "@fontsource/sora/latin-800.css";
import "./globals.css";
import "./marketing.css";
import "./landing.css";
import "./v2.css";
import "./hero-platform.css";

const { siteUrl } = getSiteConfig();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Verity | Governance, risk, and compliance", template: "%s | Verity" },
  description: "Manage controls, evidence, policies, assets, vulnerabilities, and third-party risk in one GRC workspace. Start with the SOC 2 library.",
  openGraph: {
    type: "website",
    title: "Verity | Governance, risk, and compliance",
    description: "Manage controls, evidence, policies, assets, vulnerabilities, and third-party risk in one GRC workspace. Start with the SOC 2 library.",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "Verity — Governance, risk, and compliance in one workspace" }],
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "try{if(sessionStorage.getItem('verity-landing-intro-seen')==='1')document.documentElement.dataset.verityIntroSeen='1'}catch{}" }} />
      </head>
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
