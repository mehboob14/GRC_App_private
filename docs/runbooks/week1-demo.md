# Week 1 demo script

A runnable sequence of API calls that exercises everything Week 1 shipped: an operator registers
a customer company, a trial signs itself up, people land in groups and roles, one person works
across two organisations, and the audit log shows every step. Each step names the integration
test that pins it, so this script cannot rot silently — if the test is green, the step works.

Prerequisites: the stack is up and migrated ([local-setup.md](local-setup.md)), one platform
admin is seeded and enrolled (`seed-platform-admin`), and `jq` is on the path. The API port is
8000 by default (8001 on machines where 8000 is taken — see week1-review-decisions.md, item 21).

```bash
API=http://localhost:8000/api/v1
```

## 1. The provider registers an organisation

Sign in as the operator (TOTP is mandatory on the provider plane), then register the company and
invite its first admin. The tenant stays `provisioning` until that admin accepts.

```bash
CHALLENGE=$(curl -s -X POST $API/provider/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "ops@example.com", "password": "<seeded password>"}' | jq -r .challenge_token)
OPS_TOKEN=$(curl -s -X POST $API/provider/mfa/verify \
  -H 'Content-Type: application/json' \
  -d "{\"challenge_token\": \"$CHALLENGE\", \"code\": \"<authenticator code>\"}" | jq -r .token)

TENANT=$(curl -s -X POST $API/provider/tenants \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"legal_name": "Delta Industries", "slug": "delta", "plan": "starter"}' | jq -r .id)

INVITE=$(curl -s -X POST $API/provider/tenants/$TENANT/admin-invite \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"email": "admin@delta.example", "full_name": "Delta Admin"}')
echo "$INVITE" | jq -r .accept_url   # Week 1: the inviter hands this link over (decision 15)
```

The invited admin accepts — setting their name and password — and **that acceptance is what
flips the tenant to `active`** (decision 10):

```bash
curl -s -X POST $API/auth/invitations/accept -H 'Content-Type: application/json' \
  -d "{\"token\": \"$(echo "$INVITE" | jq -r .invite_token)\",
       \"full_name\": \"Delta Admin\", \"password\": \"a-long-password-here\"}"
```

Pinned by `tests/integration/test_iam_auth.py::test_a_provider_created_tenant_activates_when_its_admin_accepts`.

## 2. A trial signs itself up

No operator involved — one transaction creates company, user, credentials, Admin membership, the
five built-in roles, and completes provisioning. Admin means TOTP before any session exists, so
the flow is signup → enroll → confirm:

```bash
CHALLENGE=$(curl -s -X POST $API/auth/signup -H 'Content-Type: application/json' \
  -d '{"company_name": "Acme Compliance", "full_name": "Founding Admin",
       "email": "founder@acme.example", "password": "orbit-mango-quartz-42"}' \
  | jq -r .challenge_token)
ENROLL=$(curl -s -X POST $API/auth/mfa/enroll -H 'Content-Type: application/json' \
  -d "{\"challenge_token\": \"$CHALLENGE\"}")
echo "$ENROLL" | jq -r .otpauth_url   # scan into an authenticator app
SESSION=$(curl -s -X POST $API/auth/mfa/confirm -H 'Content-Type: application/json' \
  -d "{\"challenge_token\": \"$CHALLENGE\", \"code\": \"<authenticator code>\"}")
ACME_TOKEN=$(echo "$SESSION" | jq -r .access_token)
```

Pinned by `test_signup_returns_the_enrollment_challenge_and_activates_the_tenant` and
`test_full_signup_matches_the_frontend_contract` (same file).

## 3. Members, groups, and roles

```bash
AUTH="Authorization: Bearer $ACME_TOKEN"

# The five built-in roles; Admin's bundle is every key that exists (decision 13).
curl -s $API/roles -H "$AUTH" | jq '.[] | {name, permission_keys}'
EMPLOYEE_ROLE=$(curl -s $API/roles -H "$AUTH" | jq -r '.[] | select(.name=="Employee") | .id')

# Invite a member; the one-time accept link comes back in the response.
INVITE=$(curl -s -X POST $API/members/invite -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"email\": \"employee@acme.example\", \"full_name\": \"Plain Employee\",
       \"role_id\": \"$EMPLOYEE_ROLE\"}")
curl -s -X POST $API/auth/invitations/accept -H 'Content-Type: application/json' \
  -d "{\"token\": \"$(echo "$INVITE" | jq -r .invite_token)\",
       \"full_name\": \"Plain Employee\", \"password\": \"delta-crimson-otter-77\"}"

# A group holds memberships, never users.
GROUP=$(curl -s -X POST $API/groups -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name": "Engineering"}' | jq -r .id)
MEMBER=$(curl -s $API/members -H "$AUTH" \
  | jq -r '.[] | select(.email=="employee@acme.example") | .membership_id')
curl -s -X POST $API/groups/$GROUP/members -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"membership_id\": \"$MEMBER\"}"

curl -s $API/members -H "$AUTH" | jq '.[] | {email, status, role_names, group_names}'
```

Pinned by `tests/integration/test_iam_management.py` (list shape, invites, groups, roles,
assignments, 403-vs-404).

## 4. One person across two organisations

Invite the Acme founder into Delta as a **time-boxed Auditor** — the guest-auditor path; the
window lands on the role assignment, and an existing user accepts with the token alone:

```bash
DELTA_TOKEN=...   # Delta admin's session from step 1's login (enroll on first login)
AUDITOR_ROLE=$(curl -s $API/roles -H "Authorization: Bearer $DELTA_TOKEN" \
  | jq -r '.[] | select(.name=="Auditor") | .id')
INVITE=$(curl -s -X POST $API/members/invite \
  -H "Authorization: Bearer $DELTA_TOKEN" -H 'Content-Type: application/json' \
  -d "{\"email\": \"founder@acme.example\", \"full_name\": \"Guest Auditor\",
       \"role_id\": \"$AUDITOR_ROLE\",
       \"valid_from\": \"2026-08-12\", \"valid_until\": \"2026-09-11\"}")
curl -s -X POST $API/auth/invitations/accept -H 'Content-Type: application/json' \
  -d "{\"token\": \"$(echo "$INVITE" | jq -r .invite_token)\"}"
```

The founder's next login answers `select_workspace` with both organisations; each selection (and
every later `POST /auth/workspaces/switch`) is a **new session, audited in the target tenant's
stream** — never a parameter on the old one:

```bash
LOGIN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email": "founder@acme.example", "password": "orbit-mango-quartz-42"}')
echo "$LOGIN" | jq '{status, workspaces: [.workspaces[] | {tenant_name, membership_id}]}'
curl -s -X POST $API/auth/workspaces/select -H 'Content-Type: application/json' \
  -d "{\"selection_token\": \"$(echo "$LOGIN" | jq -r .selection_token)\",
       \"membership_id\": \"<the Delta membership id>\"}"
```

Isolation is the point of the exercise: a session bound to Acme cannot see the founder's own
Delta membership, Delta's groups, or Delta's role assignments. Pinned by
`test_an_existing_user_is_invited_into_a_second_tenant_time_boxed`,
`test_workspace_switch_issues_a_new_session_audited_in_the_target_stream`, and
`tests/isolation/test_iam_isolation.py::test_a_user_in_both_tenants_cannot_see_their_own_b_membership`.

## 5. The audit log shows every action

```bash
curl -s "$API/audit-log?limit=50" -H "$AUTH" \
  | jq '.items[] | {occurred_at, actor_type, action, object_type}'
```

Every step above is there: the tenant creation, each user / credentials / membership creation,
the five role seeds, the Admin assignment, each completed login as `create` on `session` (the
object id is the token's `jti`), the invite, the acceptance, the group add — and any failed
password or TOTP attempt as `create` on `auth_attempt`, with no email address in the snapshot.
Pinned by `tests/integration/test_audit_route.py` and the session/attempt assertions across
`test_iam_auth.py`.
