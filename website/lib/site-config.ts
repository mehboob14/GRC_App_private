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

/** An optional HTTPS URL (an endpoint or a policy page). Empty means "not configured". */
export function optionalHttpsUrl(value: string | undefined, name: string): string | null {
  if (!value) return null;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${name} must be a valid URL`);
  }
  if (url.protocol !== "https:" && !(development && url.hostname === "localhost")) throw new Error(`${name} must use HTTPS`);
  if (url.username || url.password) throw new Error(`${name} must not contain credentials`);
  return url.toString();
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
    /** Where demo requests are POSTed as JSON. Unset: the form explains that nothing is sent. */
    demoEndpoint: optionalHttpsUrl(process.env.NEXT_PUBLIC_DEMO_ENDPOINT, "NEXT_PUBLIC_DEMO_ENDPOINT"),
    /** Where "Was this page helpful?" votes are POSTed. Unset: the widget is hidden. */
    feedbackEndpoint: optionalHttpsUrl(process.env.NEXT_PUBLIC_FEEDBACK_ENDPOINT, "NEXT_PUBLIC_FEEDBACK_ENDPOINT"),
    /** Legal pages are linked only once real, approved policies exist. */
    privacyUrl: optionalHttpsUrl(process.env.PRIVACY_URL, "PRIVACY_URL"),
    termsUrl: optionalHttpsUrl(process.env.TERMS_URL, "TERMS_URL"),
    locale: { lang: "en", dir: "ltr" as "ltr" | "rtl" },
  };
}

export type SiteConfig = ReturnType<typeof getSiteConfig>;
