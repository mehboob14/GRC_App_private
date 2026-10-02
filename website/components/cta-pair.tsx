import Link from "next/link";
import { getSiteConfig } from "@/lib/site-config";

export function CtaPair({ light = false, demoHref }: { light?: boolean; demoHref?: string }) {
  const { trialUrl, demoUrl } = getSiteConfig();
  return (
    <div className="cta-pair">
      <a className={`button ${light ? "button-white" : "button-primary"}`} href={trialUrl}>Start trial</a>
      <Link className={`button ${light ? "button-ghost-light" : "button-outline"}`} href={demoHref ?? demoUrl}>Book a demo</Link>
    </div>
  );
}
