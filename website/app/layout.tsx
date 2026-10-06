import type { Metadata, Viewport } from "next";
import { getSiteConfig } from "@/lib/site-config";
import { RevealObserver } from "@/components/site/reveal-observer";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "@fontsource-variable/source-serif-4/opsz.css";
import "@fontsource-variable/jetbrains-mono/wght.css";
import "./globals.css";
import "./motion.css";

const { siteUrl, locale } = getSiteConfig();

const description = "Verity is the compliance and security platform for organisations that have to prove it. Map controls across frameworks, keep evidence fresh, and manage policies, risks, vendors, assets and vulnerabilities in one place.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Verity | Compliance and security, end to end", template: "%s | Verity" },
  description,
  applicationName: "Verity",
  openGraph: {
    type: "website",
    siteName: "Verity",
    title: "Verity | Compliance and security, end to end",
    description,
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "Verity: compliance without the scramble" }],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = { themeColor: "#ffffff", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang={locale.lang} dir={locale.dir} suppressHydrationWarning>
      <head>
        {/* Before paint: mark scripting (reveal styles apply only then) and restore the docs theme.
            The docs are light unless the visitor has switched them to dark themselves: the
            operating system's preference is deliberately not read, so the first visit is white. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.documentElement.classList.add('js');try{document.documentElement.dataset.docsTheme=localStorage.getItem('verity-docs-theme')==='dark'?'dark':'light'}catch(e){document.documentElement.dataset.docsTheme='light'}",
          }}
        />
      </head>
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        {children}
        <RevealObserver />
      </body>
    </html>
  );
}
