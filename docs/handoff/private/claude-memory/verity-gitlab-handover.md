---
name: verity-gitlab-handover
description: "Client GitLab repo for Verity (gitlab.com/grc3253640/verity, branch phase_01); remote `gitlab` added 2026-10-08; how snapshots are pushed"
metadata:
  node_type: memory
  type: reference
  originSessionId: d6af4007-e1d8-417f-a8c0-ccc4ae6fbc3f
  modified: 2026-11-14T09:30:32.406Z
---

Client repo: https://gitlab.com/grc3253640/verity, branch `phase_01` (invite from Faheem's side; auth works through the user's cached credentials). Local remote name `gitlab` in C:\Development\Verity_GRC_Platform.

Snapshot pushed 2026-10-08: commit 8583a4e on top of c34b94d, tree of origin/feat/phase1-completion at 371f8a7, authored mehboob14, no Claude trailer, no `website/`. GitLab history is deliberately separate from GitHub, so a plain push of a GitHub branch is rejected; push a `git commit-tree <tree> -p gitlab/phase_01` snapshot instead.

**Why:** the client gets clean history under the user's name ([[feedback-commit-attribution]]).
**How to apply:** after each batch, when the user says push to GitLab, fetch gitlab, commit-tree the current feat/phase1-completion tree on gitlab/phase_01, push. The repo also carries .agents/.claude/.cursor folders from the first snapshot.

**2026-11-06: GitLab is now the main version control** (owner's decision) after obfuscated malware was force pushed into `postcss.config` files on every GitHub branch (tips rewritten, same message and date, +0100 timezone; infected commits tagged locally `incident-2026-11-06/*`). ISO 27001 plus built-in checks pushed to GitLab as 33df5e3 from the clean local branch: `push-gitlab.bat "msg" refs/heads/feat/phase1-completion`. Never use the script's default source (origin) or pull/build from GitHub until the owner has secured the account and restored it.

2026-11-14 public check: the injection was pushed BY the mehboob14 account itself in a 3-minute burst on 2026-10-19 23:24 to 23:27 UTC (04:24 PKT) across complywerse_ai, GRC_App_private and Mehboob_Arshad, so the account's credentials (a token or a machine) were compromised. Still live on PUBLIC repos: complywerse_ai has 14 of 26 branches infected incl. main (`grc-frontend/postcss.config.js` is 6,844 or 8,312 bytes; clean is 83), and Mehboob_Arshad `eslint.config.js` line 41 is 6,760 chars. Payload starts `global.o='8-hhn8453';var _$_ee73=(function(h,o){`, hidden after `};` with padding spaces. Detect by file size via raw.githubusercontent.com (strip `\r` from branch lists on Windows).
