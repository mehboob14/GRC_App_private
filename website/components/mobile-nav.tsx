"use client";

import { useRef } from "react";
import Link from "next/link";

export function MobileNav({ signInUrl, trialUrl }: { signInUrl: string; trialUrl: string }) {
  const menuRef = useRef<HTMLDetailsElement>(null);
  const closeMenu = () => { if (menuRef.current) menuRef.current.open = false; };

  return <details className="mobile-nav" ref={menuRef}>
    <summary aria-label="Open navigation menu"><span></span><span></span><span></span></summary>
    <nav aria-label="Mobile navigation" onClick={(event) => { if ((event.target as HTMLElement).closest("a")) closeMenu(); }}>
      <Link href="/#platform">Platform</Link>
      <Link href="/#coverage">What it covers</Link>
      <Link href="/docs/">Documentation</Link>
      <a href={signInUrl}>Sign in</a>
      <a href={trialUrl}>Start trial</a>
      <Link href="/#request-demo">Book a demo</Link>
    </nav>
  </details>;
}
