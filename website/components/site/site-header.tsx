import { getSiteConfig } from "@/lib/site-config";
import { platformMenu, resourcesMenu, solutionsMenu } from "@/content/navigation";
import { SiteNavigation } from "./site-navigation";

export function SiteHeader() {
  const { signInUrl, trialUrl } = getSiteConfig();
  return <SiteNavigation platform={platformMenu} solutions={solutionsMenu} resources={resourcesMenu} signInUrl={signInUrl} trialUrl={trialUrl} />;
}
