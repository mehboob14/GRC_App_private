import { SoonSection } from "./soon";

export function RiskAssessmentsPage() {
  return (
    <SoonSection
      icon="clipboard"
      title="Risk assessments"
      text="Run assessments in cycles and sign them off, with every risk landing in a register."
      items={[
        { icon: "team", title: "RCSA campaigns", text: "Control owners rate design and operating effectiveness by period." },
        { icon: "workflow", title: "ISO 31000 stages", text: "Scope, identify, analyse, evaluate and treat, each signed off." },
        { icon: "shield", title: "Framework assessments", text: "Maturity and gaps per requirement for ISO 27001, HIPAA and GDPR." },
        { icon: "lightning", title: "Incidents", text: "Record incidents on a timeline and rescore the risks they touch." },
        { icon: "calculator", title: "Quantification", text: "Loss ranges and annual exposure for material risks." },
        { icon: "sparkle", title: "AI mitigation plans", text: "Draft treatment plans from the risk, its controls and incidents." },
      ]}
    />
  );
}

export function RiskIndicatorsPage() {
  return (
    <SoonSection
      icon="trend"
      title="Key risk indicators"
      text="Measures with thresholds that warn before a risk materialises."
      items={[
        { icon: "target", title: "Thresholds", text: "Alert above or below the limit you set for each indicator." },
        { icon: "activity", title: "Measurements", text: "Periodic values, entered or collected, with a trend line." },
        { icon: "bell", title: "Breach alerts", text: "Owners and escalation contacts hear first." },
        { icon: "scales", title: "Appetite and tolerance", text: "Indicators roll up to category appetite and tolerance." },
        { icon: "pulse", title: "Control signals", text: "Failing monitored controls feed the indicators they affect." },
        { icon: "report", title: "Board reporting", text: "Indicator trends in the board pack beside the heatmap." },
      ]}
    />
  );
}
