import { getSiteConfig } from "@/lib/site-config";
import { getSidebarGroups } from "@/lib/docs";
import { DemoProvider } from "@/components/site/demo-provider";
import { SearchProvider } from "@/components/docs/search-dialog";
import { DocsHeader } from "@/components/docs/docs-chrome";
import "../docs.css";

export default function DocsLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { trialUrl, demoEndpoint } = getSiteConfig();
  return (
    <DemoProvider endpoint={demoEndpoint}>
      <div className="docs-root min-h-screen bg-canvas text-body">
        <SearchProvider>
          <DocsHeader groups={getSidebarGroups()} trialUrl={trialUrl} />
          {children}
        </SearchProvider>
      </div>
    </DemoProvider>
  );
}
