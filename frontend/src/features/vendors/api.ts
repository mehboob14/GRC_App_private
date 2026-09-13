import { ApiError, apiFetch } from "@/lib/api/client";
import type {
  Approver,
  Assessment,
  Condition,
  Contract,
  ContractInput,
  ContactInput,
  DecisionInput,
  DocumentInput,
  DuplicateMatch,
  EngagementInput,
  Finding,
  FindingPage,
  IntakeInput,
  IntakePage,
  IntakeRequest,
  IssuedQuestionnaire,
  OffboardingCompletionInput,
  Portal,
  Roster,
  SocReview,
  SocReviewInput,
  SubprocessorInput,
  TieringInput,
  VendorCreateInput,
  VendorDetail,
  VendorDocument,
  VendorFacets,
  VendorFilters,
  VendorInput,
  VendorPage,
  VendorSort,
  VendorSummary,
  Subprocessor,
} from "./types";

/**
 * Data layer for the vendors module, wired to the real backend.
 *
 * `apiFetch` prefixes `/api/v1` itself, so every path here is written without
 * it. Nineteen of these routes return the whole `VendorDetail`; seed the detail
 * cache with what comes back rather than refetching.
 */

// -- register -----------------------------------------------------------------

function query(filters: Partial<VendorFilters>, page: number, pageSize: number): string {
  const p = new URLSearchParams();
  if (filters.search) p.set("search", filters.search);
  if (filters.vendor_type && filters.vendor_type !== "all") p.set("vendor_type", filters.vendor_type);
  for (const s of filters.statuses ?? []) p.append("statuses", s);
  for (const t of filters.tiers ?? []) p.append("tiers", t);
  for (const c of filters.classifications ?? []) p.append("classifications", c);
  for (const b of filters.business_units ?? []) p.append("business_units", b);
  if (filters.owner) p.set("owner", filters.owner);
  // Only `true` is a filter: the backend reads false as "no filter", so there is
  // deliberately no way to ask for vendors that do NOT store personal data.
  if (filters.stores_pii) p.set("stores_pii", "true");
  for (const a of filters.attention ?? []) p.append("attention", a);
  p.set("page", String(page));
  p.set("page_size", String(pageSize));
  return `?${p.toString()}`;
}

export async function listVendors(
  filters: Partial<VendorFilters> = {},
  page = 1,
  pageSize = 25,
  sort: VendorSort | null = null,
  direction: "asc" | "desc" = "asc",
): Promise<VendorPage> {
  // Omitting `sort` keeps the server's risk ranking: worst tier first, untiered
  // immediately after critical, then unowned, then alphabetical.
  const suffix = sort ? `&sort=${sort}&direction=${direction}` : "";
  return apiFetch<VendorPage>(`/vendors${query(filters, page, pageSize)}${suffix}`);
}

/** The portfolio picture the overview reads. One round trip, whole tenant. */
export async function getSummary(): Promise<VendorSummary> {
  return apiFetch<VendorSummary>("/vendors/summary");
}

export async function getFacets(): Promise<VendorFacets> {
  return apiFetch<VendorFacets>("/vendors/facets");
}

/** Called as the name is typed, so the warning arrives before the record does. */
export async function checkDuplicates(name: string, website?: string | null): Promise<DuplicateMatch[]> {
  const p = new URLSearchParams({ name });
  if (website) p.set("website", website);
  const out = await apiFetch<{ matches: DuplicateMatch[] }>(`/vendors/duplicate-check?${p.toString()}`);
  return out.matches;
}

export async function createVendor(body: VendorCreateInput): Promise<VendorDetail> {
  return apiFetch<VendorDetail>("/vendors", { method: "POST", body: JSON.stringify(body) });
}

export async function getVendor(id: string): Promise<VendorDetail | null> {
  try {
    return await apiFetch<VendorDetail>(`/vendors/${id}`);
  } catch (e) {
    // A vendor that isn't there is an empty state, not an error the page throws on.
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

/** A full replacement, despite the verb: the body is the whole `VendorWrite`,
 *  so send every field you want kept, not only the ones that changed. */
export async function updateVendor(id: string, body: VendorInput): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${id}`, { method: "PATCH", body: JSON.stringify(body) });
}

export async function addEngagement(vendorId: string, body: EngagementInput): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/engagements`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Also a full replacement. Tier and status are derived server-side and are
 *  not accepted here — sending either is an extra field and 422s the request. */
export async function updateEngagement(
  vendorId: string,
  engagementId: string,
  body: EngagementInput,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/engagements/${engagementId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function addContact(vendorId: string, body: ContactInput): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/contacts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type Member = { membership_id: string; name: string };

/**
 * Tenant members for the owner and approver pickers. Served by IAM, not by this
 * module, so it needs `members:read` — a vendors-only role sees an empty list
 * and every picker degrades to the ids it already holds rather than breaking.
 */
export async function listMembers(): Promise<Member[]> {
  const rows = await apiFetch<{ membership_id: string; full_name: string }[]>("/members");
  return rows.map((m) => ({ membership_id: m.membership_id, name: m.full_name }));
}

// -- tiering and the lifecycle ------------------------------------------------

/**
 * Scores the engagement AND materialises its whole stage list in one
 * transaction. The client never sends a score or a tier — both are computed
 * server-side from the five answers.
 */
export async function tierEngagement(
  vendorId: string,
  engagementId: string,
  body: TieringInput,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/engagements/${engagementId}/tiering`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// The three transitions are keyed on the STAGE row, not the engagement: an
// engagement can have several cycles, and each cycle has its own twelve rows.

export async function advanceStage(
  vendorId: string,
  stageId: string,
  note?: string | null,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/stages/${stageId}/advance`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

/** `to_stage` is a stage code (`"tiering"`), and the reason is not optional. */
export async function sendBackStage(
  vendorId: string,
  stageId: string,
  toStage: string,
  reason: string,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/stages/${stageId}/send-back`, {
    method: "POST",
    body: JSON.stringify({ to_stage: toStage, reason }),
  });
}

export async function skipStage(
  vendorId: string,
  stageId: string,
  reason: string,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/stages/${stageId}/skip`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// -- questionnaire, assessment, findings --------------------------------------

/**
 * The response carries `portal_url`, which is the only copy of the token that
 * will ever exist — the row stores a hash. Show it once and offer a copy.
 */
export async function issueQuestionnaire(
  vendorId: string,
  engagementId: string,
  body: { contact_id?: string | null; due_date?: string | null; bank_code?: string },
): Promise<IssuedQuestionnaire> {
  return apiFetch<IssuedQuestionnaire>(
    `/vendors/${vendorId}/engagements/${engagementId}/questionnaire`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function getAssessment(vendorId: string, assessmentId: string): Promise<Assessment> {
  return apiFetch<Assessment>(`/vendors/${vendorId}/assessments/${assessmentId}`);
}

export async function scoreAssessment(vendorId: string, assessmentId: string): Promise<Assessment> {
  return apiFetch<Assessment>(`/vendors/${vendorId}/assessments/${assessmentId}/score`, {
    method: "POST",
  });
}

export async function openReassessment(vendorId: string, engagementId: string): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/engagements/${engagementId}/reassess`, {
    method: "POST",
  });
}

export async function listFindings(params: {
  vendor_id?: string;
  statuses?: string[];
} = {}): Promise<FindingPage> {
  const p = new URLSearchParams();
  if (params.vendor_id) p.set("vendor_id", params.vendor_id);
  for (const s of params.statuses ?? []) p.append("statuses", s);
  const s = p.toString();
  return apiFetch<FindingPage>(`/vendors/findings${s ? `?${s}` : ""}`);
}

export async function remediateFinding(
  vendorId: string,
  findingId: string,
  ownerMembershipId?: string | null,
): Promise<Finding> {
  return apiFetch<Finding>(`/vendors/${vendorId}/findings/${findingId}/remediate`, {
    method: "POST",
    body: JSON.stringify({ owner_membership_id: ownerMembershipId ?? null }),
  });
}

export async function acceptFinding(
  vendorId: string,
  findingId: string,
  until: string,
  rationale: string,
): Promise<Finding> {
  return apiFetch<Finding>(`/vendors/${vendorId}/findings/${findingId}/accept`, {
    method: "POST",
    body: JSON.stringify({ until, rationale }),
  });
}

export async function closeFinding(
  vendorId: string,
  findingId: string,
  note?: string | null,
): Promise<Finding> {
  return apiFetch<Finding>(`/vendors/${vendorId}/findings/${findingId}/close`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

// -- the decision -------------------------------------------------------------

export async function listApprovers(vendorId: string, engagementId: string): Promise<Approver[]> {
  const out = await apiFetch<{ items: Approver[] }>(
    `/vendors/${vendorId}/engagements/${engagementId}/approvers`,
  );
  return out.items;
}

export async function decideGate(
  vendorId: string,
  engagementId: string,
  body: DecisionInput,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/engagements/${engagementId}/decision`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function closeCondition(
  vendorId: string,
  conditionId: string,
  status: string,
  waivedReason?: string | null,
): Promise<Condition> {
  return apiFetch<Condition>(`/vendors/${vendorId}/conditions/${conditionId}`, {
    method: "POST",
    body: JSON.stringify({ status, waived_reason: waivedReason ?? null }),
  });
}

// -- paperwork ----------------------------------------------------------------

export async function addDocument(vendorId: string, body: DocumentInput): Promise<VendorDocument> {
  return apiFetch<VendorDocument>(`/vendors/${vendorId}/documents`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function reviewSocReport(vendorId: string, body: SocReviewInput): Promise<SocReview> {
  return apiFetch<SocReview>(`/vendors/${vendorId}/soc-reviews`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function addContract(vendorId: string, body: ContractInput): Promise<Contract> {
  return apiFetch<Contract>(`/vendors/${vendorId}/contracts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Returns the whole subprocessor list, not just the row that was added. */
export async function addSubprocessor(
  vendorId: string,
  body: SubprocessorInput,
): Promise<Subprocessor[]> {
  const out = await apiFetch<{ items: Subprocessor[] }>(`/vendors/${vendorId}/subprocessors`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return out.items;
}

// -- intake and roster --------------------------------------------------------

export async function listIntake(decision?: string | null): Promise<IntakePage> {
  return apiFetch<IntakePage>(`/vendors/intake${decision ? `?decision=${decision}` : ""}`);
}

/** Needs only `vendors:read` — anyone who can see the register may ask for a vendor. */
export async function requestVendor(body: IntakeInput): Promise<IntakeRequest> {
  return apiFetch<IntakeRequest>("/vendors/intake", { method: "POST", body: JSON.stringify(body) });
}

export async function decideIntake(
  requestId: string,
  approve: boolean,
  reason?: string | null,
): Promise<IntakeRequest> {
  return apiFetch<IntakeRequest>(`/vendors/intake/${requestId}/decide`, {
    method: "POST",
    body: JSON.stringify({ approve, reason: reason ?? null }),
  });
}

export async function getRoster(): Promise<Roster> {
  return apiFetch<Roster>("/vendors/roster");
}

export async function setRosterRole(role: string, membershipId: string): Promise<Roster> {
  return apiFetch<Roster>("/vendors/roster", {
    method: "POST",
    body: JSON.stringify({ role, membership_id: membershipId }),
  });
}

// -- the exit -----------------------------------------------------------------

/** Omit `engagement_id` to end the whole relationship rather than one engagement. */
export async function offboard(
  vendorId: string,
  reason: string,
  engagementId?: string | null,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/offboarding`, {
    method: "POST",
    body: JSON.stringify({ reason, engagement_id: engagementId ?? null }),
  });
}

export async function completeOffboarding(
  vendorId: string,
  offboardingId: string,
  body: OffboardingCompletionInput,
): Promise<VendorDetail> {
  return apiFetch<VendorDetail>(`/vendors/${vendorId}/offboarding/${offboardingId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// -- the vendor portal --------------------------------------------------------
//
// These four are the only unauthenticated calls in the app, and they
// deliberately bypass `apiFetch`. It attaches whatever bearer token is in
// storage, and a 401 on a request that carried one clears the session and
// redirects — so an internal user who happens to be signed in and opens a
// portal link would be signed out by someone else's expired token.
//
// Every failure mode here — bad token, expired, revoked, rate-limited — comes
// back as one indistinguishable error by design. Do not branch on it.

const PORTAL_BASE = "/api/v1/vendor-portal";

export class PortalError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "PortalError";
    this.status = status;
  }
}

async function portalFetch(path: string, init?: RequestInit): Promise<Portal> {
  let response: Response;
  try {
    response = await fetch(`${PORTAL_BASE}${path}`, {
      ...init,
      headers:
        init?.body instanceof FormData
          ? undefined
          : { "Content-Type": "application/json", Accept: "application/json" },
    });
  } catch {
    throw new PortalError(0, "Can't reach the questionnaire. Check your connection, then try again.");
  }
  if (!response.ok) {
    // The server's message is written for this reader (a refused file type, a
    // missing reason, a dead link), so show it. The fallbacks cover a body that
    // is not the API's error shape, such as a proxy's own 413 page.
    const body = (await response.json().catch(() => null)) as {
      error?: { message?: string };
    } | null;
    const fallback =
      response.status === 429
        ? "Too many attempts. Wait a few minutes, then try again."
        : response.status === 413
          ? "That file is too large. Attach one under 25 MB."
          : response.status === 404
            ? "This questionnaire link is no longer valid. Ask your contact to send a new one."
            : "That did not save. Try again.";
    throw new PortalError(
      response.status,
      response.status === 429 ? fallback : (body?.error?.message ?? fallback),
    );
  }
  return (await response.json()) as Portal;
}

export async function getPortal(token: string): Promise<Portal> {
  return portalFetch(`/${token}`);
}

export async function answerPortalQuestion(
  token: string,
  body: {
    question_id: string;
    answer: string;
    implementation_notes?: string | null;
    na_justification?: string | null;
  },
): Promise<Portal> {
  return portalFetch(`/${token}/answers`, { method: "POST", body: JSON.stringify(body) });
}

/** The multipart field name is exactly `file` — the backend rejects anything else. */
export async function uploadPortalEvidence(
  token: string,
  questionId: string,
  file: File,
): Promise<Portal> {
  const form = new FormData();
  form.set("file", file);
  return portalFetch(`/${token}/answers/${questionId}/evidence`, { method: "POST", body: form });
}

export async function submitPortal(token: string): Promise<Portal> {
  return portalFetch(`/${token}/submit`, { method: "POST" });
}
