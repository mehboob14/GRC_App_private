import type { Metadata } from "next";
import { DemoBookingForm } from "@/components/demo-booking-form";

export const metadata: Metadata = { title: "Book a demo", description: "Tell us what you would like to see in a Verity demo.", alternates: { canonical: "/demo/" } };

export default function DemoPage() {
  return <main id="main-content" className="demo-page"><div className="site-container demo-layout"><div className="demo-intro"><h1>Explore Verity with your team.</h1><p>Choose the workflows you want to see and a preferred date. Online booking is being set up, so this form does not send a request yet.</p><div className="demo-agenda"><h2>What we can walk through</h2><ul><li>Controls and evidence with the current SOC 2 library</li><li>Assets, vulnerabilities, and third-party risk</li><li>Risk ownership, decisions, and activity history</li></ul></div></div><DemoBookingForm /></div></main>;
}
