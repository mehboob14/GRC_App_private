# Slack

| | |
|---|---|
| Capabilities | Listed today under `alerting`. Proposed: none as an evidence source for alerting; Slack is Verity's **notification channel**, and optionally a business application whose own members are checked |
| Delivery phase | Phase 2 (signed catalogue, as an alerting provider) |
| Auth model | Notifications: Verity's Slack app, OAuth v2 install, bot token with `chat:write` [K23] [K20]. Optional member evidence: an admin's or owner's user token with `users:read` (only admins see the two factor field) [K4] |
| Shares setup with | Verity's notification settings (where workspace admins choose channels) |
| Go library | None official: Slack's official SDKs are Java, JavaScript (Node), Python and Deno [K32]. `github.com/slack-go/slack` is listed as community developed [K33]. Notification sending lives in the Python core, not in a Go collector, so no Go library is needed |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Honestly, very little about whether a control operated.

| Question | What Slack can show | Verdict |
|---|---|---|
| Did an alert page the person on call? | Slack has no schedules, escalation or acknowledgement. A message in a channel can sit unread | Not evidence for `alerts.*`. Use PagerDuty |
| Does the workspace require two factor? | The setting exists on every plan [K6], but no API found returns it: `team.info` and `team.preferences.list` do not include it [K1] [K5] (rechecked 2026-11-23: `team.preferences.list` returns only `display_real_names`, `disable_file_uploads`, `msg_edit_window_mins` and `who_can_post_general`, and Enterprise `admin.teams.settings.info` documents no two factor field [K14]; that no method exists stays unverified because an absence cannot be shown) | Cannot be checked by API. A screenshot stays the evidence |
| Does each member use two factor? | `users.list` returns `has_2fa` and `two_factor_type`, visible only when the caller is an admin [K3] [K4]. On Enterprise, `admin.users.list` also returns `has_sso` [K15] | Possible, with an admin's user token. Useful only where Slack is outside single sign on |
| What is the retention setting? | Retention exists on all plans [K12]; on Enterprise only, per channel custom retention can be read [K16]. No workspace level read API found (unverified; `admin.teams.settings.info` documents no retention field [K14]) | Not checkable outside Enterprise, and only partly there |
| Are security settings changes recorded? | The Audit Logs API (Enterprise only, two years of history since 30 April 2026) records two factor, SSO and retention setting changes, sign ins and role changes [K17] [K18] [K19] | Enterprise only; not planned |
| Was a security message sent to staff? | `chat.postMessage` returns `ok` and a message timestamp when Slack accepted it [K20] | Proof the message was **sent**, not that anyone read it (no read receipt API found; unverified because an absence cannot be shown, and the `chat.postMessage` answer carries only `ok`, `channel`, `ts` and the message [K20]) |

What Verity should use Slack for: delivering notifications (evidence requests, failing checks,
acknowledgement campaigns, approvals) to the places people work. Delivery supports the workflow; it is
not proof that a security control operated (continuous compliance plan, section 7). The one honest
evidence use is the record that Verity sent a security message, which fills part of CS-04.D and CS-06.B
(section 6), and that record belongs to Verity's notifications, not to a Slack check.

## 2. Connecting: method, credentials and permissions

### 2.1 Notifications (recommended scope of this integration)

| Scope | Read only | Needed for | Who installs |
|---|---|---|---|
| `chat:write` | no (it posts) | posting Verity notifications to channels the app is in [K20] | a workspace member allowed to install apps; admins may require approval |
| `chat:write.public` | no | posting to public channels without joining [K20] | same |
| `channels:read`, plus `groups:read` for private channels the app was added to | yes | the channel picker (`conversations.list`, which accepts `channels:read`, `groups:read`, `im:read`, `mpim:read` and lists public channels by default) [K38] [K39] | same. Corrected 2026-11-23: was "`channels:read` (unverified that this is the minimal scope)"; without `groups:read` the picker cannot show the private channels of setup step 4 |

This is the only Verity integration that writes to the customer's system, and it writes only Verity's
own messages. That is a deliberate exception to "Verity never writes": the customer chooses the channels,
and nothing is read from conversations.

Install: OAuth v2 at `https://slack.com/oauth/v2/authorize`, code exchange at `oauth.v2.access`, bot
token `xoxb-`; the code expires in 10 minutes; tokens do not expire unless rotation is turned on [K23].
Token rotation (12 hour tokens, single use refresh tokens) cannot be turned off once on [K24];
recommended, since the core already refreshes OAuth tokens (evidence model 1.5).

Distribution: an app can be distributed without a Marketplace listing [K25]. A listing needs at least
10 active workspaces, test credentials, a demo video, a reason for each scope and a support commitment
[K26]. Unlisted commercial apps are throttled on reading message history since 29 May 2025 [K27], which
does not affect posting. Legacy custom bots lost support on 31 March 2025, and classic apps are being
retired [K28]; build a current granular scope app.

### 2.2 Member evidence (optional, not proposed for the first release)

| Scope | Read only | Needed for | Who grants |
|---|---|---|---|
| `users:read`, `users:read.email` (user token of an admin or owner) | yes | member list with `has_2fa`, roles, deactivated state [K3] [K4] | the admin or owner whose token it is |
| `team:read`, `team.billing:read` | yes | workspace name and plan (`free`, `std`, `plus`, `enterprise`) [K1] [K2] | same |
| `admin` (user token) | yes for reads | `team.accessLogs` (paid plans) [K7], `team.integrationLogs` [K9], SCIM read (Business+ and Enterprise) [K10] | admin; the `admin` scope also allows writes through SCIM, so it is not least privilege |
| `admin.users:read`, `auditlogs:read` (Enterprise, org level install by an Org Owner) | yes | per user `has_2fa` and `has_sso` [K15]; audit log [K17] | Org Owner |

A user token is tied to one admin and ends when they leave or lose the role. Vanta's Slack access
integration uses the same three scopes and the same admin requirement [K34].

### 2.3 Plans

| Feature | Free | Pro | Business+ | Enterprise | Source |
|---|---|---|---|---|---|
| Require two factor | yes | yes | yes | yes | [K6] |
| SAML single sign on | with a connected Salesforce org only | same | yes | yes | [K11] [K30] [K31] |
| SCIM | with a connected Salesforce org only | same | yes | yes | [K11] |
| Access logs | no | yes | yes | yes | [K8] [K11] |
| Audit Logs API | no | no | no | yes | [K11] [K17] |
| Custom retention | 90 days or 1 year | yes | yes | yes, org level too | [K11] [K12] |

Slack's docs say "Enterprise plan" and the pricing page "Enterprise+" [K29]. They are not one plan
renamed: Enterprise+ is a plan Slack introduced in June 2025 [K31], and the Enterprise Grid plan is being
retired, announced 3 March 2026, with no new purchase at renewals after 1 March 2027 [K40] (corrected
2026-11-23: was "whether Enterprise Grid was formally renamed is unverified"). The Enterprise only
methods above need an Enterprise organization install; which current plans give one is not stated.

## 3. Customer setup guide (draft, notifications)

1. In Verity, open **Settings**, then **Notifications**, and choose **Connect Slack**.
2. Slack shows what Verity's app may do: post messages. Approve it, or ask a workspace admin to approve
   it if your workspace requires that.
3. Back in Verity, pick a channel for each kind of notification (failing checks, evidence requests,
   approvals, acknowledgement campaigns).
4. Invite the Verity app to private channels you picked.

Verity never reads messages or files in Slack.

## 4. What Verity collects

Nothing for evidence in the recommended scope. For each message Verity posts it keeps, in its own
notifications record: channel id, time sent, Slack's `ok` answer and message timestamp [K20]. Posting is
limited to about one message per second per channel; over the limit Slack answers 429 with
`Retry-After` [K20] [K22].

If member evidence is added later: `users.list` (cursor paging, `limit` under 1,000 with 200 recommended,
Tier 2: 20 or more calls per minute) [K3]; fields `id`, `deleted`, `is_admin`, `is_owner`, `is_bot`, `has_2fa`, `two_factor_type`,
email [K4].

## 5. Checks

| Check | Slack | Why |
|---|---|---|
| `alerts.security_routed` | N | A channel is not an on call rotation; nothing escalates if nobody reads it |
| `alerts.acknowledged_in_time` | N | Slack has no acknowledgement of an alert |
| `alerts.incidents_resolved` | N | Slack has no incident record. Incident channels hold conversation, which Verity does not read |
| any `alerts.*` new check | N | Same reasons |

No new check is proposed in the operations prefixes. Two needs go to other prefixes
([operations-checks.md](operations-checks.md) section 6):

| Need | Population | Predicate | Controls |
|---|---|---|---|
| NEED business application (Slack): members use a second factor or SSO | Active, non bot members, read with an admin's user token | `has_2fa` true, or (Enterprise) `has_sso` true | IAM-04 partial (the safeguard for an application outside single sign on, IAM-04.C), IAM-03 partial |
| NEED verity (notifications): security messages Verity sent | Security messages sent by Verity in the period (policy changes, incident notices to staff) | Each has a delivery record with channel, time and provider message id | CS-04 partial (CS-04.D), CS-06 partial (CS-06.B) |

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `sample-of-messages-sent-under-the` | CS-04.D, CS-06.B, CS-06.C | CS-04, CS-06 | person + Verity notifications delivery log (module, partial: sent, not read or understood). Only for messages Verity itself sends |
| `approved-exceptions-for-applications-outside-single` | IAM-04.C | IAM-04 | person + the Slack member second factor need (partial), only if member evidence is built |

## 7. Framework reach

Through the needs above only: SOC 2 CC2.2 (CS-04; CS-06 has no SOC 2 mapping), CC6.1 (IAM-03,
IAM-04). ISO 27001:2022: clauses 5.2, 7.3 and 7.4, A.5.1 and A.6.3 (CS-04, CS-06), A.8.5 (IAM-03,
IAM-04). All partial. Nothing reaches CC7 (detection and response).

## 8. Limits and false assurance traps

- **A posted message is not a page.** Treating a Slack alert channel as on call is the trap this
  document exists to name.
- **Delivery is not receipt.** `ok` means Slack stored the message.
- **Admin user tokens are personal.** Member evidence stops when that admin leaves.
- **Two factor in Slack is moot under SSO.** With SSO, Slack defers two factor to the identity
  provider [K6]; then `idp.mfa_enforced` is the evidence.

## 9. Product and UI

- **Where:** Settings, Notifications, not the evidence Connections catalogue. The catalogue card for
  Slack says "Notifications only; does not provide evidence for on call or incident response".
- **Health:** app removed (posting fails with `not_in_channel` or `channel_not_found`), token revoked;
  failed deliveries are retried and then shown in the notifications log.
- **In product guide:** no. Slack's own install screen is enough.

## 10. Implementation notes

- Posting from the Python core through the existing notifications module; respect one message per
  second per channel [K20].
- Store the bot token envelope encrypted like any credential; with rotation, refresh before the 12 hour
  expiry [K24].
- Record every send attempt and Slack's answer, so the delivery log is complete, including failures.
- Fixtures: a free test workspace; a revoked install; a private channel without the app.

## 11. How comparable platforms do it

| Platform | Use | Auth | Evidence |
|---|---|---|---|
| Vanta | Two integrations: Slack Access (read only users and their second factor) and the Vanta Slack app (notifications, agent, Trust Center approvals) | Access: OAuth by an admin or owner, `team:read`, `users:read`, `users:read.email` | Tests "MFA on Slack" and Slack accounts linked to people [K34] |
| Drata | Notifications (posts messages only) and optional user access review | OAuth install; one workspace | Users and roles for access review; no second factor evidence [K35] |
| Secureframe | Personnel and access sync, tasks sent to Slack | not public (unverified) | access sync [K36] |
| Sprinto | Users and roles for offboarding; policy acknowledgement by direct message | needs a Slack admin; scopes unverified | offboarding checks; acknowledgements recorded in Sprinto [K37] |

Note on sources: the Sprinto pages carry an embedded block of instructions addressed to AI agents; it
was ignored and has no bearing on this document.

Sprinto's policy acknowledgement in Slack is worth noting for Verity's acknowledgement campaigns: the
acknowledgement is recorded in the compliance tool, with Slack only carrying the prompt. That is the
same boundary proposed here.

## 12. Sources

- [K1] https://docs.slack.dev/reference/methods/team.info
- [K2] https://docs.slack.dev/reference/methods/team.billing.info
- [K3] https://docs.slack.dev/reference/methods/users.list
- [K4] https://docs.slack.dev/reference/objects/user-object
- [K5] https://docs.slack.dev/reference/methods/team.preferences.list
- [K6] https://slack.com/help/articles/212221668-Mandatory-workspace-two-factor-authentication-
- [K7] https://docs.slack.dev/reference/methods/team.accessLogs
- [K8] https://slack.com/help/articles/360002084807-View-access-logs-for-your-workspace
- [K9] https://docs.slack.dev/reference/methods/team.integrationLogs
- [K10] https://docs.slack.dev/admins/scim-api, https://docs.slack.dev/reference/scim-api
- [K11] https://slack.com/help/articles/115003205446-Slack-plans-and-features
- [K12] https://slack.com/help/articles/203457187-Customize-data-retention-in-Slack
- [K13] https://docs.slack.dev/reference/scopes/admin.teams.read/
- [K14] https://docs.slack.dev/reference/methods/admin.teams.settings.info
- [K15] https://docs.slack.dev/reference/methods/admin.users.list
- [K16] https://docs.slack.dev/reference/methods/admin.conversations.getCustomRetention
- [K17] https://docs.slack.dev/admins/audit-logs-api
- [K18] https://docs.slack.dev/reference/audit-logs-api/methods-actions-reference
- [K19] https://slack.com/help/articles/360000394286-Audit-logs-in-Slack
- [K20] https://docs.slack.dev/reference/methods/chat.postMessage
- [K21] https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks
- [K22] https://docs.slack.dev/apis/web-api/rate-limits
- [K23] https://docs.slack.dev/authentication/installing-with-oauth
- [K24] https://docs.slack.dev/authentication/using-token-rotation
- [K25] https://docs.slack.dev/distribution
- [K26] https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide
- [K27] https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/
- [K28] https://docs.slack.dev/changelog/2024-09-legacy-custom-bots-classic-apps-deprecation/
- [K29] https://slack.com/pricing
- [K30] https://slack.com/help/articles/203772216-Set-up-SAML-single-sign-on-for-Slack
- [K31] https://slack.com/help/articles/39264531104275-Updates-to-feature-availability-and-pricing-for-Slack-plans
- [K32] https://docs.slack.dev/tools
- [K33] https://docs.slack.dev/tools/community-developed-tools/
- [K34] https://help.vanta.com/en/articles/15971608-connecting-vanta-slack-access, https://help.vanta.com/en/articles/11345744-setting-up-and-using-the-vanta-slack-app
- [K35] https://help.drata.com/en/articles/6425963-slack-integration-guide-communication-and-uar
- [K36] https://support.secureframe.com/en/articles/15111544-slack
- [K37] https://docs.sprinto.com/integrations/overview/slack-integration, https://docs.sprinto.com/policies/dashboard-actions/policy-acknowledgement-in-slack
- [K38] https://docs.slack.dev/reference/methods/conversations.list
- [K39] https://docs.slack.dev/reference/scopes/groups.read
- [K40] https://slack.com/help/articles/4426294050451-Slack-feature-and-plan-retirements
