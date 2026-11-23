"""The company profile questions: one catalogue that validates answers and drives the form.

Guided onboarding part 2, section 2.1 (requirements PR-1, PR-4, PR-5, PR-6). The frontend
renders the form from ``GET /tenant/profile/questions``, so the options a person can pick and
the options the server accepts are the same list. Every question names what reads its answer
(``used_for``); a content test fails a question with no consumer, so nothing is asked that
nothing uses.

Answers are stored as one JSON object on ``company_profile.answers``. "Not sure yet" is a valid
answer to every yes or no question and produces no proposal later (PR-6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

from verity.core.errors import InvalidInput
from verity.shared.countries import is_country, is_country_or_region

Kind = Literal["text", "one", "many", "tri", "country", "countries", "regions", "month"]

ANSWERS_SCHEMA: Final = 1
TEXT_MAX: Final = 400
TRI: Final[tuple[tuple[str, str], ...]] = (
    ("yes", "Yes"),
    ("no", "No"),
    ("not_sure", "Not sure yet"),
)
NONE_VALUE: Final = "none"


@dataclass(frozen=True, slots=True)
class ShowIf:
    """Show a question only when another answer matches. ``contains`` for list answers."""

    key: str
    equals: tuple[str, ...] = ()
    contains: str | None = None

    def holds(self, answers: dict[str, Any]) -> bool:
        value = answers.get(self.key)
        if self.contains is not None:
            return isinstance(value, list) and self.contains in value
        return value in self.equals


@dataclass(frozen=True, slots=True)
class Question:
    key: str
    section: str
    label: str
    kind: Kind
    used_for: str
    """One plain line saying what reads the answer. Shown under the question."""
    core: bool = False
    options: tuple[tuple[str, str], ...] = ()
    show_if: tuple[ShowIf, ...] = field(default_factory=tuple)
    """Shown when any condition holds. Empty means always shown."""
    hint: str | None = None

    def shown(self, answers: dict[str, Any]) -> bool:
        return not self.show_if or any(rule.holds(answers) for rule in self.show_if)


SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("about", "About the company"),
    ("where", "Where you operate"),
    ("how", "How you work"),
    ("systems", "Systems"),
    ("data", "Data and privacy"),
    ("regulation", "Regulation and assurance"),
)

QUESTIONS: Final[tuple[Question, ...]] = (
    # -- about -------------------------------------------------------------------
    Question(
        "description",
        "about",
        "What do you sell, in two sentences?",
        "text",
        "Your context register, system description and risk suggestions.",
        core=True,
    ),
    Question(
        "industry",
        "about",
        "Industry",
        "one",
        "Which sector rules we show you, and risk suggestions.",
        core=True,
        options=(
            ("software", "Software and SaaS"),
            ("financial_services", "Financial services"),
            ("payments", "Payments"),
            ("insurance", "Insurance"),
            ("healthcare", "Healthcare"),
            ("telecom", "Telecoms"),
            ("energy_utilities", "Energy and utilities"),
            ("government_supplier", "Government supplier"),
            ("manufacturing_devices", "Manufacturing and devices"),
            ("retail_ecommerce", "Retail and e commerce"),
            ("education", "Education"),
            ("professional_services", "Professional services"),
            ("other", "Other"),
        ),
    ),
    Question(
        "customer_types",
        "about",
        "Who are your customers?",
        "many",
        "Which sector rules we show you, and prompts for what you promise customers.",
        options=(
            ("businesses", "Businesses"),
            ("consumers", "Consumers"),
            ("government", "Government or defence"),
            ("banks_insurers", "Banks and insurers"),
            ("healthcare_providers", "Hospitals and health plans"),
            ("car_makers", "Car makers"),
        ),
    ),
    Question(
        "headcount_band",
        "about",
        "How many people work for you?",
        "one",
        "Workforce tasks, size thresholds in the rules we show you, audit time.",
        core=True,
        options=(
            ("1_10", "1 to 10"),
            ("11_50", "11 to 50"),
            ("51_200", "51 to 200"),
            ("201_500", "201 to 500"),
            ("501_1000", "501 to 1,000"),
            ("over_1000", "More than 1,000"),
        ),
    ),
    Question(
        "revenue_band",
        "about",
        "Annual revenue, in US dollars",
        "one",
        "Size thresholds in the rules we show you.",
        options=(
            ("under_1m", "Under 1 million"),
            ("1m_10m", "1 to 10 million"),
            ("10m_50m", "10 to 50 million"),
            ("50m_250m", "50 to 250 million"),
            ("over_250m", "Over 250 million"),
        ),
    ),
    Question(
        "fiscal_year_end",
        "about",
        "Month your financial year ends",
        "month",
        "Review and audit timing, and SOC 1 guidance.",
    ),
    Question(
        "oversight_body",
        "about",
        "Who oversees management?",
        "one",
        "The wording of your governance controls.",
        options=(
            ("independent_board", "A board with independent members"),
            ("executive_team", "The executive team only"),
        ),
    ),
    # -- where -------------------------------------------------------------------
    Question(
        "hq_country",
        "where",
        "Where is the company registered?",
        "country",
        "Your documents, your legal register and the rules we show you.",
        core=True,
    ),
    Question(
        "operating_countries",
        "where",
        "Where do you have staff or offices?",
        "countries",
        "The rules we show you and people security wording.",
        core=True,
    ),
    Question(
        "uae_zones",
        "where",
        "In the United Arab Emirates, where are you set up?",
        "many",
        "Which UAE data protection law we show you.",
        core=True,
        options=(("onshore", "Onshore"), ("difc", "DIFC"), ("adgm", "ADGM")),
        show_if=(
            ShowIf("operating_countries", contains="AE"),
            ShowIf("hq_country", equals=("AE",)),
        ),
    ),
    Question(
        "customer_regions",
        "where",
        "Where are your customers and the people whose data you hold?",
        "regions",
        "Laws that reach you from abroad, and privacy suggestions.",
        core=True,
    ),
    Question(
        "data_hosting_regions",
        "where",
        "Where is customer data stored?",
        "regions",
        "Data location rules and your system description.",
    ),
    # -- how ---------------------------------------------------------------------
    Question(
        "workforce_types",
        "how",
        "Employees, contractors or both?",
        "one",
        "Whether contractor controls apply.",
        core=True,
        options=(
            ("employees", "Employees"),
            ("contractors", "Contractors"),
            ("both", "Both"),
        ),
    ),
    Question(
        "work_arrangement",
        "how",
        "Office, hybrid or fully remote?",
        "one",
        "Your remote working policy and related controls.",
        core=True,
        options=(("office", "Office"), ("hybrid", "Hybrid"), ("remote", "Fully remote")),
    ),
    Question(
        "offices",
        "how",
        "Do you have offices?",
        "one",
        "Physical security controls and the office policy.",
        core=True,
        options=(
            ("none", "No offices"),
            ("managed_shared", "A managed or shared office"),
            ("own_premises", "Our own premises"),
        ),
    ),
    Question(
        "own_server_sites",
        "how",
        "Do you run your own data centre, server room or comms cabinet?",
        "tri",
        "Site and equipment protection controls.",
        core=True,
        options=TRI,
    ),
    Question(
        "device_model",
        "how",
        "Whose laptops and phones do people use for work?",
        "one",
        "Device security guidance.",
        options=(
            ("company", "Company devices"),
            ("personal", "Personal devices"),
            ("both", "Both"),
        ),
    ),
    # -- systems -----------------------------------------------------------------
    Question(
        "builds_software",
        "systems",
        "Do you build software or scripts in house?",
        "tri",
        "Whether development controls apply.",
        core=True,
        options=TRI,
    ),
    Question(
        "outside_developers",
        "systems",
        "Do outside developers write code for you?",
        "tri",
        "Outsourced development controls.",
        options=TRI,
    ),
    Question(
        "hosting_providers",
        "systems",
        "Where do your systems run?",
        "many",
        "Systems to connect, and suppliers your auditor will ask about.",
        core=True,
        options=(
            ("aws", "Amazon Web Services"),
            ("azure", "Microsoft Azure"),
            ("gcp", "Google Cloud"),
            ("other_cloud", "Another cloud provider"),
            ("own_hardware", "Our own hardware"),
        ),
    ),
    Question(
        "identity_provider",
        "systems",
        "How do staff sign in to company systems?",
        "one",
        "Systems to connect.",
        options=(
            ("google_workspace", "Google Workspace"),
            ("microsoft_entra", "Microsoft Entra ID"),
            ("okta", "Okta"),
            ("jumpcloud", "JumpCloud"),
            ("other", "Something else"),
            (NONE_VALUE, "No central sign in"),
        ),
    ),
    Question(
        "public_app",
        "systems",
        "Do you run an application open to the internet?",
        "tri",
        "Web application protection controls.",
        options=TRI,
    ),
    Question(
        "ai_use",
        "systems",
        "Do you use or build AI?",
        "one",
        "Risk suggestions, AI rules we show you, and AI points your auditor may ask about.",
        core=True,
        options=(
            (NONE_VALUE, "No"),
            ("staff_tools", "Staff use AI tools"),
            ("product_affects_people", "Our product uses AI that affects people"),
            ("builds_ai", "We build AI systems"),
        ),
    ),
    Question(
        "connected_products",
        "systems",
        "Do you make or sell connected devices?",
        "tri",
        "Product security rules we show you.",
        options=TRI,
    ),
    # -- data --------------------------------------------------------------------
    Question(
        "personal_data_role",
        "data",
        "Whose personal data do you hold?",
        "one",
        "Privacy controls and whether to suggest the privacy category.",
        core=True,
        options=(
            ("staff_only", "Only our staff's"),
            ("controller", "Customers' data we decide how to use"),
            ("processor", "Data we process for our customers"),
            ("both", "Both of these"),
        ),
    ),
    Question(
        "sensitive_data",
        "data",
        "Do you handle any of these?",
        "many",
        "Extra guidance in your controls and the rules we show you.",
        core=True,
        options=(
            ("health", "Health data"),
            ("card_stored", "Payment card data we store or process"),
            ("card_outsourced", "Payment cards fully handled by a payment provider"),
            ("children", "Children's data"),
            ("biometric", "Biometric data"),
            ("government_classified", "Government classified data"),
            (NONE_VALUE, "None of these"),
        ),
    ),
    Question(
        "shares_with_subprocessors",
        "data",
        "Do you pass customer data to other companies?",
        "tri",
        "Subprocessor controls, checked against your vendor list.",
        options=TRI,
    ),
    # -- regulation --------------------------------------------------------------
    Question(
        "regulator_licences",
        "regulation",
        "Do you hold a licence from a regulator?",
        "many",
        "Sector rules we show you.",
        options=(
            ("financial", "Financial"),
            ("payments", "Payments"),
            ("insurance", "Insurance"),
            ("telecom", "Telecoms"),
            ("health", "Health"),
            (NONE_VALUE, "No licence"),
        ),
        show_if=(
            ShowIf(
                "industry",
                equals=("financial_services", "payments", "insurance", "telecom", "healthcare"),
            ),
        ),
    ),
    Question(
        "critical_or_provider",
        "regulation",
        "Are you critical infrastructure, or a cloud, data centre or managed service provider?",
        "tri",
        "Critical infrastructure and provider rules we show you.",
        options=TRI,
    ),
    Question(
        "listed_us",
        "regulation",
        "Are your shares or debt listed on a US exchange?",
        "tri",
        "Disclosure rules we show you.",
        options=TRI,
        show_if=(ShowIf("industry", equals=("financial_services", "payments", "insurance")),),
    ),
    Question(
        "affects_customer_financial_reporting",
        "regulation",
        "Do your services affect your customers' financial reporting?",
        "tri",
        "Whether we show SOC 1 guidance.",
        core=True,
        options=TRI,
    ),
    Question(
        "verity_performs_controls",
        "regulation",
        "Will Verity run control activities for you, such as monitoring or vendor reviews?",
        "tri",
        "A note on whether to list Verity as a supplier in your audit.",
        options=TRI,
    ),
)

BY_KEY: Final[dict[str, Question]] = {q.key: q for q in QUESTIONS}


def _fail(question: Question, message: str) -> InvalidInput:
    return InvalidInput(
        f"{question.label} {message}", detail=f"profile answer {question.key!r}: {message}"
    )


def _clean_one(question: Question, value: object) -> object:  # noqa: PLR0912 — one branch per kind
    allowed = {code for code, _ in question.options}
    if question.kind == "text":
        if not isinstance(value, str):
            raise _fail(question, "needs text.")
        text = value.strip()
        if len(text) > TEXT_MAX:
            raise _fail(question, f"must be {TEXT_MAX} characters or fewer.")
        return text or None
    if question.kind in {"one", "tri"}:
        if value not in allowed:
            raise _fail(question, "has an answer we do not recognise.")
        return value
    if question.kind == "month":
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 12:  # noqa: PLR2004
            raise _fail(question, "needs a month.")
        return value
    if question.kind == "country":
        if not isinstance(value, str) or not is_country(value):
            raise _fail(question, "needs a country from the list.")
        return value
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _fail(question, "needs a list.")
    unique = list(dict.fromkeys(value))
    if question.kind == "many":
        if any(v not in allowed for v in unique):
            raise _fail(question, "has an answer we do not recognise.")
        if NONE_VALUE in unique and len(unique) > 1:
            raise _fail(question, "cannot be none and something else at once.")
    elif question.kind == "countries":
        if any(not is_country(v) for v in unique):
            raise _fail(question, "needs countries from the list.")
    elif any(not is_country_or_region(v) for v in unique):
        raise _fail(question, "needs countries or regions from the list.")
    return unique or None


def merge_answers(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Apply a patch: a key sent with null removes the answer, any other value replaces it.

    Every value is checked against its question. Unknown keys are refused, so a typo in a
    client can never store an answer nothing reads.
    """
    merged = dict(current)
    for key, value in patch.items():
        question = BY_KEY.get(key)
        if question is None:
            raise InvalidInput(
                "That profile question does not exist.", detail=f"profile answer {key!r}"
            )
        cleaned = None if value is None else _clean_one(question, value)
        if cleaned is None:
            merged.pop(key, None)
        else:
            merged[key] = cleaned
    return merged


def missing_core(answers: dict[str, Any]) -> list[Question]:
    """Core questions shown for these answers that have no answer yet."""
    return [q for q in QUESTIONS if q.core and q.shown(answers) and q.key not in answers]


def core_progress(answers: dict[str, Any]) -> tuple[int, int]:
    """(answered, total) over the core questions these answers show."""
    shown = [q for q in QUESTIONS if q.core and q.shown(answers)]
    return sum(1 for q in shown if q.key in answers), len(shown)
