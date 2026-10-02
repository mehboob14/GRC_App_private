import Link from "next/link";

export default function NotFound() {
  return <main id="main-content" className="not-found site-container"><span className="section-kicker">404 / NOT FOUND</span><h1>This page isn’t in the guide.</h1><p>Try the guide index or go back to the homepage.</p><div className="cta-pair"><Link className="button button-primary" href="/docs/">Open the guide</Link><Link className="button button-outline" href="/">Go home</Link></div></main>;
}
