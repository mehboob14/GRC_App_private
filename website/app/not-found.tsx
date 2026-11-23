import Link from "next/link";
import { getSiteConfig } from "@/lib/site-config";
import { DemoProvider } from "@/components/site/demo-provider";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { Icon } from "@/components/ui/icon";

export default function NotFound() {
  const { demoEndpoint } = getSiteConfig();
  return (
    <DemoProvider endpoint={demoEndpoint}>
      <SiteHeader />
      <main id="main-content" className="bg-gradient-to-b from-[#eef2f6] to-white">
        <div className="frame flex min-h-[60vh] flex-col items-start justify-center py-24">
          <p className="eyebrow">404 · Not found</p>
          <h1 className="mt-4 max-w-2xl font-serif text-display-lg">There is nothing at this address.</h1>
          <p className="mt-5 max-w-xl text-lg text-dim">The page may have moved when we reorganised the site and documentation. These will get you back on track.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/" className="btn btn-dark">Go to the homepage</Link>
            <Link href="/docs/" className="btn btn-outline"><Icon name="book" size={17} />Open the documentation</Link>
          </div>
        </div>
      </main>
      <SiteFooter />
    </DemoProvider>
  );
}
