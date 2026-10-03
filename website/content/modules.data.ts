import type { ModulePage } from "./modules";

/**
 * Copy for the 18 module pages, in the order of `modules` in catalog.ts.
 *
 * Live pages describe only what the product does today, as the user guide and
 * the application code describe it (where they differ, the code wins). Coming
 * soon pages use "will", give no dates and show no metrics; their visuals are
 * concept cards with fictional sample rows. Facts are verifiable numbers from
 * the shipped content library or the product's defaults, never usage metrics.
 */
export const modulePages: ModulePage[] = [
  // ---------------------------------------------------------------- Compliance
  {
    slug: "compliance-automation",
    eyebrow: "Compliance",
    headline: "Every control owned, proven and ready for audit.",
    lead: "Verity starts every workspace with the full SOC 2 control library adopted: 114 controls mapped to 61 criteria. Give each control an owner, work it to Implemented, attach the proof, and see your readiness by criterion instead of rebuilding a spreadsheet before every audit.",
    facts: [
      { label: "SOC 2 criteria mapped", value: "61" },
      { label: "Control templates", value: "114" },
      { label: "Control-to-criterion mappings", value: "150" },
    ],
    heroVisual: { kind: "composition", name: "proof-flow" },
    sections: [
      {
        eyebrow: "Start complete",
        title: "Start with the whole SOC 2 library, not a blank sheet",
        text: "Every new workspace begins with the full SOC 2 control library already adopted, so you edit reality rather than build a list from nothing. The summary line on the register shows at once how many controls lack an owner or evidence. Filter to the unowned ones and work down the list.",
        bullets: [
          "Filter by framework, Trust Services category, type, owner, status or evidence",
          "Add your own controls, marked apart from the shipped library",
          "Owners are workspace members; ownership changes are recorded",
          "Export the register to a spreadsheet",
        ],
        visual: {
          kind: "screenshot",
          name: "controls-register",
          alt: "The controls library register, headed 114 controls, 96 without owner and 112 without evidence, with filters and a row per control showing its Trust Services categories, criteria, owner, evidence count and status",
        },
      },
      {
        eyebrow: "Work a control",
        title: "Work each control from Not started to Implemented",
        text: "Open a control and read what it has to achieve, with short guidance on how it is usually operated. Set the owner, move it to In progress, attach the proof on the Evidence tab, and mark it Implemented once it genuinely operates. History records who changed what, and when.",
        bullets: [
          "Statuses: Not started, In progress, Implemented, Not applicable",
          "Tabs for evidence, automation, requirements, linked records and history",
          "Retire a control with Disable and a reason; its record stays",
        ],
        visual: {
          kind: "screenshot",
          name: "control-detail",
          alt: "A control's detail page for BC-01 Automated, monitored backups, with its statement and implementation guidance, an Automation panel, linked evidence marked Current, and owner, status and SOC 2 mappings in the side column",
        },
      },
      {
        eyebrow: "Map once",
        title: "One control set for every framework you answer to",
        text: "Each control answers one or more criteria, so a single access review can satisfy every requirement that asks for one. Today the SOC 2 library ships with every workspace. Libraries for other standards and regulators will map onto the same controls, so evidence you collect now keeps its value.",
        bullets: [
          "SOC 2 today: 61 criteria, 114 control templates, 150 mappings",
          "Scope records what is in and out of the audit",
          "Libraries for more frameworks are coming soon",
        ],
        visual: { kind: "composition", name: "control-mapping" },
      },
    ],
    capabilities: [
      { icon: "shield", title: "SOC 2 control library", text: "114 control templates mapped to 61 SOC 2 criteria, adopted in every workspace.", status: "live" },
      { icon: "user-check", title: "Named owners", text: "Every control owned by a workspace member, with ownership changes in its history.", status: "live" },
      { icon: "gauge", title: "Readiness dashboard", text: "See how many controls are passing, which criteria are weak and what is in review.", status: "live" },
      { icon: "target", title: "Audit scope", text: "Record what is in and out of the audit, and why.", status: "live" },
      { icon: "plug", title: "Automated checks", text: "Connect GitHub and seven checks run daily, attaching dated results to mapped controls.", status: "live" },
      { icon: "copy", title: "Custom controls", text: "Add controls that answer no framework criterion, marked apart from the shipped library.", status: "live" },
      { icon: "lock", title: "Retire, never delete", text: "Disabled controls keep their history, evidence and mappings for the audit window.", status: "live" },
      { icon: "stack", title: "More framework libraries", text: "ISO/IEC 27001, PCI DSS, HIPAA, GDPR, NIST and regional regulators' frameworks, on the same controls.", status: "soon" },
      { icon: "certificate", title: "More SOC reports", text: "SOC 1 and SOC 3 support will join the SOC 2 library.", status: "soon" },
    ],
    related: ["evidence-management", "policy-management", "integrations", "risk-management"],
    docs: [
      { title: "Frameworks and readiness", href: "/docs/compliance/frameworks/" },
      { title: "Controls", href: "/docs/compliance/controls/" },
      { title: "Automated checks", href: "/docs/compliance/automated-checks/" },
      { title: "More frameworks", href: "/docs/compliance/framework-library/" },
    ],
    faqs: [
      {
        q: "Do we have to build our control list from scratch?",
        a: "No. Every workspace starts with the full SOC 2 library adopted: 114 controls mapped to 61 criteria. You assign owners, set each control's status and mark the ones that do not apply. You can also add controls of your own, and the register marks them apart from the shipped library.",
      },
      {
        q: "Which frameworks are available today?",
        a: "SOC 2 ships today. Libraries for other standards and regulators are coming soon and will map onto the same controls, so you will not repeat work you have already done. The framework library shows the status of each one.",
      },
      {
        q: "Can we delete a control we no longer operate?",
        a: "Controls are disabled rather than deleted, with a reason. A disabled control leaves the active view but keeps its history, evidence and mappings, because an audit asks what you were operating during the period under review. You can enable it again later.",
      },
      {
        q: "Does Verity certify us?",
        a: "No. Certification and attestation come from your auditor or certification body. Verity organises the controls, evidence and decisions they review.",
      },
    ],
  },
  {
    slug: "evidence-management",
    eyebrow: "Compliance",
    headline: "Collect proof once, and know when it goes stale.",
    lead: "Evidence turns a promise into something an auditor can open. Verity keeps each file or link with its owner, the controls it supports and a renewal date, so you see what has gone stale before an auditor does, and a reviewer can approve or reject each item.",
    facts: [
      { label: "Configuration export, default validity", value: "90 days" },
      { label: "Policy document, default validity", value: "1 year" },
      { label: "Log export, default validity", value: "30 days" },
      { label: "Aging window before renewal", value: "30 days" },
    ],
    heroVisual: {
      kind: "screenshot",
      name: "evidence-register",
      alt: "The evidence register, with a freshness chart counting current, aging, stale and no-expiry items, evidence by owner, a coverage snapshot, and rows showing each item's type, controls, owner, renewal date, freshness and review state",
    },
    sections: [
      {
        eyebrow: "Collect once",
        title: "One artefact, attached to every control it proves",
        text: "Upload a file Verity holds, or record a link to something that lives elsewhere. Pick the type and Verity sets a sensible validity, then attach the item to every control it supports. Verity can also suggest controls, and nothing is linked until a person chooses to link it.",
        bullets: [
          "Files cannot change underneath you; links stay current on their own",
          "Validity by type: 90 days for configuration exports, a year for policies",
          "Each suggested control comes with the reason it was proposed",
          "Each item's owner is the person who refreshes it",
        ],
        visual: {
          kind: "screenshot",
          name: "control-detail",
          alt: "A control's detail page with three linked evidence items, each marked Current, beside Link existing and Add evidence buttons",
        },
      },
      {
        eyebrow: "Review and approve",
        title: "Approve or reject, and keep the reason",
        text: "Review is the second look: a reviewer checks what is attached and which controls it is said to support, then approves it or rejects it with a reason. A rejection is not a delete. The item stays, with its reason, so the next person can see why it fell short.",
        bullets: [
          "Review states: Pending review, Approved, Rejected",
          "Filter the register by review state, freshness or type",
          "Every review is written to the audit log",
        ],
        visual: {
          kind: "screenshot",
          name: "evidence-detail",
          alt: "An evidence record for an AWS IAM password policy export, marked Current and Pending review, with Approve and Reject buttons and details of its type, owner, origin, collection date and validity",
        },
      },
      {
        eyebrow: "Without uploads",
        title: "Evidence that arrives without anyone uploading it",
        text: "Connect GitHub and its checks run every day, attaching dated results to the controls they map to, at most once a day unless the result changes. Policies count too: link a document to the controls it satisfies, and it counts toward their coverage without a separate upload.",
        bullets: [
          "Seven GitHub checks attach their output to mapped controls",
          "Results read Passing, Failing or Could not check",
          "A broken connection never looks like a failed control",
          "Cloud and identity connections are coming soon",
        ],
        visual: {
          kind: "screenshot",
          name: "connections",
          alt: "The Connections page, with GitHub ready to connect and other systems such as Amazon Web Services, Okta and Jira listed as planned",
        },
      },
    ],
    capabilities: [
      { icon: "file", title: "Files and links", text: "Hold a copy that cannot change, or link to a system that stays current.", status: "live" },
      { icon: "clock", title: "Validity by type", text: "Each type sets a default renewal date, from 30 days to a year.", status: "live" },
      { icon: "pulse", title: "Freshness at a glance", text: "Current, Aging, Stale or No expiry on every item, filterable in the register.", status: "live" },
      { icon: "link", title: "Map once", text: "Attach one artefact to every control it supports, instead of uploading it again.", status: "live" },
      { icon: "lightbulb", title: "Mapping suggestions", text: "Verity proposes controls an item may support; a person links or dismisses each.", status: "live" },
      { icon: "stamp", title: "Review and approval", text: "Reviewers approve, or reject with a reason; rejected items stay on the record.", status: "live" },
      { icon: "plug", title: "Collected by connections", text: "GitHub check results arrive as dated evidence on the controls they map to.", status: "live" },
      { icon: "cloud", title: "More automated collection", text: "Cloud, identity and ticketing connections will add evidence without uploads.", status: "soon" },
    ],
    related: ["compliance-automation", "integrations", "policy-management", "workflows-and-approvals"],
    docs: [
      { title: "Evidence", href: "/docs/compliance/evidence/" },
      { title: "Automated checks", href: "/docs/compliance/automated-checks/" },
      { title: "Controls", href: "/docs/compliance/controls/" },
    ],
    faqs: [
      {
        q: "Should we upload a file or record a link?",
        a: "Upload a file when the auditor needs a copy that cannot change, such as an export or a signed review. Record a link when the source lives elsewhere and should stay current, such as a dashboard or a ticket. Whoever reads a link later needs access to that system.",
      },
      {
        q: "What happens when evidence expires?",
        a: "Nothing is deleted. An item shows as Aging in the 30 days before its renewal date and as Stale once the date passes. Filter the register by freshness, collect a new copy and keep the old one: it proves the control operated in the earlier window, which is what a Type II audit examines.",
      },
      {
        q: "Does Verity attach evidence to controls by itself?",
        a: "Only from connections: GitHub checks attach their results to the controls they map to as dated evidence. Mapping suggestions are drafts, and nothing is linked until a person chooses to link it.",
      },
      {
        q: "Can we see which controls have no evidence?",
        a: "Yes. The controls register counts controls without evidence in its summary line and can be filtered by evidence, and the evidence register's coverage snapshot shows how many controls have evidence at all.",
      },
    ],
  },
  {
    slug: "policy-management",
    eyebrow: "Compliance",
    headline: "Policies approved, published and actually read.",
    lead: "Draft from 15 templates in a real editor, map each policy to the controls it satisfies, and route it through tiered approval. When the last approver says yes it publishes, and an acknowledgement campaign asks the people who must read it to sign.",
    facts: [
      { label: "Policy templates", value: "15" },
      { label: "Template source licence", value: "Apache-2.0" },
      { label: "Change levels on save", value: "Major, minor, patch" },
    ],
    heroVisual: { kind: "composition", name: "policy-campaign" },
    sections: [
      {
        eyebrow: "Draft and edit",
        title: "Start from a template, not a blank page",
        text: "Choose one of 15 policy templates and you get a complete draft in your organisation's name, ready to edit, with a list of the details still to fill in. Or write from scratch, or upload the PDF or Word file you already have. Every save makes a new version.",
        bullets: [
          "A rich text editor with headings, lists, quotes, links and images",
          "Mark a change as major when people need to read it again",
          "Version history shows what each version changed",
          "Map the policy to the controls it satisfies",
        ],
        visual: {
          kind: "screenshot",
          name: "document-editor",
          alt: "The full-screen editor open on a draft Access Control Policy, with a formatting toolbar, a side panel listing 18 details still to fill in, and the company name already filled in throughout the text",
        },
      },
      {
        eyebrow: "Tiered approval",
        title: "Approval in tiers, published on the final yes",
        text: "Each tier is one round of sign-off and can name a person, a role or a group; for a role or group, any one member decides. Tiers run in order, approvers type approve or reject to confirm, and the document publishes itself when the last required decision lands.",
        bullets: [
          "Approvers get a notification and a dedicated review page",
          "Changing approved text sends the document back to Draft",
          "Published documents are archived, never deleted, and stay readable",
        ],
        visual: {
          kind: "screenshot",
          name: "document-detail",
          alt: "A draft Access Control Policy's detail page, with a banner counting 18 details to fill in before approval, its owner, and Tier 1 reviewers and Tier 2 approvers waiting to be assigned",
        },
      },
      {
        eyebrow: "Acknowledgement campaigns",
        title: "Proof that the people who must read it, did",
        text: "Publishing is not the same as being read. An acknowledgement campaign targets any mix of people, roles and groups, with an optional due date. Each recipient confirms they have read the document, and the campaign records who acknowledged it and when, which is the evidence an auditor asks for.",
        bullets: [
          "Recipients are notified and sign on the campaign page",
          "See who has acknowledged and who is still pending",
          "A policy past its renewal date shows Needs renewal",
        ],
        visual: {
          kind: "screenshot",
          name: "documents-register",
          alt: "The policies and documents register, with Templates and New document buttons and columns for each document's version, owner, status, next review date and acknowledgement state",
        },
      },
    ],
    capabilities: [
      { icon: "file", title: "15 policy templates", text: "Complete drafts in your organisation's name, from an Apache-2.0 open policy library.", status: "live" },
      { icon: "stack", title: "Every save versioned", text: "Version history shows what each version changed, and earlier versions can be restored.", status: "live" },
      { icon: "folder", title: "Upload what you have", text: "Existing PDF or Word policies go through the same approval and acknowledgement.", status: "live" },
      { icon: "stamp", title: "Tiered approval", text: "Name people, roles or groups for each tier; tiers run in order.", status: "live" },
      { icon: "signature", title: "Acknowledgement campaigns", text: "Target people, roles and groups, set a due date, and see who has signed.", status: "live" },
      { icon: "link", title: "Mapped to controls", text: "Link a policy to the frameworks and controls it satisfies.", status: "live" },
      { icon: "lock", title: "Archived, never deleted", text: "Retired documents stay readable, so you can show what a policy said.", status: "live" },
      { icon: "sparkle", title: "AI drafting", text: "Drafts of policies, procedures, guidelines and standards, marked as AI drafts for review.", status: "soon" },
    ],
    related: ["compliance-automation", "evidence-management", "workflows-and-approvals", "trust-center"],
    docs: [
      { title: "Draft a policy", href: "/docs/policies/documents-and-policies/" },
      { title: "Approve and publish", href: "/docs/policies/approval-and-publishing/" },
      { title: "Acknowledgement campaigns", href: "/docs/policies/acknowledgement-campaigns/" },
    ],
    faqs: [
      {
        q: "We already have policies. Do we have to rewrite them?",
        a: "No. Upload your existing PDF or Word files. Approval, publishing and acknowledgement then work exactly as they do for a policy written in Verity.",
      },
      {
        q: "What happens if someone edits an approved policy?",
        a: "Changing the text of an approved or published document, by saving a new version or restoring an old one, returns it to Draft and clears its approvals. They were given against wording that is no longer current, so it must be approved again before it is published.",
      },
      {
        q: "How do we show an auditor that staff read a policy?",
        a: "Run an acknowledgement campaign on the published document. Its record shows who acknowledged it and when, and who is still pending.",
      },
      {
        q: "Can AI write our policies?",
        a: "Not yet. AI drafting is coming soon. When it arrives, AI drafts will be marked as such and will go through the same review and approval as anything a person writes. Today, the 15 templates give you a complete first draft in your organisation's name.",
      },
    ],
  },
  {
    slug: "trust-center",
    eyebrow: "Compliance",
    headline: "Show customers your security posture before they ask.",
    lead: "The Trust Center will let you publish a public page that shows customers and prospects how you look after security: the policies you choose to share, the attestations you hold, and controlled access to sensitive documents. Nothing will appear on it until a person approves it.",
    heroVisual: {
      kind: "list",
      title: "Trust Center documents",
      icon: "seal",
      rows: [
        { label: "Information security policy", meta: "Policy · published", status: "Public", tone: "success" },
        { label: "SOC 2 Type II report", meta: "Attestation", status: "Under NDA", tone: "warning" },
        { label: "Penetration test summary", meta: "Report", status: "On request", tone: "progress" },
        { label: "Business continuity plan", meta: "Policy · published", status: "Public", tone: "success" },
        { label: "Access control policy", meta: "Policy · new version", status: "Awaiting approval", tone: "pending" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Share posture",
        title: "One public page for your security story",
        text: "Customers ask the same questions before every deal. The Trust Center will give them a page you publish: how you protect their data, which policies you share, and which certifications and attestations you hold, drawn from the policies, controls and evidence you already keep in Verity.",
        bullets: [
          "You will choose which published policies appear",
          "A list of the certifications and attestations you hold",
          "Built on records you already keep for audits",
        ],
        visual: {
          kind: "list",
          title: "Published on your Trust Center",
          icon: "globe",
          rows: [
            { label: "Information security policy", meta: "Published", status: "Shown", tone: "success" },
            { label: "Acceptable use policy", meta: "Published", status: "Shown", tone: "success" },
            { label: "Incident response plan", meta: "Draft", status: "Not shared", tone: "neutral" },
            { label: "SOC 2 Type II report", meta: "Attestation", status: "On request", tone: "progress" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Controlled access",
        title: "Sensitive documents shared only with the right people",
        text: "Some documents will be open to anyone. Others, such as an audit report, will be shared only on request, for example once a visitor has asked for access or accepted a non-disclosure agreement. A person in your organisation will decide what appears and who sees each document.",
        bullets: [
          "Public, on-request and NDA-protected documents",
          "Nothing published without a person approving it",
          "Changes recorded in the audit log, like everything else",
        ],
        visual: {
          kind: "list",
          title: "Document access requests",
          icon: "lock",
          rows: [
            { label: "SOC 2 Type II report", meta: "Arden Health · NDA accepted", status: "Awaiting decision", tone: "pending" },
            { label: "Penetration test summary", meta: "Kestrel Freight", status: "Approved", tone: "success" },
            { label: "Data processing agreement", meta: "Unverified visitor", status: "Declined", tone: "danger" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "globe", title: "Public security page", text: "A page you will publish to show customers how you protect their data.", status: "soon" },
      { icon: "file", title: "Shared policies", text: "You will choose which published policies appear, from your policy library.", status: "soon" },
      { icon: "certificate", title: "Attestations listed", text: "It will list the certifications and attestations your organisation holds.", status: "soon" },
      { icon: "lock", title: "Controlled document access", text: "Some documents open to anyone; sensitive ones only on request or under NDA.", status: "soon" },
      { icon: "user-check", title: "Human approval", text: "Nothing will appear on the page until a person in your organisation approves it.", status: "soon" },
      { icon: "link", title: "Built on your records", text: "It will draw on the policies, controls and evidence you already keep in Verity.", status: "soon" },
    ],
    related: ["policy-management", "questionnaire-automation", "compliance-automation", "evidence-management"],
    docs: [
      { title: "Trust Center", href: "/docs/roadmap/trust-center/" },
      { title: "Approve and publish", href: "/docs/policies/approval-and-publishing/" },
      { title: "Evidence", href: "/docs/compliance/evidence/" },
    ],
    faqs: [
      {
        q: "When will the Trust Center be available?",
        a: "It is planned, and we do not give dates for planned work. If it matters to your evaluation, tell us what you need using the form on this page.",
      },
      {
        q: "Will anything be published automatically?",
        a: "No. A person in your organisation will decide what appears on the page and who can see each document. Nothing will be published without someone approving it.",
      },
      {
        q: "Will Verity certify us for what the page shows?",
        a: "No. The page will list certifications and attestations you hold, which come from your auditor or certification body. Verity does not issue them.",
      },
      {
        q: "What can we do today?",
        a: "Keep the records a Trust Center will draw on in good order: policies approved and published, acknowledgement campaigns run, evidence current and readiness visible on the compliance dashboard. All of that is live now.",
      },
    ],
    today: [
      { title: "Approve and publish policies", text: "Tiered approval and publishing with a full version history.", href: "/platform/policy-management/" },
      { title: "Keep evidence current", text: "Renewal dates and freshness on every artefact behind your controls.", href: "/platform/evidence-management/" },
      { title: "See your readiness", text: "The compliance dashboard shows passing controls and weak criteria.", href: "/docs/compliance/frameworks/" },
    ],
  },
  {
    slug: "questionnaire-automation",
    eyebrow: "Compliance",
    headline: "Answer customer security questionnaires from your records.",
    lead: "Questionnaire automation will help you answer the security questionnaires your customers send, using the controls, policies and evidence you already keep in Verity. AI will suggest an answer for each question, and a person on your team will review, edit and approve every answer before anything is sent.",
    heroVisual: {
      kind: "list",
      title: "Security questionnaire from a customer",
      icon: "clipboard",
      rows: [
        { label: "Do you encrypt customer data at rest?", meta: "Suggested from a control and its evidence", status: "AI draft", tone: "pending" },
        { label: "Is two-factor sign-in enforced for administrators?", meta: "Suggested from the access control policy", status: "Approved", tone: "success" },
        { label: "How often do you review user access?", meta: "Edited by a reviewer", status: "In review", tone: "progress" },
        { label: "Do you test your incident response plan?", meta: "No matching record found", status: "Needs an answer", tone: "warning" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Inbound, not outbound",
        title: "The reverse of the vendor questionnaires you send today",
        text: "Verity already sends questionnaires to your suppliers through the vendor portal. Questionnaire automation will work the other way round: when a customer asks you, answers will draw on the controls you operate, the policies you have published and the evidence behind them, rather than a blank page each time.",
        bullets: [
          "Answers drawn from controls, policies and evidence",
          "Answers that start from your records, not a blank page",
          "Vendor questionnaires to your suppliers are live today",
        ],
        visual: {
          kind: "list",
          title: "How often do you review user access?",
          icon: "link",
          rows: [
            { label: "IAM-02 Periodic user access reviews", meta: "Control", status: "Implemented", tone: "success" },
            { label: "Access control policy", meta: "Policy", status: "Published", tone: "success" },
            { label: "Q3 access review sign-off", meta: "Evidence", status: "Current", tone: "success" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "AI drafts",
        title: "AI will suggest the answer, a person will approve it",
        text: "For each question, AI will suggest an answer from your records and mark it as an AI draft. Someone on your team will review it, edit it where needed and approve it. Nothing will be sent to a customer until a person approves it, and AI will never send or approve anything itself.",
        bullets: [
          "Every suggested answer marked as an AI draft",
          "The same review and approval as a human answer",
          "Prompts and outputs logged, so a bad draft is traceable",
          "You will be able to write any answer yourself",
        ],
        visual: {
          kind: "list",
          title: "Answer review",
          icon: "sparkle",
          rows: [
            { label: "Encryption of customer data at rest", meta: "AI draft · from a control and its evidence", status: "Needs review", tone: "warning" },
            { label: "Two-factor sign-in for administrators", meta: "Edited by Priya Nair", status: "Approved", tone: "success" },
            { label: "Incident response testing", meta: "No source found · write it yourself", status: "Unanswered", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "clipboard", title: "Inbound questionnaires", text: "You will work through the questionnaires customers send you in one place.", status: "soon" },
      { icon: "link", title: "Answers from records", text: "Answers will draw on your controls, published policies and current evidence.", status: "soon" },
      { icon: "sparkle", title: "AI-suggested answers", text: "A suggested answer for each question, marked as an AI draft.", status: "soon" },
      { icon: "user-check", title: "Human approval", text: "A person will review, edit and approve every answer before it is sent.", status: "soon" },
      { icon: "scroll", title: "Traceable drafts", text: "Prompts and outputs logged, so any draft can be traced.", status: "soon" },
      { icon: "chat", title: "Manual path always", text: "You will always be able to write an answer yourself, without AI.", status: "soon" },
    ],
    related: ["trust-center", "ai-assistant", "compliance-automation", "third-party-risk"],
    docs: [
      { title: "Questionnaire automation", href: "/docs/roadmap/questionnaire-automation/" },
      { title: "AI assistant and drafting", href: "/docs/roadmap/ai-assistant/" },
      { title: "Questionnaires and the portal", href: "/docs/vendors/questionnaires/" },
    ],
    faqs: [
      {
        q: "Is this the same as the vendor questionnaires in Verity?",
        a: "No. Vendor questionnaires, which are live, are ones you send to your suppliers through the vendor portal. Questionnaire automation is the reverse: it will help you answer the questionnaires your own customers send you.",
      },
      {
        q: "Will AI send answers to our customers?",
        a: "No. AI will suggest answers and mark them as AI drafts. A person will review and approve every answer, and nothing will be sent until they do.",
      },
      {
        q: "What can we do now to be ready?",
        a: "Good answers come from good records. Keep controls owned and implemented, policies published and evidence current. Those are the records answers will draw on, and all of that work is live today.",
      },
    ],
    today: [
      { title: "Keep controls owned and implemented", text: "The SOC 2 library, with an owner and a status for every control.", href: "/platform/compliance-automation/" },
      { title: "Publish your policies", text: "Templates, tiered approval and acknowledgement campaigns.", href: "/platform/policy-management/" },
      { title: "Send questionnaires to vendors", text: "The vendor portal for questionnaires you send to suppliers.", href: "/docs/vendors/questionnaires/" },
    ],
  },

  // ---------------------------------------------------------------------- Risk
  {
    slug: "risk-management",
    eyebrow: "Risk",
    headline: "Risks scored the same way and decided on the record.",
    lead: "Keep one or more risk registers, each with its own scoring matrix, categories and review cadence. Score inherent and residual risk, link the controls that reduce it, track treatment as tasks, and accept risks formally, with an approver, a justification and an end date.",
    facts: [
      { label: "Library risks", value: "60" },
      { label: "Treatment options", value: "4" },
      { label: "Scores on every risk", value: "Inherent and residual" },
    ],
    heroVisual: {
      kind: "screenshot",
      name: "risks-overview",
      alt: "The risks Overview tab, with counts of open, high and critical, uncontrolled, overdue and expiring risks, a likelihood-by-impact heatmap with a residual and inherent toggle, top risks, and breakdowns by severity, treatment and category",
    },
    sections: [
      {
        eyebrow: "Score every risk",
        title: "Write risks people can argue about, and score them",
        text: "Write each risk as a sentence with a consequence, file it under a category and score it twice: inherent, before your controls act, and residual, after they do. AI Assist can propose a starting draft, or the closest starter-library risk when no AI model is configured. Nothing is applied until you use it.",
        bullets: [
          "Likelihood times impact, on the register's own scale",
          "Treatment: mitigate, accept, avoid or transfer",
          "Set a business owner and a treatment due date",
          "Flags for risks with no owner or no linked control",
        ],
        visual: {
          kind: "screenshot",
          name: "dialog-add-risk",
          alt: "The Add risk dialog, with a title field and an AI Assist button, description, root cause, consequences and recommendations fields, category, status, business owner, business unit and linked assets, and inherent and residual scoring",
        },
      },
      {
        eyebrow: "Treat or accept",
        title: "Treat it, or accept it with an owner and an end date",
        text: "Write a treatment plan, raise its actions as tasks and link the controls that reduce the risk. To live with a risk instead, request acceptance with the reason the remaining risk is acceptable and an expiry date. Someone other than the requester decides, and when the expiry passes the risk reopens on its own.",
        bullets: [
          "Requesters cannot approve their own acceptance",
          "Linked controls make your library an answer to the register",
          "Raise a risk straight from a vendor finding or a vulnerability",
          "Every change kept in the risk's history and the audit log",
        ],
        visual: {
          kind: "screenshot",
          name: "risk-detail",
          alt: "A risk's detail page for an unlawful cross-border transfer of personal data, scored 12 and High before controls, with tabs for treatment, controls, links, acceptance and history, its description, root cause, consequences and recommendations, and inherent and residual heatmaps",
        },
      },
      {
        eyebrow: "Your registers",
        title: "Registers shaped to how your organisation works",
        text: "An operational register and a project register rarely want the same scales. Each register keeps its own likelihood and impact matrix, severity bands, categories and review cadence. Start from a library of 60 written and scored risks, or import your spreadsheet and check a preview before anything is created.",
        bullets: [
          "Adopted library risks stay editable and are never overwritten",
          "Import from a template, with a preview that catches mismatched columns",
          "Export the register to a spreadsheet",
          "Overdue reviews and expiring acceptances counted on the overview",
        ],
        visual: {
          kind: "screenshot",
          name: "risks-settings",
          alt: "Risk settings listing a default Enterprise risk register with a five-by-five matrix and a 90-day review cadence, links to its matrix and categories, and further options such as custom fields and risk appetite marked Soon",
        },
      },
    ],
    capabilities: [
      { icon: "stack", title: "Multiple registers", text: "Separate registers, each with its own matrix, bands, categories and cadence.", status: "live" },
      { icon: "chart", title: "Inherent and residual", text: "Two scores per risk show what your controls actually change.", status: "live" },
      { icon: "shield", title: "Linked controls", text: "Attach the controls that reduce a risk; risks without one are flagged.", status: "live" },
      { icon: "kanban", title: "Treatment as tasks", text: "Treatment actions tracked as tasks, where all other work lives.", status: "live" },
      { icon: "signature", title: "Formal acceptance", text: "A stated reason, an approver who is not the requester, and an expiry.", status: "live" },
      { icon: "book", title: "Starter library", text: "60 common risks, already written and scored, ready to adopt and edit.", status: "live" },
      { icon: "sparkle", title: "AI Assist", text: "A proposed starting draft for a new risk, applied only if you choose.", status: "live" },
      { icon: "chart-line", title: "Key risk indicators", text: "Measures with thresholds and trends, with alerts on breach.", status: "soon" },
      { icon: "gauge", title: "Risk appetite", text: "Appetite and tolerance per category, escalating risks above tolerance.", status: "soon" },
    ],
    related: ["third-party-risk", "enterprise-risk-management", "compliance-automation", "workflows-and-approvals"],
    docs: [
      { title: "The risk register", href: "/docs/risk/risk-register/" },
      { title: "Treat or accept a risk", href: "/docs/risk/treatment-and-acceptance/" },
      { title: "Library and settings", href: "/docs/risk/library-and-settings/" },
    ],
    faqs: [
      {
        q: "Can we import our existing risk register?",
        a: "Yes. Download the import template, fill it in and upload it. Verity shows a preview of what it read, so you can catch a column mapped to the wrong field before you commit.",
      },
      {
        q: "Can we use our own scoring matrix?",
        a: "Yes. Each register has its own likelihood and impact scales, severity bands, categories and review cadence, set by an administrator in Risks settings. Weighted or additive scoring formulas are planned.",
      },
      {
        q: "How do you stop accepted risks being forgotten?",
        a: "Every acceptance states why the remaining risk is acceptable, needs an approver who is not the requester, and carries an expiry date. When the expiry passes, the acceptance lapses and the risk reopens on its own.",
      },
      {
        q: "Does AI change our risk scores?",
        a: "No. When you add a risk, AI Assist can propose a starting draft, or the closest starter-library risk when no AI model is configured. Nothing is applied until you choose to use it, and nothing is saved until you save the risk.",
      },
    ],
  },
  {
    slug: "third-party-risk",
    eyebrow: "Risk",
    headline: "Vendors reviewed in proportion to the risk they carry.",
    lead: "Run each third party from the first request to offboarding in twelve stages. Tiering decides how deep the review goes, vendors answer questionnaires through a portal without an account, gaps become findings with owners, and an approval gate will not clear while critical findings remain open.",
    facts: [
      { label: "Lifecycle stages", value: "12" },
      { label: "Tiering questions", value: "5" },
      { label: "Questionnaire bank questions", value: "59" },
      { label: "Assessment grades", value: "A to F" },
    ],
    heroVisual: { kind: "composition", name: "vendor-register" },
    sections: [
      {
        eyebrow: "Request and intake",
        title: "Every new vendor starts as a request someone decides",
        text: "Anyone who can see the vendor register can request a new vendor: name, department, intended use and urgency. Verity checks the name against the register and flags likely duplicates. The third-party risk team approves, which creates the vendor and its first engagement, or declines with a reason that is kept.",
        bullets: [
          "Possible duplicates shown before anyone decides the request",
          "A request cannot be decided twice; declines keep their reason",
          "Shadow IT apps can be sent to intake or ignored",
          "The team can also add a vendor directly",
        ],
        visual: {
          kind: "screenshot",
          name: "vendors-intake",
          alt: "The vendor Intake tab with three pending requests, each showing its urgency, the data it would share and Approve and create or Decline buttons, one flagged because a vendor with the same name is already in the register",
        },
      },
      {
        eyebrow: "Proportionate diligence",
        title: "Diligence in proportion to what each vendor touches",
        text: "Five weighted questions, on data sensitivity, business criticality, system access, regulatory scope and fourth-party reliance, place each engagement in a Low, Medium, High or Critical tier. The tier sets the questionnaire, the reassessment cadence and how strict the approval gate is, and the twelve stages are planned from it.",
        bullets: [
          "Each engagement tiered on its own, not the whole vendor",
          "A tier override needs a reason",
          "Re-tiering reopens stages the new tier requires",
          "Bands, cadences and remediation windows set in vendor policy",
        ],
        visual: {
          kind: "screenshot",
          name: "vendor-lifecycle",
          alt: "A vendor's Lifecycle tab for Meridian Payroll, with a tier score of 92.5 in the Critical band, a progress bar across twelve stages, and the Intake stage's checks beside the stages grouped into assess, decide and operate",
        },
      },
      {
        eyebrow: "Assess and decide",
        title: "Answers become a grade, gaps become findings",
        text: "Send a questionnaire from the vendor's Assessments tab and Verity emails a portal link that works for 30 days; the vendor answers without an account. Answers produce a residual score and a grade from A to F. Gaps become findings with a severity, an owner and a due date, and critical findings hold the approval gate shut.",
        bullets: [
          "Verity stores only a hash of each portal link",
          "Remediate a finding, accept it with an expiry, or raise a risk",
          "Approval outcomes: Approved, Approved with conditions, Deferred, Rejected",
          "Neither the requester nor the business owner can approve",
        ],
        visual: {
          kind: "screenshot",
          name: "vendors-findings",
          alt: "The vendor Findings tab filtered to open findings, showing a Critical finding for an adverse opinion in a vendor's SOC 2 Type II report",
        },
      },
    ],
    capabilities: [
      { icon: "path", title: "Twelve-stage lifecycle", text: "Intake to offboarding on each engagement, with skipped stages recorded as skipped by policy.", status: "live" },
      { icon: "funnel", title: "Request and intake", text: "Anyone can request a vendor; likely duplicates are flagged before review.", status: "live" },
      { icon: "gauge", title: "Risk tiering", text: "Five weighted questions set a Low, Medium, High or Critical tier.", status: "live" },
      { icon: "clipboard", title: "Questionnaires and portal", text: "Build from a 59-question bank; vendors answer without an account.", status: "live" },
      { icon: "chart", title: "Scores and grades", text: "A residual score and an A to F grade, capped when key controls are missing.", status: "live" },
      { icon: "flag", title: "Findings", text: "Severity, owner and a policy-driven due date; remediate, accept or raise a risk.", status: "live" },
      { icon: "stamp", title: "Approval gate", text: "Four outcomes, each with a rationale, blocked while critical findings stay open.", status: "live" },
      { icon: "folder", title: "Paperwork and monitoring", text: "Contracts, DPAs and SOC 2 reports with expiry dates, plus monitoring signals and alert rules.", status: "live" },
      { icon: "eye", title: "Shadow IT", text: "Record apps that skipped intake, then send them to intake or ignore them.", status: "live" },
    ],
    related: ["risk-management", "workflows-and-approvals", "compliance-automation", "asset-inventory"],
    docs: [
      { title: "How vendor risk works", href: "/docs/vendors/overview/" },
      { title: "Tiering", href: "/docs/vendors/tiering/" },
      { title: "Questionnaires and the portal", href: "/docs/vendors/questionnaires/" },
      { title: "Assessment and findings", href: "/docs/vendors/assessment-and-findings/" },
    ],
    faqs: [
      {
        q: "Do our vendors need a Verity account to answer?",
        a: "No. Send the questionnaire from the vendor's Assessments tab and Verity emails a portal link to your contact. The vendor answers without an account or password, attaches files and saves as they go. The link works for 30 days, and Verity stores only a hash of it.",
      },
      {
        q: "Can we import our current vendor list?",
        a: "There is no spreadsheet import for vendors today. The third-party risk team adds each vendor directly, with the data it touches, its business, security and relationship owners and its first engagement, and anyone in the workspace can request a vendor through intake.",
      },
      {
        q: "Can we use our own tiering rules?",
        a: "Yes. In vendor policy an administrator sets the tier bands, the reassessment cadence for each tier, the remediation window for each finding severity and which stages each tier may skip. Work already under way keeps the policy it started under.",
      },
      {
        q: "What stops a risky vendor being approved?",
        a: "The approval stage is a gate. It will not clear while an earlier stage or a critical or blocking finding is open, or while required reviewers are unassigned. Neither the requester nor the vendor's business owner can approve, and every decision carries a rationale.",
      },
    ],
  },
  {
    slug: "enterprise-risk-management",
    eyebrow: "Risk",
    headline: "See risk across the organisation, not one register.",
    lead: "Enterprise risk management will grow the live risk register into a full programme: control self-assessments, structured risk assessments, incidents, key risk indicators and risk appetite, all feeding the registers you already keep. AI will draft mitigation plans, and a person will always decide.",
    heroVisual: {
      kind: "list",
      title: "Key risk indicators",
      icon: "chart-line",
      rows: [
        { label: "Failed sign-in attempts", meta: "Security · trend rising", status: "Above threshold", tone: "danger" },
        { label: "Vendors overdue for reassessment", meta: "Third parties · trend rising", status: "Near threshold", tone: "warning" },
        { label: "Critical findings past their window", meta: "Technology · trend flat", status: "Within threshold", tone: "success" },
        { label: "Payment processing incidents", meta: "Operations · trend falling", status: "Within threshold", tone: "success" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Structured assessment",
        title: "Self-assessments and structured risk assessments",
        text: "Risk and control self-assessment campaigns will ask control owners, period by period, to rate how well their controls are designed and how well they operate, with results rolled up by business unit. Structured risk assessments will follow the ISO 31000 stages, with sign-off, and every risk they identify will land in a register.",
        bullets: [
          "Self-assessment campaigns by period, rolled up by business unit",
          "ISO 31000 stages: scope, identify, analyse, evaluate, treat",
          "Framework maturity assessments on the shared control engine",
        ],
        visual: {
          kind: "list",
          title: "Control self-assessment",
          icon: "list",
          rows: [
            { label: "Periodic user access reviews", meta: "Retail banking · Ayesha Raza", status: "Effective", tone: "success" },
            { label: "Backup restore testing", meta: "Technology · Daniel Mensah", status: "Needs improvement", tone: "warning" },
            { label: "Vendor security due diligence", meta: "Procurement · Sara Haddad", status: "In progress", tone: "progress" },
            { label: "Peer code review", meta: "Engineering · Liam Walsh", status: "Not assessed", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Indicators and appetite",
        title: "Incidents, indicators and appetite in one picture",
        text: "You will record incidents with a severity and a timeline and link them to the risks and controls involved; an incident on a risk will prompt a rescore. Key risk indicators will track measures against thresholds, and appetite and tolerance per category will flag risks above appetite and escalate those above tolerance.",
        bullets: [
          "Key risk indicators with thresholds, trends and alerts on breach",
          "Risks above tolerance will escalate to a named owner",
          "AI-drafted mitigation plans will go through the normal approval",
          "Configurable approval workflows for risks, incidents, documents and vendors",
        ],
        visual: {
          kind: "list",
          title: "Risk appetite by category",
          icon: "gauge",
          rows: [
            { label: "Liquidity", meta: "Owner: Treasurer", status: "Above tolerance", tone: "danger" },
            { label: "Data privacy", meta: "Owner: Privacy Officer", status: "Above appetite", tone: "warning" },
            { label: "Operational resilience", meta: "Owner: Chief Operating Officer", status: "Within appetite", tone: "success" },
            { label: "Regulatory compliance", meta: "Owner: Head of Compliance", status: "Within appetite", tone: "success" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "list", title: "Control self-assessments", text: "Campaigns by period, with results rolled up by business unit.", status: "soon" },
      { icon: "search", title: "Risk assessments", text: "Structured assessments through the ISO 31000 stages, with sign-off.", status: "soon" },
      { icon: "siren", title: "Incidents", text: "Severity, timeline and links to risks and controls; an incident will prompt a rescore.", status: "soon" },
      { icon: "chart-line", title: "Key risk indicators", text: "Measures with thresholds and trends, alerting the owner on breach.", status: "soon" },
      { icon: "gauge", title: "Risk appetite", text: "Appetite and tolerance per category; risks above tolerance will escalate to a named owner.", status: "soon" },
      { icon: "certificate", title: "Framework assessments", text: "Maturity and gaps per requirement for frameworks such as ISO 27001.", status: "soon" },
      { icon: "tree", title: "Configurable workflows", text: "Approval steps for decisions on risks, incidents, documents and vendors.", status: "soon" },
      { icon: "sparkle", title: "AI mitigation drafts", text: "Draft treatment plans that a person will review and approve.", status: "soon" },
    ],
    related: ["risk-management", "business-continuity", "third-party-risk", "ai-assistant"],
    docs: [
      { title: "Enterprise risk", href: "/docs/risk/enterprise-risk/" },
      { title: "The risk register", href: "/docs/risk/risk-register/" },
      { title: "Treat or accept a risk", href: "/docs/risk/treatment-and-acceptance/" },
    ],
    faqs: [
      {
        q: "Is the risk register available now?",
        a: "Yes. Multiple registers, inherent and residual scoring, linked controls, treatment tracked as tasks and formal acceptance with an expiry are all live. Enterprise risk management will build on those registers rather than replace them.",
      },
      {
        q: "How will AI be used in enterprise risk?",
        a: "AI will draft treatment plans and actions from a risk, its controls and its incidents. Drafts will be marked as AI drafts and go through the same review and approval as anything a person writes. AI will never change a score, accept a risk or close one.",
      },
      {
        q: "Where can we record incidents until then?",
        a: "Record something that went wrong as an issue in Tasks, with containment, corrective, preventive and verification actions underneath it. Each action has its own owner and state.",
      },
    ],
    today: [
      { title: "Run your risk registers", text: "Scoring, treatment, acceptance and a 60-risk starter library.", href: "/platform/risk-management/" },
      { title: "Track issues and corrective actions", text: "Issues with containment, corrective, preventive and verification actions.", href: "/platform/workflows-and-approvals/" },
      { title: "Assess third parties", text: "The twelve-stage vendor lifecycle, tiered by risk.", href: "/platform/third-party-risk/" },
    ],
  },
  {
    slug: "business-continuity",
    eyebrow: "Risk",
    headline: "Know what matters most, and how you will recover it.",
    lead: "Business continuity will help you plan for disruption: identify the processes and services the business depends on, keep the plans for keeping them running and restoring them, and record the exercises that show those plans work, linked to the assets, vendors and risks you already track.",
    heroVisual: {
      kind: "list",
      title: "Business impact analysis",
      icon: "lifebuoy",
      rows: [
        { label: "Card payments processing", meta: "Depends on Payments API Gateway", status: "Critical", tone: "danger" },
        { label: "Customer onboarding", meta: "Depends on Customer Portal", status: "High", tone: "warning" },
        { label: "Monthly payroll", meta: "Depends on a payroll vendor", status: "Medium", tone: "pending" },
        { label: "Marketing website", meta: "Depends on a hosting vendor", status: "Low", tone: "neutral" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Impact analysis",
        title: "Start from what the business cannot do without",
        text: "A business impact analysis will identify the processes and services the organisation depends on and what an outage of each would cost. It will draw on records Verity already keeps: how critical each asset is, what depends on what, and which vendors the business relies on.",
        bullets: [
          "Processes and services ranked by the cost of an outage",
          "Linked to critical assets and their dependencies",
          "Linked to the vendors the business cannot do without",
        ],
        visual: {
          kind: "list",
          title: "What card payments depend on",
          icon: "tree",
          rows: [
            { label: "Payments API Gateway", meta: "Application · asset", status: "Critical", tone: "danger" },
            { label: "Core Banking Database", meta: "Data · asset", status: "Critical", tone: "danger" },
            { label: "Harbor Cloud Hosting", meta: "Infrastructure · vendor", status: "Critical tier", tone: "danger" },
            { label: "Card scheme connectivity", meta: "Business service · asset", status: "High", tone: "warning" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Plans and exercises",
        title: "Recovery plans, with proof that they were tested",
        text: "Continuity and recovery plans will sit next to the records they depend on, so a plan points at the assets, vendors and processes behind it. You will record exercises against each plan and what they found, so you can show an auditor or a regulator that the plans hold up.",
        bullets: [
          "Plans for staying running and for restoring systems and data",
          "Exercises recorded with what they found",
          "The detailed design is still being settled",
        ],
        visual: {
          kind: "list",
          title: "Continuity exercises",
          icon: "calendar",
          rows: [
            { label: "Core banking failover", meta: "Recovery plan · tabletop", status: "Passed", tone: "success" },
            { label: "Payroll vendor outage", meta: "Continuity plan · walkthrough", status: "Findings raised", tone: "warning" },
            { label: "Loss of the main office", meta: "Continuity plan", status: "Planned", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "target", title: "Business impact analysis", text: "Critical processes and services identified, with what an outage would cost.", status: "soon" },
      { icon: "lifebuoy", title: "Continuity plans", text: "Plans for keeping critical services running through disruption.", status: "soon" },
      { icon: "database", title: "Recovery plans", text: "How you restore systems and data, next to the records they depend on.", status: "soon" },
      { icon: "calendar", title: "Testing exercises", text: "Exercises recorded against each plan, with what they found.", status: "soon" },
      { icon: "flag", title: "Exercise findings", text: "What an exercise found, kept with the plan it tested.", status: "soon" },
      { icon: "tree", title: "Linked dependencies", text: "Plans linked to the critical assets, vendors and processes behind them.", status: "soon" },
    ],
    related: ["asset-inventory", "third-party-risk", "risk-management", "enterprise-risk-management"],
    docs: [
      { title: "Business continuity", href: "/docs/risk/business-continuity/" },
      { title: "Hygiene and dependencies", href: "/docs/assets/hygiene-and-dependencies/" },
      { title: "Tiering", href: "/docs/vendors/tiering/" },
    ],
    faqs: [
      {
        q: "What will the business continuity module include?",
        a: "The planned direction is business impact analysis, continuity and recovery plans, and testing exercises, linked to the assets, vendors and processes you rely on. The detailed design is still being settled, so its exact shape may change.",
      },
      {
        q: "Can we keep a continuity plan in Verity today?",
        a: "Yes, as a policy. The template library includes a Business Continuity and Disaster Recovery template you can draft from and take through approval, publishing and acknowledgement.",
      },
      {
        q: "Which records will it build on?",
        a: "Asset criticality and dependencies, the business criticality question in vendor tiering, continuity risks in your register, and the availability controls in your SOC 2 library. All of those are live today.",
      },
    ],
    today: [
      { title: "Map dependencies between assets", text: "Criticality from the CIA rating, and what runs on what.", href: "/platform/asset-inventory/" },
      { title: "Draft your BC/DR plan", text: "Start from the Business Continuity and Disaster Recovery template.", href: "/platform/policy-management/" },
      { title: "Tier vendors by criticality", text: "Business criticality is one of the five tiering questions.", href: "/platform/third-party-risk/" },
    ],
  },

  // ------------------------------------------------------------------ Security
  {
    slug: "asset-inventory",
    eyebrow: "Security",
    headline: "Know what you run, who owns it and how critical it is.",
    lead: "The asset inventory records every application, piece of infrastructure, data store, cloud resource, third party and business service you run. Criticality is derived from confidentiality, integrity and availability ratings and exposure, each record carries a hygiene score, and dependencies show what else goes down with it.",
    facts: [
      { label: "Asset types", value: "6" },
      { label: "Hygiene checks per asset", value: "5" },
      { label: "CIA rating scale", value: "1 to 5" },
      { label: "Default review cadence", value: "90 days" },
    ],
    heroVisual: {
      kind: "screenshot",
      name: "assets-register",
      alt: "The asset register, headed 10 assets and 8 critical, with counts for total, critical, unrated, regulated and stale assets, filters, and rows showing each asset's type, owner, criticality, CIA rating, lifecycle state and value",
    },
    sections: [
      {
        eyebrow: "Derived criticality",
        title: "Criticality you can explain to an auditor",
        text: "You do not type a criticality. Rate confidentiality, integrity and availability from 1 to 5, and Verity starts from the highest rating, then raises it for internet-facing assets, confidential or restricted data and high-impact business functions. The result is a score out of 10 and a tier.",
        bullets: [
          "Tiers: low, medium, high or critical",
          "Not rated is not medium: an unrated asset has no tier",
          "Identity, classification and exposure fields on every asset",
          "Lifecycle from planned and active to decommissioned and retired",
        ],
        visual: {
          kind: "screenshot",
          name: "asset-detail",
          alt: "An asset's detail page for Analytics Warehouse, a critical cloud resource scoring 9.0, with identity, classification and exposure details and an inventory hygiene panel showing five of five checks complete",
        },
      },
      {
        eyebrow: "Inventory hygiene",
        title: "A completeness score you can check, not just trust",
        text: "Every asset shows five hygiene checks, each worth twenty points: primary owner, type, criticality, data classification and CIA rating. Under them, a freshness line says when a person last reviewed the record. Set how long each criticality tier may go unreviewed, anywhere from 7 to 1095 days.",
        bullets: [
          "Mark reviewed records that a person looked today",
          "The default review cadence is 90 days for every tier",
          "Dependencies stored once and read correctly from both ends",
          "Linked controls, risks, evidence, documents and vendors in one place",
        ],
        visual: {
          kind: "screenshot",
          name: "assets-settings",
          alt: "Asset settings with a review cadence for each criticality tier, critical, high, medium, low and not yet rated, each set to 90 days, and a custom fields section with an Add field button",
        },
      },
      {
        eyebrow: "Bring your list",
        title: "Start from the spreadsheet you already keep",
        text: "Download the template, upload your file, and Verity shows what it understood row by row, with errors called out before anything is created. Fix the sheet and upload again, or commit what parsed. If your organisation tracks something the inventory does not ask for, add a custom field.",
        bullets: [
          "Field types: text, long text, number, date, choice, yes/no",
          "Mark a field as required for every asset",
          "Archived fields keep last year's values readable",
          "Decommissioning closes the asset's open findings",
        ],
        visual: {
          kind: "screenshot",
          name: "dialog-custom-field",
          alt: "The Add a field dialog over asset settings, with a field name, a type of Text, optional helper text and a Required switch",
        },
      },
    ],
    capabilities: [
      { icon: "server", title: "Six asset types", text: "Applications, infrastructure, data, cloud resources, third parties and business services.", status: "live" },
      { icon: "gauge", title: "Derived criticality", text: "A score out of 10 and a tier, from CIA ratings and exposure.", status: "live" },
      { icon: "check", title: "Inventory hygiene", text: "Five field checks and a review clock on every record.", status: "live" },
      { icon: "tree", title: "Dependencies", text: "Record what runs on what, and see what else goes down.", status: "live" },
      { icon: "bug", title: "Vulnerabilities per asset", text: "Open findings listed on the asset, with new ones added in place.", status: "live" },
      { icon: "database", title: "Spreadsheet import", text: "A template, a row-by-row preview and errors flagged before anything is created.", status: "live" },
      { icon: "list", title: "Custom fields", text: "Six field types, optionally required, archived rather than deleted.", status: "live" },
      { icon: "cloud", title: "Asset discovery", text: "Cloud and discovery connections will keep the inventory in step with what runs.", status: "soon" },
      { icon: "laptop", title: "Device monitoring", text: "Daily checks that staff laptops are managed, encrypted and patched.", status: "soon" },
    ],
    related: ["vulnerability-management", "risk-management", "business-continuity", "device-monitoring"],
    docs: [
      { title: "Asset inventory", href: "/docs/assets/inventory/" },
      { title: "Hygiene and dependencies", href: "/docs/assets/hygiene-and-dependencies/" },
      { title: "Import assets", href: "/docs/assets/import-and-custom-fields/" },
    ],
    faqs: [
      {
        q: "Can we import our existing asset list?",
        a: "Yes. Download the template so your columns match, upload the file, and review what Verity read row by row, with errors called out before anything is created. Fix the sheet and upload again, or commit what parsed.",
      },
      {
        q: "How is criticality worked out?",
        a: "From the highest of the asset's confidentiality, integrity and availability ratings, raised for internet-facing assets, confidential or restricted data and high-impact business functions. The result is a score out of 10 and a tier. An asset with no rating has no tier, rather than a default of medium.",
      },
      {
        q: "Does Verity discover assets automatically?",
        a: "Not yet. Today you add assets by hand or import them from a spreadsheet. Connections that discover cloud resources and other systems are coming soon.",
      },
      {
        q: "What happens to an asset we stop using?",
        a: "Decommission it. That records the disposal and closes the asset's open findings, because a finding on a machine that no longer exists is noise.",
      },
    ],
  },
  {
    slug: "vulnerability-management",
    eyebrow: "Security",
    headline: "Fix the vulnerabilities that matter first, on time.",
    lead: "Import scanner exports or add findings by hand, and Verity ties each one to an asset and ranks it by what it means to you: severity, the likelihood of exploitation, known exploitation and the asset it sits on. Findings get a due date from their severity.",
    facts: [
      { label: "Critical, default window", value: "15 days" },
      { label: "High, default window", value: "30 days" },
      { label: "Medium, default window", value: "60 days" },
      { label: "Low, default window", value: "90 days" },
    ],
    heroVisual: { kind: "composition", name: "estate-dashboard" },
    sections: [
      {
        eyebrow: "Contextual priority",
        title: "A priority that reflects your estate, not just CVSS",
        text: "A CVSS score describes a weakness in the abstract. Verity weighs it with the EPSS probability of exploitation and the Known Exploited Vulnerabilities catalogue, then with the asset's criticality and whether it is internet-facing or customer-facing. A medium on your payment gateway can rightly outrank a high on a test box.",
        bullets: [
          "A finding on the KEV catalogue is never below P1",
          "Each risk score shows how it was calculated",
          "One definition, many findings: fix one host at a time",
          "Enter a CVE and Verity fills in the details",
        ],
        visual: {
          kind: "screenshot",
          name: "vulnerability-detail",
          alt: "A finding for Log4Shell on the Payments API Gateway, marked Critical, KEV and P1 with a risk score of 100, showing how the score was calculated from CVSS, exploit probability, known exploitation and the asset's criticality, and a Request exception option",
        },
      },
      {
        eyebrow: "Scanner imports",
        title: "Turn scanner output into a list someone can work",
        text: "Upload a scanner export of up to 10 MB as CSV, Excel or XML, including a Nessus file. Verity matches each row to an asset in your inventory, deduplicates against what is already open, and reports what it created, updated, resurfaced or could not match. Findings that come back after a fix are marked and counted.",
        bullets: [
          "Filter by severity, asset, exploit and flags",
          "States run from New through Pending retest to Fixed",
          "Fixed only after Verify fixed, from Pending retest",
          "Live scanner connections are coming soon",
        ],
        visual: {
          kind: "screenshot",
          name: "vulnerabilities-register",
          alt: "The vulnerability register, headed 10 open and 3 critical, with counts for open, overdue, known exploited and accepted findings, and rows showing each finding's CVE, CWE, severity, CVSS, EPSS, vector, asset and contextual priority",
        },
      },
      {
        eyebrow: "Remediation windows",
        title: "Remediation windows, and exceptions that expire",
        text: "Due dates come from severity: by default 15 days for critical, 30 for high, 60 for medium and 90 for low, with findings flagged in their last seven days. Overdue findings escalate. When a fix cannot land in time, request an exception for a set number of days, up to 365, that someone else approves.",
        bullets: [
          "A change to the windows applies only to new findings",
          "Exceptions state why, the potential risks and any compensating controls",
          "Remediation plans record proposal, approval and verification",
          "Custom fields for change tickets and maintenance windows",
        ],
        visual: {
          kind: "screenshot",
          name: "vulnerabilities-settings",
          alt: "Vulnerability settings with remediation windows of 15, 30, 60 and 90 days for critical, high, medium and low findings, no service level for informational ones, and a custom fields section",
        },
      },
    ],
    capabilities: [
      { icon: "target", title: "Contextual priority", text: "CVSS, EPSS and known exploitation, weighed with the asset's criticality and exposure.", status: "live" },
      { icon: "warning", title: "KEV floor", text: "A finding on the Known Exploited Vulnerabilities catalogue is floored at P1.", status: "live" },
      { icon: "funnel", title: "Scanner imports", text: "CSV, Excel and XML imports matched to assets and deduplicated against open findings.", status: "live" },
      { icon: "search", title: "CVE lookup", text: "Enter a CVE and the description, score, vector and threat intelligence fill in.", status: "live" },
      { icon: "clock", title: "Remediation windows", text: "Due dates by severity, flagged when due soon, with escalation when overdue.", status: "live" },
      { icon: "signature", title: "Time-boxed exceptions", text: "Up to 365 days, approved by someone other than the requester, then lapsing.", status: "live" },
      { icon: "scales", title: "Raise a risk", text: "Carry a finding into the risk register when it deserves one.", status: "live" },
      { icon: "list", title: "Custom fields", text: "Record change tickets, sign-offs and maintenance windows that scanners cannot know.", status: "live" },
      { icon: "detective", title: "Live scanner connections", text: "Connections to Tenable Nessus, Rapid7 Nexpose and Qualys are planned.", status: "soon" },
    ],
    related: ["asset-inventory", "risk-management", "continuous-monitoring", "workflows-and-approvals"],
    docs: [
      { title: "Findings and priority", href: "/docs/vulnerabilities/findings-and-priority/" },
      { title: "Import findings", href: "/docs/vulnerabilities/importing-findings/" },
      { title: "Remediation and exceptions", href: "/docs/vulnerabilities/remediation/" },
    ],
    faqs: [
      {
        q: "Which scanners can we import from?",
        a: "Upload an export as CSV, Excel or XML, including a Nessus file, or use the import template to shape your own. You can also add findings by hand. Direct connections to Tenable Nessus, Rapid7 Nexpose and Qualys are coming soon.",
      },
      {
        q: "Why is a medium CVSS finding ranked above a high one?",
        a: "Because priority reflects your estate. A medium weakness that is known to be exploited, on an internet-facing payment gateway, can matter more than a high one on a test machine. Each finding shows how its score was calculated.",
      },
      {
        q: "Can we change the remediation deadlines?",
        a: "Yes, in vulnerability settings. A change applies to findings detected from then on and does not silently move the due date on findings that already exist.",
      },
      {
        q: "What if a fix cannot be made in time?",
        a: "Request an exception for a set number of days, up to 365, stating why it is needed and what could go wrong. Someone other than the requester decides, and when the exception lapses the finding returns to the open register.",
      },
    ],
  },
  {
    slug: "continuous-monitoring",
    eyebrow: "Security",
    headline: "Hear when a control stops working, not at audit time.",
    lead: "Continuous monitoring will turn your connected systems into a standing watch on your controls. Checks will run on a schedule, every run will be kept, a failing check will open a finding that resolves itself when it passes, and the right people will be alerted.",
    heroVisual: {
      kind: "list",
      title: "Monitoring findings",
      icon: "pulse",
      rows: [
        { label: "Default branch is protected", meta: "payments-service repository", status: "Failing", tone: "danger" },
        { label: "Stored data is encrypted", meta: "Production account", status: "Passing", tone: "success" },
        { label: "Two factor is enforced", meta: "Identity provider", status: "Could not check", tone: "warning" },
        { label: "Backups run and are kept", meta: "Customer database", status: "Resolved", tone: "success" },
        { label: "Secret scanning is on", meta: "legacy-admin repository · waived until review", status: "Waived", tone: "pending" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Findings and alerts",
        title: "A finding for every failure, resolved when it passes",
        text: "A failing check will open a finding for the specific resource it failed on, so three unprotected repositories will mean three findings. When the check passes again, its finding will resolve itself. A control that moves to failing will raise an alert, so the people responsible hear about it without waiting for a review.",
        bullets: [
          "Every run kept, so controls show history across the audit window",
          "Waivers time-boxed, justified and approved by someone else",
          "Checks scoped to the repositories, accounts or tags that matter",
          "Exclusions will need a reason and will appear on the evidence",
        ],
        visual: {
          kind: "list",
          title: "Peer code review · daily history",
          icon: "chart-line",
          rows: [
            { label: "Today", meta: "Every repository protected", status: "Passing", tone: "success" },
            { label: "Yesterday", meta: "Finding resolved on the next pass", status: "Passing", tone: "success" },
            { label: "Two days ago", meta: "Branch protection removed on one repository", status: "Failing", tone: "danger" },
            { label: "Three days ago", meta: "Token expired, then reconnected", status: "Could not check", tone: "warning" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Error, not fail",
        title: "A broken connection will never look like a failed control",
        text: "When a check cannot read a system, because a token expired or permissions were reduced, it will record an error, not a failure. You will see that the check could not run, and why, rather than a red mark against a control that may be working perfectly well. GitHub checks already work this way.",
        bullets: [
          "Could not check is distinct from Failing, everywhere",
          "Connection health visible, with the reason it needs attention",
          "Checks will run only for controls in scope of a framework",
        ],
        visual: {
          kind: "list",
          title: "Connection health",
          icon: "plug",
          rows: [
            { label: "GitHub · engineering organisation", meta: "Last run this morning", status: "Healthy", tone: "success" },
            { label: "Amazon Web Services · production", meta: "Token expired", status: "Needs attention", tone: "warning" },
            { label: "Okta · staff directory", meta: "Connected today", status: "Waiting for first run", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "clock", title: "Scheduled checks", text: "Checks will run on a schedule across every system you connect.", status: "soon" },
      { icon: "flag", title: "Findings per resource", text: "One finding per failing check and resource, resolved automatically on the next pass.", status: "soon" },
      { icon: "bell", title: "Alerts", text: "A control moving to failing will alert the people responsible.", status: "soon" },
      { icon: "signature", title: "Waivers", text: "Time-boxed, justified and approved by someone other than the requester.", status: "soon" },
      { icon: "funnel", title: "Scoping and exclusions", text: "Checks scoped by repository, account or tag; exclusions will need a reason.", status: "soon" },
      { icon: "chart-line", title: "History across the window", text: "Every run will be kept, so each control shows its record over the audit period.", status: "soon" },
      { icon: "cloud", title: "More connections", text: "Cloud, identity, ticketing and observability systems added to the checks.", status: "soon" },
      { icon: "chat", title: "Jira and Slack", text: "Two-way ticket sync with Jira and alerts posted to Slack.", status: "soon" },
    ],
    related: ["integrations", "compliance-automation", "evidence-management", "device-monitoring"],
    docs: [
      { title: "Continuous monitoring", href: "/docs/monitoring/continuous-monitoring/" },
      { title: "Automated checks", href: "/docs/compliance/automated-checks/" },
      { title: "How connections work", href: "/docs/integrations/overview/" },
    ],
    faqs: [
      {
        q: "Do any checks run today?",
        a: "Yes. Connect GitHub and seven checks read your repositories every day, attaching their results to the controls they support as dated evidence. Continuous monitoring will add findings, alerts, waivers and more systems on top.",
      },
      {
        q: "What happens when a connected system cannot be read?",
        a: "The check records that it could not check, never a failure. A broken connection must never look like a failed control, and that already holds for the GitHub checks that run today.",
      },
      {
        q: "How will we hear about a failure?",
        a: "A control that moves to failing will raise an alert, and the failing check will open a finding for the affected resource. Slack alerts and two-way Jira sync are also planned.",
      },
    ],
    today: [
      { title: "Connect GitHub", text: "Seven checks run daily and attach dated results to mapped controls.", href: "/platform/integrations/" },
      { title: "Read results on a control", text: "The Automation tab shows what ran, when and what it found.", href: "/docs/compliance/automated-checks/" },
      { title: "Track fixes as tasks", text: "Raise a task for each failing result until findings arrive.", href: "/platform/workflows-and-approvals/" },
    ],
  },
  {
    slug: "device-monitoring",
    eyebrow: "Security",
    headline: "Prove every staff laptop is managed and protected.",
    lead: "Laptops carry your data out of the building. Device monitoring will check, every day, that each staff laptop is enrolled in device management, encrypted, locked when idle, patched, wipeable and protected, and attach the results to the endpoint controls already in your library.",
    heroVisual: {
      kind: "list",
      title: "Laptop fleet",
      icon: "laptop",
      rows: [
        { label: "MBP-ENG-014 · Omar Siddiqui", meta: "Engineering", status: "Compliant", tone: "success" },
        { label: "LT-FIN-007 · Grace Liu", meta: "Disk encryption off", status: "Failing", tone: "danger" },
        { label: "LT-OPS-022 · Tom Becker", meta: "Operating system out of date", status: "Failing", tone: "danger" },
        { label: "MBP-SAL-031 · Amina Yusuf", meta: "Not reporting to device management", status: "Could not check", tone: "warning" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Daily checks",
        title: "The checks auditors ask about, on every laptop",
        text: "Five checks will read from your device management system: laptops are enrolled, disks are encrypted, screens lock when idle, operating systems are patched and lost laptops can be wiped. A sixth will read from your endpoint protection system to confirm a protection agent is running on laptops and servers.",
        bullets: [
          "Enrolled, encrypted, screen lock, patched and remote wipe",
          "Endpoint protection running on laptops and servers",
          "Results will attach to endpoint controls as dated evidence",
        ],
        visual: {
          kind: "list",
          title: "Device checks",
          icon: "list",
          rows: [
            { label: "Laptops are managed", meta: "Device management", status: "Passing", tone: "success" },
            { label: "Laptop disks are encrypted", meta: "Device management", status: "Failing", tone: "danger" },
            { label: "Screens lock when idle", meta: "Device management", status: "Passing", tone: "success" },
            { label: "Operating systems are patched", meta: "Device management", status: "Failing", tone: "danger" },
            { label: "Lost laptops can be wiped", meta: "Device management", status: "Passing", tone: "success" },
            { label: "Endpoint protection is running", meta: "Endpoint protection", status: "Could not check", tone: "warning" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Act on results",
        title: "Every failing laptop named, with what to fix",
        text: "A failing check will name the laptops that need attention and what to do, such as enrolling them, pushing the screen lock setting or updating them. A laptop the check cannot read will show as could not check, never as a failure, so a reporting gap is not mistaken for a failed control.",
        bullets: [
          "Guidance on what to fix with every failing laptop",
          "Could not check will never show as a failure",
          "Will read from the device management you already use",
        ],
        visual: {
          kind: "list",
          title: "Laptops needing attention",
          icon: "warning",
          rows: [
            { label: "LT-FIN-007", meta: "Turn on full disk encryption", status: "Failing", tone: "danger" },
            { label: "LT-OPS-022", meta: "Update to a supported operating system", status: "Failing", tone: "danger" },
            { label: "MBP-SAL-031", meta: "Not reporting; check its enrolment", status: "Could not check", tone: "warning" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "laptop", title: "Enrolment check", text: "Every company laptop enrolled in device management.", status: "soon" },
      { icon: "lock", title: "Disk encryption", text: "Full disk encryption turned on for every managed laptop.", status: "soon" },
      { icon: "desktop", title: "Screen lock", text: "Screens that lock after the idle time your policy sets.", status: "soon" },
      { icon: "check", title: "Operating system patches", text: "A supported, patched operating system on every managed laptop.", status: "soon" },
      { icon: "key", title: "Remote wipe", text: "Confirmation that every managed laptop can be locked and wiped remotely.", status: "soon" },
      { icon: "shield", title: "Endpoint protection", text: "A healthy, up-to-date protection agent on laptops and servers.", status: "soon" },
      { icon: "folder", title: "Evidence on controls", text: "Results will attach to the endpoint controls as dated evidence.", status: "soon" },
    ],
    related: ["asset-inventory", "continuous-monitoring", "integrations", "access-reviews"],
    docs: [
      { title: "Device monitoring", href: "/docs/monitoring/device-monitoring/" },
      { title: "Evidence", href: "/docs/compliance/evidence/" },
      { title: "How connections work", href: "/docs/integrations/overview/" },
    ],
    faqs: [
      {
        q: "Will Verity install software on our laptops?",
        a: "Device monitoring is planned to read from the device management and endpoint protection systems your company already uses, rather than from an agent of its own.",
      },
      {
        q: "Which device management systems will it support?",
        a: "Supported systems have not been announced. Tell us which one you use with the request option on the Connections page, so it can be taken into account.",
      },
      {
        q: "How do we prove device controls today?",
        a: "The endpoint controls are already in your library. Give them owners and attach an export from your device management or endpoint protection console as evidence. A configuration export is valid for 90 days by default.",
      },
    ],
    today: [
      { title: "Prove endpoint controls with evidence", text: "Attach console exports to the endpoint controls already in your library.", href: "/platform/evidence-management/" },
      { title: "Record the fleet as assets", text: "Keep laptops in the inventory with owners and criticality.", href: "/platform/asset-inventory/" },
      { title: "Request your device management system", text: "Tell us which system you use from the Connections page.", href: "/docs/integrations/overview/" },
    ],
  },
  {
    slug: "access-reviews",
    eyebrow: "Security",
    headline: "Confirm who should still have access, on the record.",
    lead: "Access reviews will ask one question on a schedule: should each of these people still have this access? Reviews will start from the live user list in your identity provider, reviewers will confirm or revoke each person's access, and every decision will be written to the audit log.",
    heroVisual: {
      kind: "list",
      title: "Access review · production cloud",
      icon: "user-check",
      rows: [
        { label: "Hamza Qureshi", meta: "Platform engineering · administrator", status: "Confirmed", tone: "success" },
        { label: "Ella Morgan", meta: "Left the company", status: "Revoked", tone: "danger" },
        { label: "Rui Santos", meta: "Data team · read only", status: "Pending", tone: "pending" },
        { label: "Nadia Rahman", meta: "Support · moved teams", status: "Pending", tone: "pending" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Periodic reviews",
        title: "Every review will start from the live user list",
        text: "Instead of a stale spreadsheet, each review will start from the current users and groups exported from your identity provider. Reviewers will move group by group, confirming or revoking each person's access, and a completed review will stand as evidence for the access controls that expect one.",
        bullets: [
          "Periodic reviews from your identity provider's users and groups",
          "Confirm or revoke, with every decision in the audit log",
          "Evidence for access review, privileged access and removal controls",
        ],
        visual: {
          kind: "list",
          title: "Review by group",
          icon: "users",
          rows: [
            { label: "Production administrators", meta: "Security Officer reviewing", status: "Complete", tone: "success" },
            { label: "Finance systems", meta: "Business Operations Lead reviewing", status: "In progress", tone: "progress" },
            { label: "Customer data read access", meta: "Privacy Officer reviewing", status: "Not started", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Identity checks",
        title: "Identity provider checks that will run alongside reviews",
        text: "When you connect an identity provider, checks will run between reviews: few administrators, access granted through role groups, two-factor sign-in enforced, connected apps known and access lists exported for review each week. As with every check, a connection that cannot be read will show an error, never a failure.",
        bullets: [
          "Okta, Google Workspace, and Microsoft 365 and Entra ID planned",
          "Access requests checked against approved tickets",
          "Could not check will never show as a failure",
        ],
        visual: {
          kind: "list",
          title: "Identity checks",
          icon: "fingerprint",
          rows: [
            { label: "Few administrators", meta: "Identity provider", status: "Passing", tone: "success" },
            { label: "Access comes from roles", meta: "Identity provider", status: "Failing", tone: "danger" },
            { label: "Two factor is enforced", meta: "Identity provider", status: "Passing", tone: "success" },
            { label: "Access lists export for review", meta: "Identity provider · weekly", status: "Passing", tone: "success" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "calendar", title: "Periodic reviews", text: "Reviews that will come round on a schedule, from the live user list.", status: "soon" },
      { icon: "user-check", title: "Confirm or revoke", text: "Reviewers will decide on each person's access, one group at a time.", status: "soon" },
      { icon: "scroll", title: "Decisions on record", text: "Who decided what, and when, written to the audit log.", status: "soon" },
      { icon: "fingerprint", title: "Identity provider checks", text: "Administrators, role-based access, two-factor and connected apps, checked regularly.", status: "soon" },
      { icon: "folder", title: "Evidence for access controls", text: "Completed reviews will stand as evidence for the controls that expect them.", status: "soon" },
      { icon: "users", title: "Group by group", text: "Reviews organised around identity provider groups and Verity roles.", status: "soon" },
    ],
    related: ["integrations", "continuous-monitoring", "compliance-automation", "workflows-and-approvals"],
    docs: [
      { title: "Access reviews", href: "/docs/monitoring/access-reviews/" },
      { title: "People and invitations", href: "/docs/admin/people/" },
      { title: "How connections work", href: "/docs/integrations/overview/" },
    ],
    faqs: [
      {
        q: "Can we run access reviews in Verity today?",
        a: "Not as a dedicated workflow yet. You can run one by hand: raise a task for the review, record the sign-off and attach it to the periodic access review control as evidence.",
      },
      {
        q: "Which identity providers will it work with?",
        a: "Okta, Google Workspace, and Microsoft 365 and Entra ID are the identity providers planned for connection.",
      },
      {
        q: "How does Verity control access to itself today?",
        a: "Six built-in roles, custom roles with granular permissions, groups, and a setting that requires two-factor sign-in for admins. External auditors can be given access windows that close on their own, and a departing person's membership is disabled rather than deleted.",
      },
    ],
    today: [
      { title: "Run a review by hand", text: "Track it as a task and attach the sign-off as evidence.", href: "/platform/workflows-and-approvals/" },
      { title: "Time-boxed auditor access", text: "Give external auditors access windows that close on their own.", href: "/docs/admin/people/" },
      { title: "Roles and groups", text: "Built-in and custom roles, and groups, for your own workspace.", href: "/docs/admin/roles-and-groups/" },
    ],
  },
  {
    slug: "security-awareness-training",
    eyebrow: "Security",
    headline: "Show who has completed security training, and when.",
    lead: "Security awareness training will let you assign training to the people who need it, track who has completed it, and keep that completion as evidence for the controls that ask for it, in the same workspace as your policies and their acknowledgements.",
    heroVisual: {
      kind: "list",
      title: "Annual security awareness",
      icon: "graduation",
      rows: [
        { label: "Engineering", meta: "Assigned by group", status: "Complete", tone: "success" },
        { label: "Finance", meta: "Assigned by group", status: "In progress", tone: "progress" },
        { label: "Customer support", meta: "Assigned by group", status: "Overdue", tone: "danger" },
        { label: "Executive team", meta: "Assigned by role", status: "Not started", tone: "neutral" },
      ],
      note: "Concept · coming soon",
    },
    sections: [
      {
        eyebrow: "Assign and track",
        title: "Training assigned and completion tracked, person by person",
        text: "You will assign security awareness training to the people who need it and see, person by person, who has completed it and who is still outstanding. Completion will be kept with a name and a date, in the same workspace as your policies and the acknowledgements behind them.",
        bullets: [
          "Training assigned to the people who need it",
          "Completion tracked person by person",
          "Completion kept with a name and a date",
        ],
        visual: {
          kind: "list",
          title: "Training completion",
          icon: "users",
          rows: [
            { label: "Aisha Khan", meta: "Finance", status: "Completed", tone: "success" },
            { label: "Ben Carter", meta: "Engineering", status: "Completed", tone: "success" },
            { label: "Chen Wei", meta: "Customer support", status: "Outstanding", tone: "warning" },
            { label: "Dimitri Petrov", meta: "Operations", status: "Not started", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "Audit evidence",
        title: "Training completion that will count as audit evidence",
        text: "Auditors ask for proof that staff were trained, not just that a course exists. Completion records will stand as evidence for the security awareness training control in your library, next to the policy acknowledgements that show staff read the rules, so the answer is a record rather than a hunt through email.",
        bullets: [
          "Completion attached to the training control as evidence",
          "Alongside policy acknowledgements, which are live today",
          "Training records are already an evidence type today",
        ],
        visual: {
          kind: "list",
          title: "Evidence for security awareness training",
          icon: "folder",
          rows: [
            { label: "Annual security awareness · completion", meta: "Training record", status: "Current", tone: "success" },
            { label: "Information security policy · acknowledgements", meta: "Campaign record", status: "Current", tone: "success" },
            { label: "New joiner security induction · completion", meta: "Training record", status: "Aging", tone: "warning" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "graduation", title: "Assign training", text: "You will assign security awareness training to the people who need it.", status: "soon" },
      { icon: "list", title: "Completion tracking", text: "You will see, person by person, who has completed training and who has not.", status: "soon" },
      { icon: "folder", title: "Completion as evidence", text: "Completion kept as evidence for the controls that call for training.", status: "soon" },
      { icon: "scroll", title: "Named and dated", text: "Every completion recorded with the person's name and the date.", status: "soon" },
      { icon: "signature", title: "Beside acknowledgements", text: "Training records next to the policy acknowledgements staff already sign.", status: "soon" },
      { icon: "stack", title: "One workspace", text: "Training tracked in the same workspace as your policies and controls.", status: "soon" },
    ],
    related: ["policy-management", "evidence-management", "compliance-automation", "workflows-and-approvals"],
    docs: [
      { title: "Security awareness training", href: "/docs/roadmap/security-awareness-training/" },
      { title: "Acknowledgement campaigns", href: "/docs/policies/acknowledgement-campaigns/" },
      { title: "Evidence", href: "/docs/compliance/evidence/" },
    ],
    faqs: [
      {
        q: "Will Verity provide training courses?",
        a: "The planned focus is assigning training, tracking completion and keeping that completion as evidence. Built-in course content has not been announced.",
      },
      {
        q: "How do we evidence training today?",
        a: "Upload completion records as evidence of the training record type, valid for a year by default, and attach them to the security awareness training control already in your library. Use acknowledgement campaigns to show that staff have read your security policies.",
      },
      {
        q: "Is this the same as policy acknowledgement?",
        a: "No. Acknowledgement campaigns, which are live, ask people to read and sign a published policy. Training will track completion of security awareness training. Both will sit side by side as evidence.",
      },
    ],
    today: [
      { title: "Run acknowledgement campaigns", text: "Ask people, roles and groups to read and sign a policy.", href: "/platform/policy-management/" },
      { title: "Upload training records as evidence", text: "Training records are valid for a year by default.", href: "/platform/evidence-management/" },
      { title: "Own the training control", text: "Security awareness training is already a control in your library.", href: "/platform/compliance-automation/" },
    ],
  },

  // ------------------------------------------------------------------ Platform
  {
    slug: "integrations",
    eyebrow: "Platform",
    headline: "Your systems checked daily, with the proof attached.",
    lead: "Connect GitHub with a read-only token and seven checks run every day on how your software is reviewed, protected and released. Results attach to the controls they map to as dated evidence, and a broken connection shows as an error, never as a failed control.",
    facts: [
      { label: "Live connector", value: "GitHub" },
      { label: "GitHub checks, run daily", value: "7" },
      { label: "Token access needed", value: "Read only" },
    ],
    heroVisual: {
      kind: "screenshot",
      name: "connections",
      alt: "The Connections page, with GitHub ready to connect, systems such as Amazon Web Services, Cloudflare, Okta, Microsoft Entra ID, Google Workspace, GitLab, Bitbucket, Jira and Slack not yet available, and a Request integration button",
    },
    sections: [
      {
        eyebrow: "Connect GitHub",
        title: "Seven checks on how your software is built and released",
        text: "Paste a personal access token that can only read your GitHub organisation. Verity encrypts it before it is stored and keeps it out of every log. The first run starts at once, then the checks run daily, answering questions a SOC 2 auditor asks about reviews, branch protection and scanning.",
        bullets: [
          "Default branch protected; an approving review required before merge",
          "Merged changes reviewed; checks must pass before merge",
          "Secret scanning and dependency alerts switched on",
          "Two-factor sign-in required for access to code",
        ],
        visual: {
          kind: "list",
          title: "GitHub checks",
          icon: "code",
          rows: [
            { label: "Default branch is protected", meta: "Daily · SD-06, SD-01", status: "Passing", tone: "success" },
            { label: "Merges need an approving review", meta: "Daily · SD-06, SD-01", status: "Passing", tone: "success" },
            { label: "Merged changes were reviewed", meta: "Daily · SD-01, SD-06", status: "Failing", tone: "danger" },
            { label: "Checks must pass before merge", meta: "Daily · SD-02", status: "Passing", tone: "success" },
            { label: "Secret scanning is on", meta: "Daily · SD-11", status: "Passing", tone: "success" },
            { label: "Dependency alerts are on", meta: "Daily · SD-03, LM-11", status: "Could not check", tone: "warning" },
            { label: "Two factor is required for code access", meta: "Daily · IAM-03", status: "Passing", tone: "success" },
          ],
          note: "The seven live checks · sample results",
        },
      },
      {
        eyebrow: "On the control",
        title: "Results land on the controls they answer",
        text: "Each check maps to the controls it can support. Open a control's Automation tab to see what ran, when and what it found. The output is attached to the control as dated evidence, at most once a day unless the result changes, so a passing check does not bury the record in copies.",
        bullets: [
          "Results read Passing, Failing or Could not check",
          "A broken connection shows Needs attention, with the reason",
          "Checks stop rather than quietly report a pass",
        ],
        visual: {
          kind: "screenshot",
          name: "control-detail",
          alt: "A control's detail page with an Automation panel offering to connect the system its checks need, linked evidence marked Current, and the control's SOC 2 mappings",
        },
      },
      {
        eyebrow: "What comes next",
        title: "Cloud, identity and ticketing connections are on the way",
        text: "GitHub is the first live connector. Connections for cloud infrastructure, identity providers, ticketing, alerting, observability and vulnerability scanners are planned, each designed around read-only, least-privilege access. If the system you rely on is not listed, request it from the Connections page so it can be prioritised.",
        bullets: [
          "Amazon Web Services and other cloud platforms",
          "Okta, Google Workspace, and Microsoft 365 and Entra ID",
          "Jira, Slack, PagerDuty, Datadog and more",
          "Request integration records what you need",
        ],
        visual: {
          kind: "list",
          title: "Planned connections",
          icon: "plug",
          rows: [
            { label: "Amazon Web Services", meta: "Cloud infrastructure", status: "Coming soon", tone: "pending" },
            { label: "Okta", meta: "Identity provider", status: "Coming soon", tone: "pending" },
            { label: "Google Workspace", meta: "Identity provider", status: "Coming soon", tone: "pending" },
            { label: "Microsoft 365 and Entra ID", meta: "Identity provider", status: "Coming soon", tone: "pending" },
            { label: "Jira", meta: "Ticketing", status: "Coming soon", tone: "pending" },
            { label: "Slack", meta: "On call and alerting", status: "Coming soon", tone: "pending" },
          ],
          note: "Planned · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "code", title: "GitHub connector", text: "Seven daily checks on reviews, branch protection, scanning and two-factor sign-in.", status: "live" },
      { icon: "key", title: "Read-only tokens", text: "Nothing in Verity needs write access to your source control.", status: "live" },
      { icon: "lock", title: "Encrypted credentials", text: "Tokens encrypted before they are stored, and kept out of logs.", status: "live" },
      { icon: "folder", title: "Evidence on controls", text: "Dated results attached to mapped controls, at most once a day unless changed.", status: "live" },
      { icon: "warning", title: "Error is not fail", text: "A broken connection shows Needs attention; checks never report a pass they did not see.", status: "live" },
      { icon: "chat", title: "Request a system", text: "Register interest in a system that is not there yet, so it can be prioritised.", status: "live" },
      { icon: "cloud", title: "Cloud infrastructure", text: "Amazon Web Services, Microsoft Azure, Google Cloud and other platforms.", status: "soon" },
      { icon: "fingerprint", title: "Identity providers", text: "Okta, Google Workspace, and Microsoft 365 and Entra ID.", status: "soon" },
      { icon: "bell", title: "Ticketing and alerting", text: "Jira, Linear and others for work; PagerDuty and Slack for alerts.", status: "soon" },
    ],
    related: ["compliance-automation", "evidence-management", "continuous-monitoring", "device-monitoring"],
    docs: [
      { title: "How connections work", href: "/docs/integrations/overview/" },
      { title: "Connect GitHub", href: "/docs/integrations/github/" },
      { title: "Automated checks", href: "/docs/compliance/automated-checks/" },
    ],
    faqs: [
      {
        q: "What access does the GitHub connection need?",
        a: "Read only. Create a personal access token that can read the organisation you want checked. Nothing in Verity needs to write to your source control, and a read-only token limits what a mistake can cost. Verity encrypts the token before it is stored, and it never appears in a log.",
      },
      {
        q: "Does a failing check mean our control failed?",
        a: "Not necessarily. A failing check found something other than what the control claims, and its detail says what. A check that could not run reads Could not check, never Failing, so a broken connection never looks like a failed control.",
      },
      {
        q: "What happens if our token expires?",
        a: "The connection shows Needs attention with the reason, and the checks stop rather than report a pass. Disconnect and connect again with a fresh token, and the schedule resumes.",
      },
      {
        q: "When will AWS and our identity provider be supported?",
        a: "They are planned, and we do not give dates. Each planned system is marked Coming soon here and on the Connections page. If yours is missing, request it so it can be prioritised.",
      },
    ],
  },
  {
    slug: "workflows-and-approvals",
    eyebrow: "Platform",
    headline: "Work assigned, on time and signed off on the record.",
    lead: "Everything in Verity eventually becomes work: collect this evidence, fix that finding, update the policy. Tasks and issues give work an owner, a due date and, where one applies, a service level, and approvals across the platform make sure decisions are made by the right person, on the record.",
    facts: [
      { label: "Task states", value: "6" },
      { label: "Task categories", value: "7" },
      { label: "Corrective action types", value: "4" },
      { label: "Severity matrix", value: "3 × 3" },
    ],
    heroVisual: {
      kind: "screenshot",
      name: "tasks-register",
      alt: "The tasks and issues register with 17 open items, filters for type, status, priority, category and assignee, and a side panel previewing a critical task to patch Log4j on the payments gateway with its status, SLA, owner and due date",
    },
    sections: [
      {
        eyebrow: "Tasks and issues",
        title: "Planned work and things that broke, in one register",
        text: "A task is planned work with an owner and a due date. An issue is something that went wrong: it carries a severity and holds containment, corrective, preventive and verification actions, each with its own owner and state. That trail shows an auditor you noticed, acted and checked the fix.",
        bullets: [
          "Owners are accountable; assignees do the work",
          "Sub-tasks, comments and related records on every task",
          "Every transition recorded with the person and the time",
          "Promote a corrective action to a task of its own",
        ],
        visual: {
          kind: "screenshot",
          name: "task-detail",
          alt: "A task's detail page for patching Log4j on the payments gateway, showing its status, critical priority, SLA, owner and due date, tabs for sub-tasks, related records, comments and activity, and its assignees and details",
        },
      },
      {
        eyebrow: "Service levels",
        title: "Service levels that turn a promise into a number",
        text: "A service level is a promise about how quickly work of a given priority gets done. Administrators set the targets and a severity matrix that combines impact and urgency. The overview shows what is on track, due soon and breaching now, so you can show how quickly you fix things.",
        bullets: [
          "Open work by priority, age and assignee",
          "Mean time to resolve, from your own data",
          "Respond and resolve targets for each severity",
        ],
        visual: {
          kind: "screenshot",
          name: "tasks-overview",
          alt: "The tasks Overview tab, with counts of open, breaching, due-soon and recently closed work, a service level posture chart, open work by priority and by age, and load by assignee",
        },
      },
      {
        eyebrow: "Approvals and history",
        title: "Decisions made by the right person, on the record",
        text: "Approvals run through the platform: policies in tiers, risk acceptances, vulnerability exceptions and the vendor approval gate. Where it matters, the person who asks cannot be the person who approves. Decisions waiting on you appear in your notifications, and every one lands in the append-only audit log.",
        bullets: [
          "Separation of duties on acceptances, exceptions and vendor approval",
          "The bell lists approvals waiting on you",
          "Nobody can edit or delete the audit log, administrators included",
          "Configurable multi-step approval workflows are coming soon",
        ],
        visual: {
          kind: "screenshot",
          name: "audit-log",
          alt: "The audit log, filterable by user type, action and object type, listing each create and update with who made it and a plain-language description of the change",
        },
      },
    ],
    capabilities: [
      { icon: "kanban", title: "Tasks and issues", text: "One register for planned work and for things that went wrong.", status: "live" },
      { icon: "first-aid", title: "Corrective actions", text: "Containment, corrective, preventive and verification actions under each issue.", status: "live" },
      { icon: "clock", title: "Service levels", text: "Targets by priority, with on-track, due-soon and breached work counted.", status: "live" },
      { icon: "scales", title: "Severity matrix", text: "Impact and urgency combine into a severity with respond and resolve targets.", status: "live" },
      { icon: "stamp", title: "Approvals", text: "Sign-off on policies, acceptances, exceptions and vendors, by the right person.", status: "live" },
      { icon: "scroll", title: "Append-only history", text: "Every transition and decision in the audit log, which nobody can edit.", status: "live" },
      { icon: "bell", title: "Notifications", text: "The bell lists tasks near breach, approvals to decide and policies to sign.", status: "live" },
      { icon: "tree", title: "Approval workflows", text: "Multi-step sign-off, in sequence or in parallel, with escalation on timeout.", status: "soon" },
      { icon: "link", title: "Jira and Slack", text: "Two-way sync with Jira and alerts posted to Slack.", status: "soon" },
    ],
    related: ["policy-management", "risk-management", "third-party-risk", "vulnerability-management"],
    docs: [
      { title: "Tasks and issues", href: "/docs/tasks/overview/" },
      { title: "Service levels and approvals", href: "/docs/tasks/service-levels-and-approvals/" },
      { title: "Audit log and isolation", href: "/docs/admin/audit-log-and-isolation/" },
    ],
    faqs: [
      {
        q: "What is the difference between a task and an issue?",
        a: "A task is planned work with an owner and a due date. An issue is something that went wrong: it carries a severity and can hold containment, corrective, preventive and verification actions underneath it.",
      },
      {
        q: "Who can approve a decision?",
        a: "It depends on the decision. Policy approval tiers can name a person, a role or a group. Risk acceptances, vulnerability exceptions and vendor approvals must be decided by someone other than the person who asked.",
      },
      {
        q: "Can we sync tasks with Jira or Slack?",
        a: "Not yet. Two-way Jira sync and Slack alerts are coming soon. Today, work is assigned, tracked and closed in Verity, and assignees are notified there.",
      },
      {
        q: "Can anyone change the history?",
        a: "No. The audit log is append only: nobody can edit or delete it, administrators included, and that is enforced by the database rather than by convention.",
      },
    ],
  },
  {
    slug: "ai-assistant",
    eyebrow: "Platform",
    headline: "AI that drafts the work, and people who decide.",
    lead: "The Verity assistant will answer plain-language questions about your programme, draft policies, procedures, guidelines and standards, turn scan reports into findings you review, and propose mitigation plans. Everything it produces will be marked as an AI draft, and a person will review and approve it.",
    heroVisual: { kind: "composition", name: "assistant-draft" },
    sections: [
      {
        eyebrow: "Ask and draft",
        title: "Ask Verity about your programme, in plain language",
        text: "You will ask questions such as which high risks have no owner, or which controls lack current evidence, and get answers from your own records. Ask for a policy, procedure, guideline or standard and you will get a draft, marked as an AI draft, that goes through the same approval as anything a person writes.",
        bullets: [
          "Plain-language questions answered from your own records",
          "Drafts of policies, procedures, guidelines and standards",
          "Every draft marked as an AI draft",
          "The same review and approval as human-written content",
        ],
        visual: {
          kind: "list",
          title: "Ask Verity",
          icon: "chat",
          rows: [
            { label: "Which high risks have no owner?", meta: "Answered from the risk register", status: "Answered", tone: "success" },
            { label: "Which controls lack current evidence?", meta: "Answered from controls and evidence", status: "Answered", tone: "success" },
            { label: "Draft an incident response procedure", meta: "Waiting for a reviewer", status: "AI draft", tone: "pending" },
          ],
          note: "Concept · coming soon",
        },
      },
      {
        eyebrow: "People decide",
        title: "AI never approves, publishes, closes or rescores",
        text: "Scan reports will be parsed into a set of proposed findings that a person confirms before any are created. Mitigation plans will arrive as drafts for the normal approval. AI will never approve, publish, close a finding or change a score, every prompt and output will be logged, and the manual path will always be there.",
        bullets: [
          "Scan reports parsed into findings a person confirms",
          "Mitigation proposals will go through the normal approval",
          "Prompts and outputs logged, so any draft is traceable",
          "If AI is unavailable, you will work exactly as before",
        ],
        visual: {
          kind: "list",
          title: "Proposed findings from a scan report",
          icon: "bug",
          rows: [
            { label: "Apache Log4j2 remote code execution", meta: "Payments API Gateway", status: "Confirmed", tone: "success" },
            { label: "OpenSSL X.509 denial of service", meta: "Analytics Warehouse", status: "Awaiting confirmation", tone: "pending" },
            { label: "curl SOCKS5 heap buffer overflow", meta: "No matching asset", status: "Awaiting confirmation", tone: "pending" },
            { label: "Duplicate of an open finding", meta: "Corporate VPN Concentrator", status: "Dismissed", tone: "neutral" },
          ],
          note: "Concept · coming soon",
        },
      },
    ],
    capabilities: [
      { icon: "chat", title: "Ask Verity", text: "Plain-language questions about your controls, risks, vendors and findings.", status: "soon" },
      { icon: "file", title: "Document drafting", text: "Policies, procedures, guidelines and standards drafted for your review.", status: "soon" },
      { icon: "bug", title: "Scan report parsing", text: "Reports turned into proposed findings that a person will confirm.", status: "soon" },
      { icon: "lightbulb", title: "Mitigation proposals", text: "Draft treatment plans from a risk, its controls and its incidents.", status: "soon" },
      { icon: "sparkle", title: "Marked as AI draft", text: "AI content will carry its origin through its whole lifecycle.", status: "soon" },
      { icon: "user-check", title: "Human approval", text: "No AI output will approve, publish, close or rescore anything on its own.", status: "soon" },
      { icon: "scroll", title: "Logged and traceable", text: "Prompts and outputs logged with the person, model and version.", status: "soon" },
      { icon: "lifebuoy", title: "Manual path always", text: "An AI outage will never stop anyone writing their own policy.", status: "soon" },
    ],
    related: ["policy-management", "vulnerability-management", "enterprise-risk-management", "questionnaire-automation"],
    docs: [
      { title: "AI assistant and drafting", href: "/docs/roadmap/ai-assistant/" },
      { title: "Key concepts", href: "/docs/get-started/key-concepts/" },
      { title: "Approve and publish", href: "/docs/policies/approval-and-publishing/" },
    ],
    faqs: [
      {
        q: "Will AI make compliance decisions for us?",
        a: "No. AI will draft and suggest. It will never mark a control passing, close a finding, approve evidence, change a risk score, or approve or publish a document. A person decides every time.",
      },
      {
        q: "How will we know what AI wrote?",
        a: "AI-authored content will be marked as an AI draft and keep that mark through its lifecycle, so you and your auditor can always tell what was machine-generated. Prompts and outputs will be logged.",
      },
      {
        q: "Will our data be sent to an AI provider?",
        a: "Not without an explicit, documented decision, made after the provider's data-handling terms have been confirmed. Talk to us about your requirements.",
      },
      {
        q: "Does Verity use AI anywhere today?",
        a: "Only as drafts. Where an AI model is configured, AI Assist can propose a starting draft for a new risk, and evidence mapping suggestions can come from the model. Without one, both fall back to non-AI methods, and nothing is applied until a person chooses to use it.",
      },
    ],
    today: [
      { title: "Draft from 15 policy templates", text: "Complete drafts in your organisation's name, ready to edit.", href: "/platform/policy-management/" },
      { title: "Import scanner findings", text: "Scanner exports matched to assets and deduplicated.", href: "/docs/vulnerabilities/importing-findings/" },
      { title: "AI Assist on new risks", text: "A proposed starting draft, applied only when you choose.", href: "/docs/risk/risk-register/" },
    ],
  },
];
