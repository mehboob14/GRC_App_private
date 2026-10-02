import type { Framework } from "./frameworks";

/**
 * Framework catalog. Names, issuers and versions were checked on 2026-10-02
 * against official sources (sbp.org.pk, rulebook.centralbank.ae, apra.gov.au,
 * cyber.gov.au, eur-lex.europa.eu, iso.org, nist.gov and others). Only SOC 2
 * ships today; every other library is coming soon. Recheck before relying on
 * a version for anything other than orientation.
 */
export const frameworks: Framework[] = [
  {
    "id": "iso-27001",
    "name": "ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection — Information security management systems — Requirements",
    "shortName": "ISO 27001",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "security",
      "audit-reporting"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2022 (incl. Amendment 1:2024, climate action); 2013-edition certificates lapsed 31 Oct 2025",
    "type": "standard",
    "summary": "Certifiable requirements for an information security management system: risk assessment, risk treatment, leadership commitment, internal audit and continual improvement, with Annex A controls.",
    "whoItsFor": "Any organisation wanting independently certified information security; widely requested by banks and enterprise buyers.",
    "status": "soon"
  },
  {
    "id": "iso-27002",
    "name": "ISO/IEC 27002:2022 Information security, cybersecurity and privacy protection — Information security controls",
    "shortName": "ISO 27002",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2022",
    "type": "standard",
    "summary": "Guidance on 93 information security controls grouped into organisational, people, physical and technological themes; the reference set behind ISO 27001 Annex A.",
    "whoItsFor": "Security teams selecting and implementing controls, whether or not pursuing ISO 27001 certification.",
    "status": "soon"
  },
  {
    "id": "iso-27701",
    "name": "ISO/IEC 27701:2025 Information security, cybersecurity and privacy protection — Privacy information management systems — Requirements and guidance",
    "shortName": "ISO 27701",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "privacy",
      "audit-reporting"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas"
    ],
    "version": "2025 (second edition, Oct 2025; now a standalone management system standard)",
    "type": "standard",
    "summary": "Certifiable privacy information management system for PII controllers and processors; the 2025 edition no longer requires ISO 27001 as a prerequisite.",
    "whoItsFor": "Organisations processing personal data that want certifiable evidence of privacy governance (e.g., GDPR, PDPL).",
    "status": "soon"
  },
  {
    "id": "iso-27017",
    "name": "ISO/IEC 27017:2026 Information security, cybersecurity and privacy protection — Information security controls based on ISO/IEC 27002 for cloud services",
    "shortName": "ISO 27017",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "security",
      "cloud"
    ],
    "industries": [
      "saas",
      "banking",
      "government"
    ],
    "version": "2026 (second edition, July 2026; replaces the 2015 edition)",
    "type": "standard",
    "summary": "Cloud-specific guidance on ISO 27002 controls, clarifying shared responsibilities between cloud service providers and customers, with additional cloud controls.",
    "whoItsFor": "Cloud and SaaS providers, and organisations buying cloud services.",
    "status": "soon"
  },
  {
    "id": "iso-27018",
    "name": "ISO/IEC 27018:2025 Information security, cybersecurity and privacy protection — Guidelines for protection of personally identifiable information (PII) in public clouds acting as PII processors",
    "shortName": "ISO 27018",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "privacy",
      "cloud"
    ],
    "industries": [
      "saas",
      "healthcare",
      "banking"
    ],
    "version": "2025 (third edition, Aug 2025)",
    "type": "standard",
    "summary": "Privacy controls for public cloud providers acting as PII processors, built on ISO 27002 and ISO/IEC 29100 privacy principles.",
    "whoItsFor": "Public cloud and SaaS providers that process customers' personal data.",
    "status": "soon"
  },
  {
    "id": "iso-22301",
    "name": "ISO 22301:2019 Security and resilience — Business continuity management systems — Requirements",
    "shortName": "ISO 22301",
    "issuer": "ISO (International Organization for Standardization)",
    "region": "global",
    "categories": [
      "resilience",
      "audit-reporting"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2019 (incl. Amendment 1:2024, climate action)",
    "type": "standard",
    "summary": "Certifiable requirements for a business continuity management system: business impact analysis, continuity strategies, plans, exercising and continual improvement.",
    "whoItsFor": "Organisations that must prove they can keep critical services running through disruption.",
    "status": "soon"
  },
  {
    "id": "iso-42001",
    "name": "ISO/IEC 42001:2023 Information technology — Artificial intelligence — Management system",
    "shortName": "ISO 42001",
    "issuer": "ISO/IEC (International Organization for Standardization / International Electrotechnical Commission)",
    "region": "global",
    "categories": [
      "ai",
      "audit-reporting"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2023 (first edition, Dec 2023)",
    "type": "standard",
    "summary": "Certifiable requirements for an AI management system covering AI policy, risk and impact assessment, data governance, lifecycle controls, transparency and monitoring.",
    "whoItsFor": "Organisations that develop, provide or use AI systems and want auditable AI governance.",
    "status": "soon"
  },
  {
    "id": "pci-dss",
    "name": "Payment Card Industry Data Security Standard",
    "shortName": "PCI DSS",
    "issuer": "PCI Security Standards Council",
    "region": "global",
    "categories": [
      "payments",
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "v4.0.1 (June 2024); future-dated requirements mandatory since 31 Mar 2025",
    "type": "standard",
    "summary": "Twelve core requirements to protect payment card account data, including network security, secure configuration, access control, encryption, logging, testing and security policies.",
    "whoItsFor": "Any entity that stores, processes or transmits cardholder data, or can affect its security.",
    "status": "soon"
  },
  {
    "id": "swift-cscf",
    "name": "Swift Customer Security Controls Framework (Customer Security Programme)",
    "shortName": "Swift CSCF",
    "issuer": "Swift (Society for Worldwide Interbank Financial Telecommunication)",
    "region": "global",
    "categories": [
      "financial-services",
      "payments",
      "security"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "CSCF v2026 (published July 2025; 2026 attestations due by 31 Dec 2026): 32 controls, 26 mandatory",
    "type": "framework",
    "summary": "Mandatory and advisory security controls for Swift users' local environments; users must attest compliance annually, supported by an independent assessment.",
    "whoItsFor": "Banks and other financial institutions that connect to the Swift network.",
    "status": "soon"
  },
  {
    "id": "cis-controls",
    "name": "CIS Critical Security Controls",
    "shortName": "CIS Controls",
    "issuer": "Center for Internet Security (CIS)",
    "region": "global",
    "categories": [
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "v8.1 (June 2024)",
    "type": "framework",
    "summary": "Eighteen prioritised controls with 153 safeguards, organised into three Implementation Groups, giving a practical baseline of cyber defence.",
    "whoItsFor": "Organisations of any size wanting a prioritised, practical security baseline.",
    "status": "soon"
  },
  {
    "id": "cobit-2019",
    "name": "COBIT 2019 Framework",
    "shortName": "COBIT 2019",
    "issuer": "ISACA",
    "region": "global",
    "categories": [
      "security",
      "audit-reporting"
    ],
    "industries": [
      "banking",
      "fintech",
      "government"
    ],
    "version": "COBIT 2019",
    "type": "framework",
    "summary": "IT governance framework defining 40 governance and management objectives, design factors and capability levels to align technology with business goals and risk appetite.",
    "whoItsFor": "Boards, CIOs, IT risk and internal audit teams governing enterprise technology.",
    "status": "soon"
  },
  {
    "id": "csa-ccm-star",
    "name": "Cloud Security Alliance Cloud Controls Matrix (CCM) and STAR (Security, Trust, Assurance and Risk) programme",
    "shortName": "CSA CCM / STAR",
    "issuer": "Cloud Security Alliance (CSA)",
    "region": "global",
    "categories": [
      "cloud",
      "security",
      "audit-reporting"
    ],
    "industries": [
      "saas",
      "banking",
      "fintech"
    ],
    "version": "CCM v4.1 (Jan 2026; 207 controls in 17 domains); STAR transitioning to v4.1",
    "type": "framework",
    "summary": "Cloud-specific control framework with a matching questionnaire (CAIQ); the STAR registry publishes provider self-assessments and third-party certifications or attestations.",
    "whoItsFor": "Cloud and SaaS providers proving security to customers; cloud buyers running vendor due diligence.",
    "status": "soon"
  },
  {
    "id": "soc-2",
    "name": "SOC 2® — SOC for Service Organizations: Trust Services Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy)",
    "shortName": "SOC 2",
    "issuer": "AICPA (American Institute of Certified Public Accountants)",
    "region": "us",
    "categories": [
      "security",
      "privacy",
      "audit-reporting"
    ],
    "industries": [
      "saas",
      "fintech",
      "banking",
      "healthcare"
    ],
    "version": "2017 Trust Services Criteria (revised points of focus, 2022)",
    "type": "attestation",
    "summary": "Independent CPA examination of a service organisation's controls against the Trust Services Criteria; Type 1 covers design at a date, Type 2 operating effectiveness over a period.",
    "whoItsFor": "SaaS and service providers whose customers need assurance over controls protecting their data.",
    "jurisdictionNote": "US-originated attestation, requested worldwide",
    "status": "live"
  },
  {
    "id": "soc-1",
    "name": "SOC 1® — Report on Controls at a Service Organization Relevant to User Entities' Internal Control over Financial Reporting",
    "shortName": "SOC 1",
    "issuer": "AICPA (American Institute of Certified Public Accountants)",
    "region": "us",
    "categories": [
      "audit-reporting",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "SSAE No. 18, AT-C section 320",
    "type": "attestation",
    "summary": "Service auditor's report on a service organisation's controls relevant to customers' financial reporting, used by customers and their auditors, including for SOX.",
    "whoItsFor": "Payroll, payments, loan-servicing, hosting and other providers whose services affect customers' financial statements.",
    "jurisdictionNote": "US-originated attestation, requested worldwide",
    "status": "soon"
  },
  {
    "id": "soc-3",
    "name": "SOC 3® — SOC for Service Organizations: Trust Services Criteria for General Use Report",
    "shortName": "SOC 3",
    "issuer": "AICPA (American Institute of Certified Public Accountants)",
    "region": "us",
    "categories": [
      "audit-reporting",
      "security"
    ],
    "industries": [
      "saas",
      "fintech"
    ],
    "version": "2017 Trust Services Criteria (revised points of focus, 2022)",
    "type": "attestation",
    "summary": "General-use report on controls against the Trust Services Criteria; can be shared publicly, omitting the detailed control tests found in SOC 2.",
    "whoItsFor": "Service providers wanting a public trust-page report alongside their restricted-use SOC 2.",
    "jurisdictionNote": "US-originated attestation, requested worldwide",
    "status": "soon"
  },
  {
    "id": "hipaa-security-rule",
    "name": "HIPAA Security Rule — Security Standards for the Protection of Electronic Protected Health Information (45 CFR Part 164, Subpart C)",
    "shortName": "HIPAA Security Rule",
    "issuer": "U.S. Department of Health and Human Services (HHS), Office for Civil Rights",
    "region": "us",
    "categories": [
      "healthcare",
      "security",
      "privacy"
    ],
    "industries": [
      "healthcare",
      "saas"
    ],
    "version": "45 CFR Parts 160 and 164 (Subparts A and C); major update proposed Jan 2025, not final as of mid-2026",
    "type": "regulation",
    "summary": "Requires administrative, physical and technical safeguards, including risk analysis, to protect electronic protected health information; breach notification rules apply alongside.",
    "whoItsFor": "US covered entities (providers, health plans, clearinghouses) and their business associates, including SaaS vendors.",
    "status": "soon"
  },
  {
    "id": "hitrust-csf",
    "name": "HITRUST CSF (HITRUST Common Security Framework)",
    "shortName": "HITRUST CSF",
    "issuer": "HITRUST",
    "region": "us",
    "categories": [
      "healthcare",
      "security",
      "privacy",
      "audit-reporting"
    ],
    "industries": [
      "healthcare",
      "saas"
    ],
    "version": "v11.9.0 (released 24 Sep 2026)",
    "type": "framework",
    "summary": "Certifiable control framework harmonising HIPAA, NIST, ISO and other sources, assessed through tiered e1, i1 and r2 assessments with HITRUST-issued certification.",
    "whoItsFor": "Healthcare organisations and their technology vendors needing a recognised, certifiable security assurance.",
    "status": "soon"
  },
  {
    "id": "nist-csf-2",
    "name": "NIST Cybersecurity Framework (CSF) 2.0",
    "shortName": "NIST CSF 2.0",
    "issuer": "U.S. National Institute of Standards and Technology (NIST)",
    "region": "us",
    "categories": [
      "security",
      "resilience"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2.0 (26 Feb 2024; NIST CSWP 29)",
    "type": "framework",
    "summary": "Outcome-based framework of six functions (Govern, Identify, Protect, Detect, Respond, Recover) for assessing, prioritising and communicating cybersecurity risk management.",
    "whoItsFor": "Any organisation; US bank regulators point to it since retiring the FFIEC CAT in 2025.",
    "jurisdictionNote": "Voluntary; used worldwide",
    "status": "soon"
  },
  {
    "id": "nist-sp-800-53",
    "name": "NIST SP 800-53 Rev. 5, Security and Privacy Controls for Information Systems and Organizations",
    "shortName": "NIST 800-53",
    "issuer": "U.S. National Institute of Standards and Technology (NIST)",
    "region": "us",
    "categories": [
      "security",
      "privacy",
      "government"
    ],
    "industries": [
      "government",
      "saas",
      "banking",
      "healthcare"
    ],
    "version": "Rev. 5 (Release 5.2.0, Aug 2025)",
    "type": "standard",
    "summary": "Comprehensive catalogue of security and privacy controls across 20 families; the basis for US federal systems, FedRAMP baselines and many sector frameworks.",
    "whoItsFor": "US federal agencies, their contractors and cloud providers; also a reference catalogue for regulated enterprises.",
    "status": "soon"
  },
  {
    "id": "nist-sp-800-171",
    "name": "NIST SP 800-171 Rev. 3, Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations",
    "shortName": "NIST 800-171",
    "issuer": "U.S. National Institute of Standards and Technology (NIST)",
    "region": "us",
    "categories": [
      "security",
      "government"
    ],
    "industries": [
      "government",
      "saas"
    ],
    "version": "Rev. 3 (May 2024); DoD contracts and CMMC Level 2 still assess Rev. 2 under a class deviation",
    "type": "standard",
    "summary": "Security requirements for protecting Controlled Unclassified Information held by contractors and other non-federal organisations, derived from the NIST 800-53 moderate baseline.",
    "whoItsFor": "Defence and federal contractors, universities and suppliers handling US government CUI.",
    "status": "soon"
  },
  {
    "id": "cmmc-2",
    "name": "Cybersecurity Maturity Model Certification (CMMC) Program",
    "shortName": "CMMC 2.0",
    "issuer": "U.S. Department of Defense (DoD)",
    "region": "us",
    "categories": [
      "security",
      "government",
      "audit-reporting"
    ],
    "industries": [
      "government",
      "saas"
    ],
    "version": "32 CFR Part 170 (effective 16 Dec 2024); DFARS contract rule effective 10 Nov 2025, phased rollout",
    "type": "regulation",
    "summary": "Three-level DoD certification verifying contractors protect Federal Contract Information and CUI, via self-assessment, third-party (C3PAO) or government assessment, as a contract-award condition.",
    "whoItsFor": "Companies in the US defence industrial base and their subcontractors handling FCI or CUI.",
    "status": "soon"
  },
  {
    "id": "fedramp",
    "name": "Federal Risk and Authorization Management Program",
    "shortName": "FedRAMP",
    "issuer": "U.S. General Services Administration (FedRAMP Program Management Office)",
    "region": "us",
    "categories": [
      "cloud",
      "government",
      "security"
    ],
    "industries": [
      "saas",
      "government"
    ],
    "version": "Consolidated Rules for 2026 (CR26, published June 2026); Rev5 and FedRAMP 20x paths",
    "type": "framework",
    "summary": "Standardised security assessment and authorisation for cloud services used by US federal agencies, with continuous monitoring; now moving from Rev5 baselines to the 20x model.",
    "whoItsFor": "Cloud and SaaS providers selling to US federal government agencies.",
    "status": "soon"
  },
  {
    "id": "sox-404-itgc",
    "name": "Sarbanes-Oxley Act of 2002, Section 404 — Management assessment of internal control over financial reporting (incl. IT general controls)",
    "shortName": "SOX 404 (ITGC)",
    "issuer": "U.S. Congress; implemented by the SEC and PCAOB",
    "region": "us",
    "categories": [
      "audit-reporting",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "Sarbanes-Oxley Act of 2002; SEC ICFR rules; PCAOB AS 2201",
    "type": "law",
    "summary": "Management must assess, and larger filers' auditors attest to, internal control over financial reporting, including IT general controls over access, change management and operations.",
    "whoItsFor": "SEC-registered public companies, including listed banks; providers support them through SOC 1 reports.",
    "status": "soon"
  },
  {
    "id": "glba-safeguards-rule",
    "name": "Gramm-Leach-Bliley Act Safeguards Rule — Standards for Safeguarding Customer Information (16 CFR Part 314)",
    "shortName": "GLBA Safeguards Rule",
    "issuer": "U.S. Federal Trade Commission (FTC)",
    "region": "us",
    "categories": [
      "financial-services",
      "privacy",
      "security"
    ],
    "industries": [
      "fintech",
      "banking"
    ],
    "version": "16 CFR Part 314 (amended 2021; FTC breach notification in force 13 May 2024)",
    "type": "regulation",
    "summary": "Requires a written information security program—qualified individual, risk assessment, MFA, encryption, board reporting—and FTC notice within 30 days of breaches affecting 500+ consumers.",
    "whoItsFor": "US non-bank financial institutions: lenders, fintechs, payment firms, mortgage brokers, auto dealers, tax preparers.",
    "jurisdictionNote": "FTC rule covers non-bank financial institutions; banks follow the Interagency Guidelines Establishing Information Security Standards",
    "status": "soon"
  },
  {
    "id": "nydfs-part-500",
    "name": "New York Department of Financial Services Cybersecurity Requirements for Financial Services Companies (23 NYCRR Part 500)",
    "shortName": "NYDFS Part 500",
    "issuer": "New York State Department of Financial Services (NYDFS)",
    "region": "us",
    "categories": [
      "financial-services",
      "security"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "Second Amendment (Nov 2023), fully phased in 1 Nov 2025",
    "type": "regulation",
    "summary": "Prescriptive cybersecurity program rules: CISO, risk assessment, MFA, asset inventory, encryption, 72-hour incident notice and annual compliance certification signed by CEO and CISO.",
    "whoItsFor": "Banks, insurers, money transmitters, virtual-currency firms and other entities licensed by NYDFS.",
    "jurisdictionNote": "New York State; entities licensed or regulated by NYDFS",
    "status": "soon"
  },
  {
    "id": "ccpa-cpra",
    "name": "California Consumer Privacy Act of 2018, as amended by the California Privacy Rights Act of 2020",
    "shortName": "CCPA / CPRA",
    "issuer": "State of California; regulator: California Privacy Protection Agency (CPPA)",
    "region": "us",
    "categories": [
      "privacy"
    ],
    "industries": [
      "saas",
      "fintech",
      "healthcare"
    ],
    "version": "CCPA as amended by CPRA; CPPA regulations on cybersecurity audits, risk assessments and ADMT effective 1 Jan 2026 (phased to 2030)",
    "type": "law",
    "summary": "Grants Californians rights to know, delete, correct and opt out of sale or sharing; new rules require risk assessments, cybersecurity audits and automated-decisionmaking controls.",
    "whoItsFor": "For-profit businesses meeting CCPA thresholds that handle California residents' personal information.",
    "jurisdictionNote": "California residents' personal information",
    "status": "soon"
  },
  {
    "id": "nist-ai-rmf",
    "name": "Artificial Intelligence Risk Management Framework (AI RMF 1.0)",
    "shortName": "NIST AI RMF",
    "issuer": "U.S. National Institute of Standards and Technology (NIST)",
    "region": "us",
    "categories": [
      "ai"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "1.0 (NIST AI 100-1, Jan 2023), plus Generative AI Profile (NIST AI 600-1)",
    "type": "framework",
    "summary": "Voluntary framework for managing AI risks across four functions (Govern, Map, Measure, Manage), promoting trustworthy characteristics such as validity, safety, security, accountability and privacy.",
    "whoItsFor": "Organisations designing, deploying or buying AI systems, including banks applying model risk management.",
    "jurisdictionNote": "Voluntary; used worldwide",
    "status": "soon"
  },
  {
    "id": "sec-cyber-disclosure",
    "name": "SEC Cybersecurity Risk Management, Strategy, Governance, and Incident Disclosure rules",
    "shortName": "SEC Cyber Disclosure Rules",
    "issuer": "U.S. Securities and Exchange Commission (SEC)",
    "region": "us",
    "categories": [
      "audit-reporting",
      "security",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas",
      "healthcare"
    ],
    "version": "Adopted July 2023 (Form 8-K Item 1.05; Regulation S-K Item 106)",
    "type": "regulation",
    "summary": "Public companies must disclose material cybersecurity incidents on Form 8-K within four business days of determining materiality, and annually describe cyber risk management and board oversight.",
    "whoItsFor": "SEC-registered public companies, including listed banks, insurers and technology firms.",
    "status": "soon"
  },
  {
    "id": "sbp-etgrmf",
    "name": "Enterprise Technology Governance & Risk Management Framework for Financial Institutions",
    "shortName": "SBP ETGRMF",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "financial-services",
      "security",
      "resilience"
    ],
    "industries": [
      "banking"
    ],
    "version": "BPRD Circular No. 05 of 2017 (30 May 2017)",
    "type": "framework",
    "summary": "Baseline technology governance and risk management rules: board IT committee oversight, IT steering committee, CISO independent of IT, security controls and 48-hour incident reporting to SBP.",
    "whoItsFor": "Commercial and Islamic banks, DFIs and microfinance banks regulated by SBP.",
    "status": "soon"
  },
  {
    "id": "sbp-outsourcing-framework",
    "name": "Framework for Risk Management in Outsourcing Arrangements by Financial Institutions",
    "shortName": "SBP Outsourcing Framework",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "financial-services",
      "resilience"
    ],
    "industries": [
      "banking"
    ],
    "version": "BPRD Circular No. 06 of 2017, amended by BPRD Circular No. 06 of 2019",
    "type": "framework",
    "summary": "Outsourcing policy, board approval of material arrangements, vendor due diligence, contingency and exit plans; core banking functions cannot be outsourced; certain offshore arrangements need SBP approval.",
    "whoItsFor": "Commercial, Islamic and microfinance banks and DFIs using third-party or group service providers.",
    "status": "soon"
  },
  {
    "id": "sbp-cloud-outsourcing-framework",
    "name": "Framework on Outsourcing to Cloud Service Providers",
    "shortName": "SBP Cloud Framework",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "financial-services",
      "cloud",
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "BPRD Circular No. 01 of 2023 (16 Jan 2023)",
    "type": "framework",
    "summary": "Risk-based rules for moving material and non-material workloads to cloud providers; onshore cloud is permitted, while offshore hosting of material workloads needs case-by-case SBP approval.",
    "whoItsFor": "SBP-regulated banks, digital banks, MFBs, DFIs, EMIs and payment operators, and their cloud vendors.",
    "status": "soon"
  },
  {
    "id": "sbp-payment-card-security",
    "name": "Regulations for Payment Card Security",
    "shortName": "SBP Payment Card Security Regulations",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "payments",
      "security",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "PSD Circular No. 05 of 2016 (10 June 2016); updated by PSD Circular Letter No. 02 of 2021",
    "type": "regulation",
    "summary": "Minimum operational, administrative, technical and physical safeguards for payment card operations, including a card security framework and EMV chip adoption.",
    "whoItsFor": "Banks, payment system operators and payment service providers issuing or processing payment cards in Pakistan.",
    "status": "soon"
  },
  {
    "id": "sbp-cyber-shield",
    "name": "Cyber Shield – the Cyber Resilience Strategy for Regulated Entities",
    "shortName": "SBP Cyber Shield",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "financial-services",
      "security",
      "resilience"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "Launched 16 Feb 2026; phased milestones to 2030",
    "type": "framework",
    "summary": "SBP strategy requiring regulated entities to align cybersecurity programmes with five priorities: resilience, governance and accountability, information-sharing, cyber talent, and updated security practices.",
    "whoItsFor": "SBP-regulated entities: banks, microfinance banks, DFIs and other licensed financial institutions.",
    "status": "soon"
  },
  {
    "id": "sbp-trmf-payment-institutions",
    "name": "Technology Risk Management Framework for Payment Institutions",
    "shortName": "SBP TRMF for Payment Institutions",
    "issuer": "State Bank of Pakistan (SBP)",
    "region": "pk",
    "categories": [
      "payments",
      "security",
      "financial-services"
    ],
    "industries": [
      "fintech"
    ],
    "version": "PSP&OD Circular No. 04 of 2025 (3 Oct 2025); compliance due 31 Mar 2026",
    "type": "framework",
    "summary": "Baseline technology governance, cyber security and technology risk requirements for payment institutions, applied proportionately to their size, services and technology complexity.",
    "whoItsFor": "PSOs, PSPs, EMIs and other entities licensed under Pakistan's PS&EFT Act 2007.",
    "status": "soon"
  },
  {
    "id": "pk-peca",
    "name": "Prevention of Electronic Crimes Act, 2016",
    "shortName": "PECA 2016",
    "issuer": "Parliament of Pakistan",
    "region": "pk",
    "categories": [
      "security",
      "privacy"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "2016, amended by the Prevention of Electronic Crimes (Amendment) Act, 2025",
    "type": "law",
    "summary": "Pakistan's cybercrime law: criminalises unauthorised access, data and system interference, electronic fraud and identity misuse; 2025 amendments added online-content offences and a social media regulator.",
    "whoItsFor": "All organisations operating information systems in Pakistan; service providers face data-retention and cooperation duties.",
    "status": "soon"
  },
  {
    "id": "pk-pdpb",
    "name": "Personal Data Protection Bill (draft)",
    "shortName": "Pakistan PDPB (draft)",
    "issuer": "Ministry of Information Technology & Telecommunication (MoITT), Government of Pakistan",
    "region": "pk",
    "categories": [
      "privacy"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "Draft: 2023 bill approved by Federal Cabinet (July 2023); not enacted as of mid-2026",
    "type": "law",
    "summary": "Proposed comprehensive data protection law covering consent, data-subject rights, cross-border transfers and a National Commission for Personal Data Protection; not yet enacted.",
    "whoItsFor": "Organisations processing personal data in Pakistan, if and when enacted.",
    "jurisdictionNote": "Draft only; not enacted",
    "status": "soon"
  },
  {
    "id": "secp-insurance-cybersecurity",
    "name": "SEC Guidelines on Cybersecurity Framework for the Insurance Sector, 2020",
    "shortName": "SECP Insurance Cybersecurity Guidelines",
    "issuer": "Securities and Exchange Commission of Pakistan (SECP)",
    "region": "pk",
    "categories": [
      "security",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "2020 (effective 1 July 2020)",
    "type": "framework",
    "summary": "Principles for insurers and takaful operators to anticipate, withstand, detect and respond to cyber attacks, including a CISO and an annual framework assessment report to SECP.",
    "whoItsFor": "Insurers and takaful operators registered under Pakistan's Insurance Ordinance 2000.",
    "jurisdictionNote": "Insurance sector; no general SECP IT framework for all regulated entities was verified",
    "status": "soon"
  },
  {
    "id": "uae-ia-standard",
    "name": "UAE Information Assurance Standard (successor to the UAE Information Assurance Regulation, formerly NESA IAS)",
    "shortName": "UAE IAS",
    "issuer": "UAE Cyber Security Council",
    "region": "ae",
    "categories": [
      "security",
      "government",
      "critical-infrastructure"
    ],
    "industries": [
      "government",
      "banking",
      "healthcare"
    ],
    "version": "v2.0 (2025, Cyber Security Council); replaces UAE IA Regulation v1.1 (TDRA, March 2020)",
    "type": "standard",
    "summary": "National risk-based control set of management and technical control families, aligned to ISO 27001, for protecting government and critical national information systems.",
    "whoItsFor": "UAE federal entities, critical-infrastructure operators and their suppliers.",
    "jurisdictionNote": "Federal government entities and critical information infrastructure",
    "status": "soon"
  },
  {
    "id": "desc-isr",
    "name": "Information Security Regulation (ISR) for Dubai Government entities",
    "shortName": "DESC ISR",
    "issuer": "Dubai Electronic Security Center (DESC)",
    "region": "ae",
    "categories": [
      "security",
      "government"
    ],
    "industries": [
      "government",
      "saas"
    ],
    "version": "ISR v3.0 (launched 2023)",
    "type": "regulation",
    "summary": "Mandatory information security requirements for Dubai Government entities; v3.0 adds rules such as UAE-national security leadership and keeping critical information in the UAE.",
    "whoItsFor": "Dubai Government and semi-government entities, plus contractors and vendors handling their information.",
    "jurisdictionNote": "Dubai Government entities and their suppliers",
    "status": "soon"
  },
  {
    "id": "desc-csp-security-standard",
    "name": "Cloud Service Provider (CSP) Security Standard",
    "shortName": "DESC CSP Security Standard",
    "issuer": "Dubai Electronic Security Center (DESC)",
    "region": "ae",
    "categories": [
      "cloud",
      "security",
      "government"
    ],
    "industries": [
      "saas",
      "government"
    ],
    "version": "DESC CSP Security Standard (published edition dated January 2020 update); certification with annual surveillance audits",
    "type": "standard",
    "summary": "Security requirements for cloud providers serving Dubai Government, built on ISO 27001/27017 and CSA CCM; providers demonstrate compliance through third-party certification.",
    "whoItsFor": "Cloud and SaaS providers offering services to Dubai Government and semi-government entities.",
    "jurisdictionNote": "Cloud services for Dubai Government and semi-government entities",
    "status": "soon"
  },
  {
    "id": "adhics",
    "name": "Abu Dhabi Healthcare Information and Cyber Security Standard",
    "shortName": "ADHICS",
    "issuer": "Department of Health – Abu Dhabi (DoH)",
    "region": "ae",
    "categories": [
      "healthcare",
      "security",
      "privacy"
    ],
    "industries": [
      "healthcare",
      "saas"
    ],
    "version": "v2.0 (published May 2024, effective Aug 2024); supersedes the 2019 standard",
    "type": "standard",
    "summary": "Mandatory cyber security and health-information protection controls, tiered Basic to Advanced, for entities handling health information in Abu Dhabi, including cloud and medical IoT.",
    "whoItsFor": "Abu Dhabi healthcare facilities, payers, and health technology and service providers.",
    "jurisdictionNote": "Emirate of Abu Dhabi",
    "status": "soon"
  },
  {
    "id": "uae-pdpl",
    "name": "Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data",
    "shortName": "UAE PDPL",
    "issuer": "UAE Federal Government (regulator: UAE Data Office, now within the UAE Artificial Intelligence and Data Authority)",
    "region": "ae",
    "categories": [
      "privacy"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "Federal Decree-Law No. 45 of 2021 (in force 2 Jan 2022); Executive Regulations not confirmed as published",
    "type": "law",
    "summary": "GDPR-style federal law: lawful processing, data-subject rights, security measures, breach notification, DPO for some processing, and cross-border transfer limits.",
    "whoItsFor": "Private-sector organisations processing UAE personal data; excludes DIFC/ADGM and health or banking data with own laws.",
    "jurisdictionNote": "UAE onshore; DIFC and ADGM have their own laws",
    "status": "soon"
  },
  {
    "id": "difc-dpl",
    "name": "Data Protection Law, DIFC Law No. 5 of 2020",
    "shortName": "DIFC DPL",
    "issuer": "Dubai International Financial Centre (DIFC); supervised by the DIFC Commissioner of Data Protection",
    "region": "ae",
    "categories": [
      "privacy",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "DIFC Law No. 5 of 2020 (as amended; consolidated July 2025)",
    "type": "law",
    "summary": "GDPR-aligned law for the DIFC: accountability, DPIAs, data-subject rights, breach notification and transfer rules; 2025 amendments added a private right of action.",
    "whoItsFor": "Banks, fintechs and other firms established in, or processing data within, the DIFC.",
    "jurisdictionNote": "DIFC free zone (Dubai)",
    "status": "soon"
  },
  {
    "id": "adgm-dpr",
    "name": "ADGM Data Protection Regulations 2021",
    "shortName": "ADGM DPR 2021",
    "issuer": "Abu Dhabi Global Market (ADGM); supervised by the ADGM Office of Data Protection",
    "region": "ae",
    "categories": [
      "privacy",
      "financial-services"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "2021 (enacted 11 Feb 2021; amended, incl. 2025 substantial public interest rules)",
    "type": "regulation",
    "summary": "GDPR-modelled regulations for ADGM: lawful processing, data-subject rights, DPIAs, breach notification and international transfer controls, enforced by ADGM's Office of Data Protection.",
    "whoItsFor": "Financial institutions and other businesses established in ADGM, and their processors.",
    "jurisdictionNote": "ADGM free zone (Abu Dhabi)",
    "status": "soon"
  },
  {
    "id": "cbuae-outsourcing-regulation",
    "name": "Outsourcing Regulation for Banks and Outsourcing Standards for Banks",
    "shortName": "CBUAE Outsourcing Regulation",
    "issuer": "Central Bank of the UAE (CBUAE)",
    "region": "ae",
    "categories": [
      "financial-services",
      "resilience"
    ],
    "industries": [
      "banking",
      "saas"
    ],
    "version": "Circular No. 14/2021 (effective 15 July 2021)",
    "type": "regulation",
    "summary": "Banks must assess materiality, keep an outsourcing register, obtain CBUAE non-objection for material outsourcing, and keep the master record of confidential data in the UAE.",
    "whoItsFor": "UAE-licensed banks and the technology and service vendors they outsource to.",
    "status": "soon"
  },
  {
    "id": "cbuae-operational-risk-regulation",
    "name": "Operational Risk Management Regulation",
    "shortName": "CBUAE Operational Risk Management Regulation",
    "issuer": "Central Bank of the UAE (CBUAE)",
    "region": "ae",
    "categories": [
      "financial-services",
      "resilience",
      "security"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "Circular No. 1/2026 (in force 14 Sep 2026); replaces the 2018 Operational Risk Regulation (C 163/2018) and Standards",
    "type": "regulation",
    "summary": "Operational resilience and BCM rules: identify critical operations, map dependencies, manage cyber and third-party risk, and notify CBUAE within four hours of significant disruptions.",
    "whoItsFor": "Banks, insurers and other CBUAE-licensed financial institutions with legal personality.",
    "status": "soon"
  },
  {
    "id": "cbuae-consumer-protection",
    "name": "Consumer Protection Regulation and Consumer Protection Standards",
    "shortName": "CBUAE Consumer Protection Regulation",
    "issuer": "Central Bank of the UAE (CBUAE)",
    "region": "ae",
    "categories": [
      "financial-services",
      "privacy"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "Circular No. 8/2020 (Regulation); Consumer Protection Standards issued 2021",
    "type": "regulation",
    "summary": "Conduct, governance, disclosure, complaints-handling and consumer data protection obligations for licensed financial institutions, including controls against information security breaches.",
    "whoItsFor": "Banks, finance companies, payment providers and other CBUAE-licensed institutions serving consumers.",
    "status": "soon"
  },
  {
    "id": "uae-health-ict-law",
    "name": "Federal Law No. 2 of 2019 Concerning the Use of Information and Communications Technology in Health Fields",
    "shortName": "UAE Health ICT Law",
    "issuer": "UAE Federal Government (Ministry of Health and Prevention with emirate health authorities)",
    "region": "ae",
    "categories": [
      "healthcare",
      "privacy",
      "security"
    ],
    "industries": [
      "healthcare",
      "saas"
    ],
    "version": "Federal Law No. 2 of 2019 (in force May 2019); exceptions in Ministerial Resolution No. 51 of 2021",
    "type": "law",
    "summary": "Governs health data security and confidentiality; health data must be stored and processed in the UAE unless an exception applies, and retained at least 25 years.",
    "whoItsFor": "Healthcare providers, insurers and health-tech companies handling UAE health data.",
    "status": "soon"
  },
  {
    "id": "apra-cps-234",
    "name": "Prudential Standard CPS 234 Information Security",
    "shortName": "APRA CPS 234",
    "issuer": "Australian Prudential Regulation Authority (APRA)",
    "region": "au",
    "categories": [
      "financial-services",
      "security"
    ],
    "industries": [
      "banking",
      "fintech"
    ],
    "version": "July 2019 (in force 1 July 2019)",
    "type": "regulation",
    "summary": "Board-accountable information security capability, controls proportional to threats, systematic control testing, and APRA notification within 72 hours of material incidents.",
    "whoItsFor": "APRA-regulated banks (ADIs), insurers and superannuation trustees, including oversight of their service providers.",
    "status": "soon"
  },
  {
    "id": "apra-cps-230",
    "name": "Prudential Standard CPS 230 Operational Risk Management",
    "shortName": "APRA CPS 230",
    "issuer": "Australian Prudential Regulation Authority (APRA)",
    "region": "au",
    "categories": [
      "financial-services",
      "resilience"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "In force 1 July 2025 (replaces CPS 231 Outsourcing and CPS 232 Business Continuity, among others)",
    "type": "regulation",
    "summary": "Requires operational risk management, business continuity for critical operations within set tolerances, and management of material service providers, with an annual service-provider register to APRA.",
    "whoItsFor": "APRA-regulated entities and, indirectly, the material service providers they rely on.",
    "status": "soon"
  },
  {
    "id": "essential-eight",
    "name": "Essential Eight Maturity Model",
    "shortName": "Essential Eight",
    "issuer": "Australian Signals Directorate (ASD) / Australian Cyber Security Centre",
    "region": "au",
    "categories": [
      "security",
      "government"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "Maturity model last updated November 2023 (ASD consulted in 2026 on its evolution)",
    "type": "framework",
    "summary": "Eight prioritised mitigation strategies, including patching, MFA, application control, restricted admin privileges and backups, assessed at maturity levels zero to three.",
    "whoItsFor": "Non-corporate Commonwealth entities (Maturity Level Two under PSPF) and businesses wanting a practical baseline.",
    "status": "soon"
  },
  {
    "id": "australian-ism",
    "name": "Information Security Manual",
    "shortName": "ISM",
    "issuer": "Australian Signals Directorate (ASD)",
    "region": "au",
    "categories": [
      "security",
      "government"
    ],
    "industries": [
      "government",
      "saas"
    ],
    "version": "Updated quarterly; September 2026 release is current",
    "type": "framework",
    "summary": "ASD's cyber security framework of principles and controls for protecting systems and data, applied by risk and classification; the basis for IRAP assessments.",
    "whoItsFor": "Australian government agencies, their suppliers and cloud providers, and organisations wanting rigorous controls.",
    "status": "soon"
  },
  {
    "id": "pspf",
    "name": "Protective Security Policy Framework",
    "shortName": "PSPF",
    "issuer": "Australian Government Department of Home Affairs",
    "region": "au",
    "categories": [
      "government",
      "security"
    ],
    "industries": [
      "government"
    ],
    "version": "PSPF Release 2026",
    "type": "framework",
    "summary": "Mandatory protective security requirements for Commonwealth entities across governance, risk, information, technology, personnel and physical security, with annual reporting.",
    "whoItsFor": "Australian Government entities and the contractors and providers handling government information.",
    "jurisdictionNote": "Australian Government (Commonwealth) entities",
    "status": "soon"
  },
  {
    "id": "au-privacy-act",
    "name": "Privacy Act 1988 (Cth), including the Australian Privacy Principles and the Notifiable Data Breaches scheme",
    "shortName": "Privacy Act / APPs",
    "issuer": "Parliament of Australia; regulator: Office of the Australian Information Commissioner (OAIC)",
    "region": "au",
    "categories": [
      "privacy"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "As amended by the Privacy and Other Legislation Amendment Act 2024; further (tranche 2) reforms at exposure-draft stage",
    "type": "law",
    "summary": "Thirteen Australian Privacy Principles govern personal information handling and security; eligible data breaches must be notified to the OAIC and individuals as soon as practicable.",
    "whoItsFor": "Australian Government agencies and most organisations with annual turnover above A$3 million, plus health service providers.",
    "status": "soon"
  },
  {
    "id": "soci-act-cirmp",
    "name": "Security of Critical Infrastructure Act 2018 and Security of Critical Infrastructure (Critical infrastructure risk management program) Rules (LIN 23/006) 2023",
    "shortName": "SOCI Act / CIRMP",
    "issuer": "Parliament of Australia; administered by the Cyber and Infrastructure Security Centre (Department of Home Affairs)",
    "region": "au",
    "categories": [
      "critical-infrastructure",
      "security",
      "resilience"
    ],
    "industries": [
      "banking",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "SOCI Act 2018 (as amended); CIRMP Rules 2023",
    "type": "law",
    "summary": "Critical infrastructure asset owners must register assets, report cyber incidents to ASD within 12 or 72 hours, and run a board-approved risk management program.",
    "whoItsFor": "Responsible entities in 11 sectors, including financial services, health care, and data storage or processing.",
    "status": "soon"
  },
  {
    "id": "irap",
    "name": "Infosec Registered Assessors Program",
    "shortName": "IRAP",
    "issuer": "Australian Signals Directorate (ASD)",
    "region": "au",
    "categories": [
      "government",
      "cloud",
      "audit-reporting"
    ],
    "industries": [
      "saas",
      "government"
    ],
    "version": "Ongoing ASD program; assessments against the current ISM",
    "type": "attestation",
    "summary": "ASD-endorsed assessors independently evaluate systems and cloud services against the ISM and PSPF; reports inform government risk decisions and are not a certification.",
    "whoItsFor": "Cloud and SaaS providers selling to Australian government, especially for OFFICIAL: Sensitive or PROTECTED data.",
    "status": "soon"
  },
  {
    "id": "gdpr",
    "name": "General Data Protection Regulation (Regulation (EU) 2016/679)",
    "shortName": "GDPR",
    "issuer": "European Parliament and Council of the European Union",
    "region": "eu",
    "categories": [
      "privacy",
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "Regulation (EU) 2016/679 (applies since 25 May 2018)",
    "type": "regulation",
    "summary": "Comprehensive data protection law: lawful basis, data-subject rights, security, DPIAs, DPOs, 72-hour breach notification to regulators, and restrictions on international transfers.",
    "whoItsFor": "Organisations in the EU, and non-EU organisations offering services to or monitoring people in the EU.",
    "jurisdictionNote": "EU/EEA; also applies to non-EU firms targeting or monitoring people in the EU",
    "status": "soon"
  },
  {
    "id": "dora",
    "name": "Digital Operational Resilience Act (Regulation (EU) 2022/2554)",
    "shortName": "DORA",
    "issuer": "European Parliament and Council of the European Union",
    "region": "eu",
    "categories": [
      "financial-services",
      "resilience",
      "security"
    ],
    "industries": [
      "banking",
      "fintech",
      "saas"
    ],
    "version": "Regulation (EU) 2022/2554 (applies from 17 Jan 2025)",
    "type": "regulation",
    "summary": "ICT risk management, major-incident reporting, resilience testing including threat-led penetration testing, and ICT third-party risk management with a register of information for EU financial entities.",
    "whoItsFor": "EU banks, insurers, investment and payment firms, crypto-asset providers, and their critical ICT providers.",
    "jurisdictionNote": "EU financial sector; critical ICT third-party providers overseen by the European Supervisory Authorities",
    "status": "soon"
  },
  {
    "id": "nis2",
    "name": "Directive (EU) 2022/2555 on measures for a high common level of cybersecurity across the Union (NIS2 Directive)",
    "shortName": "NIS2",
    "issuer": "European Parliament and Council of the European Union",
    "region": "eu",
    "categories": [
      "security",
      "critical-infrastructure",
      "resilience"
    ],
    "industries": [
      "healthcare",
      "banking",
      "saas",
      "government"
    ],
    "version": "Directive (EU) 2022/2555 (transposition deadline 17 Oct 2024; several Member States still transposing in 2026)",
    "type": "law",
    "summary": "Cybersecurity risk-management measures, management-body accountability, supply-chain security, and staged incident reporting (24-hour early warning, 72-hour notification, one-month report) for essential and important entities.",
    "whoItsFor": "Medium and large organisations in 18 critical sectors, including health, banking, digital infrastructure, ICT services and public administration.",
    "jurisdictionNote": "Applies through each Member State's transposing law",
    "status": "soon"
  },
  {
    "id": "eu-ai-act",
    "name": "Artificial Intelligence Act (Regulation (EU) 2024/1689)",
    "shortName": "EU AI Act",
    "issuer": "European Parliament and Council of the European Union",
    "region": "eu",
    "categories": [
      "ai"
    ],
    "industries": [
      "banking",
      "fintech",
      "healthcare",
      "saas",
      "government"
    ],
    "version": "Regulation (EU) 2024/1689, amended by Regulation (EU) 2026/1744; most high-risk obligations deferred to 2 Dec 2027 (Annex III) and 2 Aug 2028 (Annex I)",
    "type": "regulation",
    "summary": "Risk-based AI rules: prohibited practices, obligations for high-risk systems (risk management, data governance, human oversight, logging), transparency duties and general-purpose AI model requirements.",
    "whoItsFor": "Providers and deployers of AI used in the EU, including non-EU firms; bank credit scoring is high-risk.",
    "jurisdictionNote": "EU market; applies to non-EU providers whose AI is used in the EU",
    "status": "soon"
  }
];
