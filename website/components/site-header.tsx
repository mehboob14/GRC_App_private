import { Brand } from "./brand";
import { getSiteConfig } from "@/lib/site-config";
import { SiteNavigation } from "./site-navigation";

export function SiteHeader() {
  const config = getSiteConfig();
  return (
    <header className="site-header">
      <div className="site-container header-inner">
        <Brand />
        <SiteNavigation signInUrl={config.signInUrl} trialUrl={config.trialUrl} />
      </div>
    </header>
  );
}
