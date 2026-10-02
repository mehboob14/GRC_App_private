import { getSiteConfig } from "@/lib/site-config";
import { DemoProvider } from "@/components/site/demo-provider";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";

export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { demoEndpoint } = getSiteConfig();
  return (
    <DemoProvider endpoint={demoEndpoint}>
      <SiteHeader />
      {children}
      <SiteFooter />
    </DemoProvider>
  );
}
