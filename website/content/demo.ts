import type { IconName } from "@/components/ui/icon";

/**
 * Copy for the demo request page. Kept out of the components so the page can be
 * translated by swapping this module.
 */

export const demoPage = {
  eyebrow: "Book a demo",
  title: "See Verity with our team.",
  lead: "Tell us who you are and which frameworks you answer to. We reply by email to find a time that suits you.",
  formTitle: "Request a demo",
  formNote: "Takes under a minute.",
  messageLabel: "What would you like to see?",
  messageHint: "Frameworks you answer to, an audit date, the regulator you report to.",
  consent: "We use your details only to reply to this request.",
  afterSubmit: "We reply by email to find a time. Nothing is booked until we confirm it with you.",
  stepsTitle: "What happens next",
  steps: [
    { title: "We email you", text: "A person from our team replies, usually within one business day, to agree a time." },
    { title: "A short conversation", text: "We ask what you answer to and where the work slows down, so the demo covers your situation and not a script." },
    { title: "The real product", text: "A walkthrough of the live platform with demonstration data. We say plainly what is live today and what is coming soon." },
  ] satisfies { title: string; text: string }[],
  success: {
    title: (name: string) => (name ? `Thank you, ${name}. Your request is in.` : "Thank you. Your request is in."),
    text: "If you do not hear from us within a business day, check your spam folder.",
    icon: "check" as const satisfies IconName,
  },
};
