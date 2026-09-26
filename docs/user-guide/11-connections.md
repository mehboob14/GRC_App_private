# 11. Connections

## What a connection does

A connection lets Verity check a system for you, on a schedule, and attach what it
finds to the controls those checks answer. Instead of somebody screenshotting a
setting every quarter, the setting is read every day and the evidence appears on its
own.

![The connections page](images/connections.png)

## What is available today

**GitHub** is the first live connector. Later phases add identity providers, cloud
accounts, device management and ticketing. Anything marked **Soon** on this page is
not connected to real data yet.

You can register interest in a system that is not there yet using the request
option. It records what you need so it can be prioritised.

## Walkthrough: connect GitHub

1. Go to **Connections** and choose **Connect** on GitHub.
2. Give the connection a name, for example "GitHub, engineering org".
3. Paste a personal access token with read access to the organisation you want
   checked. Read only is enough, and read only is what you should use.
4. Save. Verity encrypts the credential before it is stored, and it never appears in
   a log or on a screen again.
5. The first run starts right away. After that it runs on a schedule.

> **Use a token that can only read.** Nothing in Verity needs to write to your
> source control, and a read only token limits what a mistake can cost.

## What the checks look at

The GitHub connector answers questions a SOC 2 auditor asks about how software gets
built and released, for example:

- is two factor authentication required for the organisation,
- are branch protection rules in place on the default branch,
- are pull requests reviewed before merge,
- who has administrative access,
- are secret scanning and dependency alerts switched on.

Each check maps to the controls it can support.

## Reading the results

Open a control and go to its **Automation** tab.

- **Passing** means the check ran and found what the control claims.
- **Failing** means it ran and found something else. The detail says what.
- **Needs review** means the check could not decide by itself.

The output is attached to the control as evidence, dated, so the control's evidence
list fills without anybody uploading anything. Evidence is attached at most once a
day unless the result changes, so a passing check does not bury the record in
identical copies.

## When a connection breaks

A connection whose token has expired or whose permissions were reduced shows as
unhealthy on the Connections page with the reason. The checks stop rather than
quietly report a pass. Reconnect with a fresh token and the schedule resumes.

---

Next: [Settings and administration](12-settings-and-administration.md)
