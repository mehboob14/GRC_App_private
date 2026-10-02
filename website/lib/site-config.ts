const development = process.env.NODE_ENV !== "production";

function webOrigin(value: string | undefined, name: string, fallback?: string): string {
  const candidate = value || fallback;
  if (!candidate) throw new Error(`${name} is required for the public website build`);
  const url = new URL(candidate);
  if (url.protocol !== "https:" && !(development && url.hostname === "localhost")) {
    throw new Error(`${name} must be an HTTPS origin`);
  }
  if (url.pathname !== "/" || url.search || url.hash || url.username || url.password) {
    throw new Error(`${name} must be an origin without a path, credentials, query, or fragment`);
  }
  return url.origin;
}

export function getSiteConfig() {
  const siteUrl = webOrigin(process.env.SITE_URL, "SITE_URL", development ? "http://localhost:3001" : undefined);
  const appUrl = webOrigin(process.env.APP_URL, "APP_URL", "https://runwaydream.com");
  return {
    siteUrl,
    appUrl,
    trialUrl: `${appUrl}/sign-up`,
    signInUrl: `${appUrl}/sign-in`,
    demoUrl: "/demo/",
  };
}
