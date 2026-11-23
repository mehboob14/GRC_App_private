# Amazon Web Services

| | |
|---|---|
| Capabilities | cloud_infrastructure, asset_discovery |
| Delivery phase | Phase 2 (signed catalogue: "AWS (core cloud)"). CIS hardening benchmarks are listed under Phase 3.2 in `docs/product/delivery-plan.md`, see decision D-AWS-1 |
| Auth model | Cross account IAM role assumed with `sts:AssumeRole`, bound to an external ID unique to the Verity workspace; CloudFormation quick create link for one account, StackSets for an AWS Organization |
| Shares setup with | Nothing today. Sign in to Verity through AWS IAM Identity Center is not planned |
| Go library | AWS SDK for Go v2, `github.com/aws/aws-sdk-go-v2` (requires Go 1.24 or later) with `config`, `credentials/stscreds` and one module per service (`service/iam`, `service/ec2`, ...) |

## 1. What it proves

AWS is where most customers run production, so it speaks for the technical half of the network,
logging, backup and cloud identity families: whether stored data is encrypted, whether the network
lets the internet reach admin ports, whether audit trails and threat detection run in every account and
region, whether root and console users have a second factor, whether access keys rotate, whether
backups run and are protected, and which resources exist (the asset register).

It does not prove anything a person decides: that a rule has an owner and a purpose, that an alert was
investigated, that a key policy was reviewed, that a restore was checked for completeness. It also sees
only AWS. A customer with production on another cloud, or with a database outside AWS, needs another
source for those resources.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

The customer creates an IAM role in each AWS account in scope. Its trust policy names Verity's AWS
account as the principal and requires the workspace's external ID with `sts:ExternalId`. Verity calls
`sts:AssumeRole` with that external ID and receives temporary credentials. AWS recommends this over
handing a third party an IAM user's access keys, says the third party (Verity) must generate the
external ID and keep it unique per customer, and recommends one external ID per AWS account in a
multi tenant service. The external ID is not a secret. It must be 2 to 1,224 characters, alphanumeric
plus `+ = , . @ : / -`. Verity must test that it cannot assume the role without the external ID and
refuse to save a role that it can (AWS third party guidance). [S1]

Session length: `DurationSeconds` defaults to one hour and can be raised up to the role's maximum
session duration (1 to 12 hours). A run that takes longer re-assumes the role. [S2] When Verity's own
identity is itself a role session (Roles Anywhere, D-AWS-2), the assume is role chaining and each customer
session lasts one hour at most [S22].

Vendor side prerequisite: Verity needs an AWS identity of its own to call `sts:AssumeRole`. Verity runs
on a Contabo server, not on AWS, so that identity is either a long lived IAM user key in a Verity owned
AWS account (stored in the runtime secret store, rotated) or IAM Roles Anywhere with an X.509
certificate. See decision D-AWS-2. STS allows 600 requests per
second per account and Region across `AssumeRole` and related calls, counted against the account that
calls, not the customer's. [S2]

How Roles Anywhere would work for Verity (verified 2026-11-23 [S20] [S21] [S22]):

- Roles Anywhere hands out temporary credentials to a workload outside AWS that proves itself with an
  X.509 certificate. The CA behind that certificate is registered as a trust anchor. It can be an AWS
  Private CA or any external CA whose certificate Verity uploads, so a paid AWS Private CA is optional.
- The trust anchor, the profile and the role must sit in the same account and Region. So the setup lives
  in Verity's own AWS account, never in the customer's: a Verity "broker" role trusts
  `rolesanywhere.amazonaws.com` (with `sts:AssumeRole`, `sts:SetSourceIdentity`, `sts:TagSession`) and is
  tied to the trust anchor through `aws:SourceArn`. Certificates from any trust anchor in an account can
  assume any role in it that does not add conditions, so the broker role's trust policy names the anchor.
- Verity's server exchanges its certificate for broker role credentials (the `aws_signing_helper`
  credential process), then calls `sts:AssumeRole` with the external ID into each customer role. Customer
  trust policies do not change: they still name Verity's account and the external ID.
- That second step is role chaining, which caps each customer session at one hour whatever the role's
  maximum session duration says. Runs longer than an hour re-assume (as section 10 already plans).
- The private key is still a secret on the Verity server. The signing helper can keep it in a TPM or a
  PKCS#11 module so it cannot be copied off the host; a key file on disk is no better than an access key.

### 2.2 Which policy the role carries

| Option | What it grants | Verdict |
|---|---|---|
| `ReadOnlyAccess` (AWS managed, v192) | Read of nearly every service **including data**: `s3:Get*` (object contents), `dynamodb:Scan` and `dynamodb:Get*`, `logs:Get*` (log contents), `athena:GetQueryResults`, `sqs:Receive*`, `ssm:Get*` [S3] | Rejected. Verity must never be able to read customer data |
| `ViewOnlyAccess` (AWS managed job function, v49) | Lists and some describes. It lacks `iam:Get*` (no credential report), `s3:GetBucket*`, `kms:GetKeyRotationStatus`, GuardDuty and Security Hub reads [S4] | Rejected. Too narrow for the checks |
| `SecurityAudit` (AWS managed, v95, edited 13 Nov 2026) | Security configuration metadata: `iam:Get*`, `iam:List*`, `iam:GenerateCredentialReport`, `s3:GetBucket*`, `s3:GetEncryptionConfiguration`, `s3:GetLifecycleConfiguration`, `s3:GetAccountPublicAccessBlock`, `kms:Get*`, `securityhub:Get*`, `guardduty:Get*`, `config:Describe*`, `cloudtrail:DescribeTrails`, `ec2:Describe*`, `rds:Describe*`, backup lists, `secretsmanager:ListSecrets` and `DescribeSecret`, `organizations:List*`, `elasticloadbalancing:Describe*`, `cloudwatch:Describe*`, `logs:Describe*`. No `s3:GetObject`, no `secretsmanager:GetSecretValue`, no `kms:Decrypt`. It **does** include `lambda:GetFunctionConfiguration` and `ecs:Describe*`, which return environment variable values in plain text, and `cloudtrail:LookupEvents`. It also includes `ec2:Describe*` (instance and launch template user data), `codebuild:BatchGetProjects` and `rds:DownloadDBLogFilePortion` (database log contents). It does not include `resource-explorer-2:Search`, `backup:ListRestoreJobs` or `backup:ListRestoreTestingPlans` [S5] (checked against v95 on 2026-11-23) | Acceptable only with an explicit Deny on the calls that return secrets or data (below), kept current as AWS revises the policy (corrected 2026-11-23: was "one fix"). AWS maintains it, so new services are covered without a template change |
| Custom least privilege policy (Verity managed, below) | Exactly the calls the checks make, nothing that returns data or secret values | Recommended default |

The two acceptable options differ in upkeep. The custom policy must be updated (a reconnect the
customer approves, `02-integration-model.md` 2.2) whenever a check needs a new call. `SecurityAudit`
changes under AWS's control, so Verity's reach can grow without the customer seeing a new permission.
Decision D-AWS-3 picks the default.

Custom policy limits: a customer managed policy may not exceed 6,144 characters (whitespace not
counted); a role takes 20 managed policies by default (25 maximum); a role trust policy is 2,048
characters by default. [S2] The policy below fits in one managed policy.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VerityReadSecurityConfiguration",
      "Effect": "Allow",
      "Resource": "*",
      "Action": [
        "account:ListRegions",
        "acm:DescribeCertificate", "acm:ListCertificates",
        "backup:DescribeBackupVault", "backup:GetBackupPlan", "backup:GetBackupSelection",
        "backup:ListBackupJobs", "backup:ListBackupPlans", "backup:ListBackupSelections",
        "backup:ListBackupVaults", "backup:ListProtectedResources", "backup:ListRestoreJobs",
        "backup:ListRestoreTestingPlans",
        "cloudfront:ListDistributions",
        "cloudtrail:DescribeTrails", "cloudtrail:GetEventSelectors", "cloudtrail:GetTrailStatus",
        "cloudtrail:ListEventDataStores",
        "cloudwatch:DescribeAlarms",
        "config:DescribeConfigurationAggregators", "config:DescribeConfigurationRecorderStatus",
        "config:DescribeConfigurationRecorders", "config:DescribeDeliveryChannels",
        "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeTable", "dynamodb:ListTables",
        "ec2:DescribeFlowLogs", "ec2:DescribeImages", "ec2:DescribeInstances", "ec2:DescribeNetworkAcls",
        "ec2:DescribeNetworkInterfaces", "ec2:DescribeRegions", "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroupRules", "ec2:DescribeSecurityGroups", "ec2:DescribeSnapshotAttribute",
        "ec2:DescribeSnapshots", "ec2:DescribeSubnets", "ec2:DescribeVolumes", "ec2:DescribeVpcs",
        "ec2:GetEbsEncryptionByDefault", "ec2:GetImageBlockPublicAccessState",
        "ec2:GetSnapshotBlockPublicAccessState",
        "ecr:DescribeRepositories",
        "eks:ListClusters",
        "elasticfilesystem:DescribeFileSystems",
        "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeSSLPolicies",
        "guardduty:GetDetector", "guardduty:GetFindings", "guardduty:ListDetectors", "guardduty:ListFindings",
        "iam:GenerateCredentialReport", "iam:GetAccessKeyLastUsed", "iam:GetAccountAuthorizationDetails",
        "iam:GetAccountSummary", "iam:GetCredentialReport", "iam:ListAccessKeys",
        "iam:ListOrganizationsFeatures", "iam:ListVirtualMFADevices",
        "identitystore:ListGroupMemberships", "identitystore:ListGroups", "identitystore:ListUsers",
        "kms:DescribeKey", "kms:GetKeyRotationStatus", "kms:ListKeys",
        "logs:DescribeLogGroups", "logs:DescribeMetricFilters",
        "organizations:DescribeOrganization", "organizations:ListAccounts",
        "organizations:ListOrganizationalUnitsForParent", "organizations:ListParents",
        "organizations:ListRoots", "organizations:ListTagsForResource",
        "rds:DescribeDBClusterSnapshotAttributes",
        "rds:DescribeDBClusterSnapshots", "rds:DescribeDBClusters", "rds:DescribeDBInstances",
        "rds:DescribeDBSnapshotAttributes", "rds:DescribeDBSnapshots",
        "resource-explorer-2:ListIndexes", "resource-explorer-2:Search",
        "s3:GetAccountPublicAccessBlock", "s3:GetBucketLocation", "s3:GetBucketPolicyStatus",
        "s3:GetBucketPublicAccessBlock", "s3:GetBucketVersioning", "s3:GetEncryptionConfiguration",
        "s3:GetLifecycleConfiguration", "s3:ListAllMyBuckets",
        "secretsmanager:ListSecrets",
        "securityhub:DescribeHub", "securityhub:GetEnabledStandards", "securityhub:GetFindings",
        "sso:DescribePermissionSet", "sso:ListAccountAssignments", "sso:ListInstances",
        "sso:ListManagedPoliciesInPermissionSet", "sso:ListPermissionSets",
        "sso:GetInlinePolicyForPermissionSet", "sso:ListCustomerManagedPolicyReferencesInPermissionSet"
      ]
    },
    {
      "Sid": "VerityReadApiGatewayDomainNames",
      "Effect": "Allow",
      "Action": "apigateway:GET",
      "Resource": "arn:aws:apigateway:*::/domainnames"
    }
  ]
}
```

Every action name above was checked against the AWS service authorization reference on 2026-11-23, and
none is classed as a write or permission management action there [S26]. (Corrected 2026-11-23: added
`apigateway:GET` on custom domain names for `cloud.tls_in_transit`, `rds:DescribeDBClusterSnapshotAttributes`
for public Aurora snapshots in `cloud.storage_public_access_blocked`, `eks:ListClusters` for
`assets.resources_registered` without Resource Explorer, and `sso:GetInlinePolicyForPermissionSet` plus
`sso:ListCustomerManagedPolicyReferencesInPermissionSet` so `cloud.least_privilege` sees inline and
customer managed permission set policies. Lambda functions stay out of the fallback enumeration because
`lambda:ListFunctions` returns environment values; they come only from Resource Explorer.)

If `SecurityAudit` is chosen instead, the role also carries this inline statement, because those calls
return environment variable values, user data or log contents (Lambda's `GetFunctionConfiguration`
returns `Environment.Variables` [S6]; ECS container definitions carry plain text `environment` key value
pairs, which AWS advises against using for secrets [S23]):

```json
{"Sid": "VerityNeverReadsSecretValues", "Effect": "Deny", "Resource": "*",
 "Action": ["lambda:GetFunction", "lambda:GetFunctionConfiguration", "lambda:ListFunctions",
            "ecs:DescribeTaskDefinition", "cloudtrail:LookupEvents",
            "ec2:DescribeInstanceAttribute", "ec2:DescribeLaunchTemplateVersions",
            "codebuild:BatchGetProjects", "rds:DownloadDBLogFilePortion"]}
```

`lambda:ListFunctions` is denied because each item it returns includes `Environment.Variables` [S24].
`cloudtrail:LookupEvents` is denied because event records can hold request parameters Verity has no use
for. `lambda:GetFunction` is not in `SecurityAudit` (it grants `lambda:GetFunctionConfiguration` and
`lambda:List*`), so its deny is only a guard. (Corrected 2026-11-23: the deny list first named only Lambda,
ECS and LookupEvents. `SecurityAudit` v95 also grants `ec2:Describe*`, which includes
`DescribeInstanceAttribute` (returns `userData`) and `DescribeLaunchTemplateVersions` (launch template
`userData`); `codebuild:BatchGetProjects`, whose project environment variables can be of type `PLAINTEXT`;
and `rds:DownloadDBLogFilePortion`, which returns database log file entries [S5] [S25].) The list covers
what this review found, not every data returning call in the policy, and AWS adds to `SecurityAudit`
on its own schedule, so a deny list has to be re-checked against each new policy version. That is one more
reason for D-AWS-3's recommended custom policy.

### 2.3 Permissions by check

| Permission (IAM action) | Read only | Needed for (check keys) | Who can grant it |
|---|---|---|---|
| `iam:GenerateCredentialReport`, `iam:GetCredentialReport` | yes (generate writes only the report) | `cloud.root_account_mfa`, `cloud.human_users_mfa`, `cloud.machine_credentials_rotated`, `cloud.unused_credentials_disabled`, `cloud.access_list_exported` | IAM administrator in each account |
| `iam:GetAccountSummary`, `iam:ListVirtualMFADevices`, `iam:ListOrganizationsFeatures` (name confirmed [S26]; it answers only in the management account or the IAM delegated administrator account and fails elsewhere with `AccountNotManagementOrDelegatedAdministratorException` [S27]) | yes | `cloud.root_account_mfa` | IAM administrator |
| `iam:GetAccountAuthorizationDetails`, `iam:ListAccessKeys`, `iam:GetAccessKeyLastUsed` | yes | `cloud.least_privilege`, `cloud.machine_credentials_rotated`, `cloud.access_list_exported` | IAM administrator |
| `sso:List*` and `sso:Get*` above, `identitystore:List*` above | yes | `cloud.least_privilege`, `cloud.access_list_exported`, `cloud.human_users_mfa` (Identity Center users, partial) | Management account or Identity Center delegated administrator |
| `organizations:*` above | yes | `cloud.environments_separated`, account discovery for every check | Management account or Organizations delegated administrator |
| `account:ListRegions`, `ec2:DescribeRegions` | yes | region discovery for every regional check | IAM administrator |
| `s3:*` above | yes | `cloud.encryption_at_rest`, `cloud.storage_public_access_blocked`, `cloud.storage_versioned`, `cloud.storage_lifecycle`, `cloud.audit_logging` (trail bucket) | IAM administrator |
| `rds:*`, `dynamodb:*`, `elasticfilesystem:DescribeFileSystems`, `ec2:DescribeVolumes`, `ec2:DescribeSnapshots`, `ec2:GetEbsEncryptionByDefault` | yes | `cloud.encryption_at_rest`, `cloud.backups_enabled`, `cloud.network_segmented` | IAM administrator |
| `ec2:DescribeSnapshotAttribute`, `ec2:GetSnapshotBlockPublicAccessState`, `ec2:GetImageBlockPublicAccessState`, `ec2:DescribeImages`, `rds:DescribeDBSnapshotAttributes`, `rds:DescribeDBClusterSnapshotAttributes` | yes | `cloud.storage_public_access_blocked` | IAM administrator |
| `ec2:DescribeSecurityGroups`, `DescribeSecurityGroupRules`, `DescribeNetworkInterfaces`, `DescribeNetworkAcls` | yes | `cloud.default_deny_ingress`, `cloud.admin_ports_closed` | IAM administrator |
| `ec2:DescribeVpcs`, `DescribeSubnets`, `DescribeRouteTables`, `DescribeInstances` | yes | `cloud.network_segmented`, `assets.resources_registered` | IAM administrator |
| `ec2:DescribeFlowLogs` | yes | `cloud.flow_logs_enabled` | IAM administrator |
| `elasticloadbalancing:Describe*` above, `cloudfront:ListDistributions`, `apigateway:GET` on `/domainnames` | yes | `cloud.tls_in_transit` | IAM administrator |
| `eks:ListClusters` | yes | `assets.resources_registered` (fallback when Resource Explorer is off) | IAM administrator |
| `acm:ListCertificates`, `acm:DescribeCertificate` | yes | `cloud.tls_certificates_current` | IAM administrator |
| `kms:ListKeys`, `kms:DescribeKey`, `kms:GetKeyRotationStatus` | yes | `cloud.key_rotation` | IAM administrator |
| `secretsmanager:ListSecrets` | yes (never returns values) | `cloud.secrets_managed`, `cloud.secrets_rotated` | IAM administrator |
| `cloudtrail:DescribeTrails`, `GetTrailStatus`, `GetEventSelectors`, `ListEventDataStores` | yes | `cloud.audit_logging` | IAM administrator |
| `config:Describe*` above | yes | `cloud.config_changes_recorded` | IAM administrator |
| `logs:DescribeLogGroups`, `logs:DescribeMetricFilters`, `cloudwatch:DescribeAlarms` | yes | `cloud.capacity_alarms`, `cloud.config_changes_recorded` (alerting half), `cloud.audit_logging` (retention) | IAM administrator |
| `guardduty:ListDetectors`, `GetDetector` | yes | `cloud.threat_detection` | IAM administrator |
| `guardduty:ListFindings`, `GetFindings` | yes | `cloud.threat_findings_triaged` | IAM administrator |
| `securityhub:DescribeHub`, `GetEnabledStandards`, `GetFindings` | yes | `cloud.hardening_baseline` | IAM administrator |
| `backup:*` above | yes | `cloud.backups_enabled`, `cloud.backup_jobs_succeeding`, `cloud.backups_protected`, `cloud.restore_tested` | IAM administrator |
| `ecr:DescribeRepositories` | yes | `cloud.storage_versioned` | IAM administrator |
| `resource-explorer-2:Search`, `ListIndexes` | yes | `assets.resources_registered` | IAM administrator |

Plan or licence requirements: none for the role itself. Several checks read services the customer must
have turned on and pays for: AWS Config (needed by Security Hub CSPM controls [S7]), Security Hub CSPM,
GuardDuty, AWS Backup, Resource Explorer (free to search, but indexes must be created per Region and an
aggregator index set for cross Region search [S8]). A service that is off is a finding for the check that
asks for it (`cloud.threat_detection`), and `error` with the reason "not turned on" for a check that only
reads it as a source (`cloud.hardening_baseline` when Security Hub CSPM is off). See section 8.

## 3. Customer setup guide (draft product text)

**One account**

1. In Verity, open Integrations, choose Amazon Web Services and click **Connect**. Verity shows your
   workspace's external ID and a **Launch in AWS** button.
2. Sign in to the AWS account you want Verity to check, as someone who can create IAM roles.
3. Click **Launch in AWS**. The CloudFormation page opens with the template, the stack name and your
   external ID already filled in. Check the region shown at the top, then tick **I acknowledge that AWS
   CloudFormation might create IAM resources with custom names** and click **Create stack**.
4. When the stack shows CREATE_COMPLETE, open its **Outputs** tab and copy the role ARN.
5. Paste the role ARN into Verity and click **Check connection**. Verity confirms it can read the
   account and that the role refuses requests without your external ID.
6. Choose the accounts and regions that are in scope, mark which accounts hold production, and save.

**An AWS Organization**

1. Do steps 1 and 2 in your organization's management account (or the account you made delegated
   administrator for CloudFormation StackSets).
2. Click **Launch StackSet** in Verity. Create the StackSet with service managed permissions, target your
   organization root or the OUs in scope, turn on automatic deployment, and choose **Retain stacks** or
   **Delete stacks** for accounts that leave.
3. StackSets do not deploy into the management account itself. If the management account runs
   workloads or holds the organization's trail, also launch the single account stack there (steps 3 to 5
   above).
4. Paste the management account's role ARN into Verity. Verity lists every account in the organization
   and assumes the same role name in each one. Accounts where the role is missing show as "could not
   check" until the StackSet reaches them.

Removing access: delete the stack (or the StackSet instances). Verity's connection turns to "could not
check" on its next run, and its history stays.

Sources for these steps: quick create links take `templateURL` (an S3 hosted template), `stackName` and
`param_<Name>` values, and the console still asks the user to acknowledge IAM capabilities [S9]; service
managed StackSets deploy automatically to accounts added to target OUs, with retain or delete on removal
[S10]; StackSets skip the management account [S11].

## 4. What Verity collects

Every regional call runs in every Region that is enabled for the account and in scope. Regions come from
`account:ListRegions` or `ec2:DescribeRegions`; opt in Regions that are not enabled are skipped and
listed. EC2 throttles per account and per Region with a token bucket: non mutating calls have a bucket of
100 and refill 20 per second, and unfiltered, unpaginated `DescribeSecurityGroups`, `DescribeVolumes`,
`DescribeSnapshots`, `DescribeNetworkInterfaces` and `DescribeInstances` have a smaller bucket of 50 with
a refill of 10, so Verity always paginates them [S12]. Retries use the SDK's retry modes with backoff
and jitter; throttling past the run's budget gives `insufficient_information`, never a pass.

| Resource | API (operation, Go SDK v2 service) | Fields kept | Paging and limits | Provider retention |
|---|---|---|---|---|
| Accounts and OUs | `organizations` `ListAccounts`, `ListRoots`, `ListOrganizationalUnitsForParent`, `ListParents`, `ListTagsForResource` | id, name, status, OU path, tags | paginator | live |
| Regions | `account` `ListRegions` (opt status) or `ec2` `DescribeRegions` | name, opt in status | single call | live |
| IAM users and credentials | `iam` `GenerateCredentialReport`, `GetCredentialReport` (CSV) | user, arn, created, `password_enabled`, `password_last_used`, `mfa_active`, `access_key_1_active`, `access_key_1_last_rotated`, `access_key_1_last_used_date`, same for key 2, `additional_credentials_info` | one report per account; a new one at most every 4 hours. Only the first two keys per user are in the report, so `ListAccessKeys` covers the rest [S13] | live |
| Root account | `iam` `GetAccountSummary` (`AccountMFAEnabled`, `AccountAccessKeysPresent`), credential report `<root_account>` row, `ListVirtualMFADevices` (root serial means a virtual device), `ListOrganizationsFeatures` | MFA on, keys present, virtual or not, central root management on | single calls | live |
| Principals and policies | `iam` `GetAccountAuthorizationDetails` (`Filter` takes `User`, `Role`, `Group`, `LocalManagedPolicy`, `AWSManagedPolicy`; paged with `MaxItems` and `Marker`; policy documents come back URL encoded and must be decoded [S28]); `sso-admin` `GetInlinePolicyForPermissionSet`, `ListCustomerManagedPolicyReferencesInPermissionSet`; `sso-admin` `ListInstances`, `ListPermissionSets`, `ListAccountAssignments`; `identitystore` `ListUsers`, `ListGroups`, `ListGroupMemberships` | principal, attached managed policies, inline policy documents, permission set policies, assignments | paginators; Identity Center calls only from the management account or the one member account registered as Identity Center delegated administrator, because the organization instance lives in the management account [S29] | live |
| Storage buckets | `s3` `ListBuckets`, `GetBucketEncryption`, `GetBucketVersioning`, `GetPublicAccessBlock`, `GetBucketPolicyStatus`, `GetBucketLifecycleConfiguration`; `s3control` `GetPublicAccessBlock` (account) | name, region, created, default encryption type and key, versioning, four block public access flags (bucket and account), `IsPublic`, lifecycle expiration rules | per bucket calls; "no configuration" errors are absence, `AccessDenied` is `error` | live |
| Databases | `rds` `DescribeDBInstances`, `DescribeDBClusters`, `DescribeDBSnapshots`, `DescribeDBClusterSnapshots`, `DescribeDBSnapshotAttributes`; `dynamodb` `ListTables`, `DescribeTable`, `DescribeContinuousBackups`; `efs` `DescribeFileSystems` | id, engine, `StorageEncrypted`, key, `BackupRetentionPeriod`, `PubliclyAccessible`, subnet group, Multi AZ, snapshot restore attribute (public or not), DynamoDB point in time recovery, EFS `Encrypted` | paginators | live |
| Volumes, snapshots, images | `ec2` `GetEbsEncryptionByDefault`, `DescribeVolumes`, `DescribeSnapshots` (owner self), `DescribeSnapshotAttribute`, `GetSnapshotBlockPublicAccessState`, `GetImageBlockPublicAccessState` | encrypted, attachments, public create volume permission, block public access state | paginate always | live |
| Network | `ec2` `DescribeVpcs`, `DescribeSubnets`, `DescribeRouteTables`, `DescribeSecurityGroups`, `DescribeSecurityGroupRules`, `DescribeNetworkInterfaces`, `DescribeNetworkAcls`, `DescribeFlowLogs` | VPC (default or not), subnet routes to an internet gateway, every inbound rule (protocol, ports, CIDR v4 and v6, prefix list, referenced group), group attachments, NACL entries, flow log status and destination | paginate always | live |
| Front doors and certificates | `elasticloadbalancingv2` `DescribeLoadBalancers`, `DescribeListeners`, `DescribeSSLPolicies`; `cloudfront` `ListDistributions`; `apigateway` `GetDomainNames`; `acm` `ListCertificates`, `DescribeCertificate` | listener protocol, TLS policy and its protocols, HTTP listener redirect action, CloudFront minimum protocol version (`ViewerCertificate.MinimumProtocolVersion`, present in each `ListDistributions` summary [S30]), API Gateway custom domain `securityPolicy` (`TLS_1_0`, `TLS_1_2` or a named `SecurityPolicy_TLS13_...` policy [S31]), certificate expiry and in use | paginators | live |
| Keys | `kms` `ListKeys`, `DescribeKey`, `GetKeyRotationStatus` | manager (AWS or customer), state, spec, origin, rotation enabled, rotation period, next rotation date | paginators | live |
| Secrets | `secretsmanager` `ListSecrets` | name, ARN, tags, rotation enabled, rotation rules, last rotated, last changed, last accessed (never the value) | paginator | live |
| Audit trail | `cloudtrail` `DescribeTrails` (include shadow trails), `GetTrailStatus`, `GetEventSelectors`, `ListEventDataStores` | multi Region, organization trail, logging on, last delivery and errors, log file validation, KMS key, bucket, management events read and write | single calls per Region | Event history keeps the last 90 days of management events per Region [S32]; trails and Lake keep what the customer sets |
| Configuration recorder | `config` `DescribeConfigurationRecorders`, `DescribeConfigurationRecorderStatus`, `DescribeDeliveryChannels`, `DescribeConfigurationAggregators` | recording on, all supported types, global types, last status | per Region | live |
| Alarms and log groups | `cloudwatch` `DescribeAlarms`; `cloudwatchlogs` `DescribeLogGroups`, `DescribeMetricFilters` | alarm metric, namespace, threshold, actions enabled, actions; log group retention days | paginators | live |
| Threat detection | `guardduty` `ListDetectors`, `GetDetector`, `ListFindings`, `GetFindings` | detector status and features; for findings: id, type, severity, resource, first and last seen, archived | paginators; findings filtered to high severity and not archived | GuardDuty keeps findings 90 days, a quota that cannot be raised [S33] |
| Posture findings | `securityhub` `DescribeHub`, `GetEnabledStandards`, `GetFindings` filtered on the CIS standard, compliance status FAILED, record state ACTIVE | control id, title, status, resource, updated | paginator | live while active |
| Backups | `backup` `ListBackupPlans`, `GetBackupPlan`, `ListBackupSelections`, `GetBackupSelection`, `ListProtectedResources`, `ListBackupJobs` (state, created after), `ListBackupVaults`, `DescribeBackupVault`, `ListRestoreJobs`, `ListRestoreTestingPlans` (name confirmed [S26]) | plan rules (schedule, retention, copy actions), selected resources, job state and times, vault lock and minimum retention, restore jobs (with `CreatedBy` showing a restore testing plan, and `ValidationStatus`) | paginators | `ListBackupJobs` returns only the last 30 days [S34]; the window for `ListRestoreJobs` is not stated on its page (unverified), so Verity keeps its own dated copy of every restore job it sees |
| Registries | `ecr` `DescribeRepositories` | tag mutability, scan on push, encryption | paginator | live |
| Resource inventory | `resource-explorer-2` `Search` on the aggregator view, else per type enumeration from the calls above | ARN, type, Region, account, tags | `Search` returns only the first 1,000 results of a query string, paging included [S35], so Verity queries per type and Region and treats a 1,000 result answer as possibly cut short | indexes refresh within minutes for tagged and under two hours for untagged resources [S8] |

Kept out on purpose: object contents, log contents, secret values, environment variables, parameter
store values, instance user data, and anything from `LookupEvents`. Nothing is written to AWS (the
credential report generation is AWS's own read side job).

## 5. Checks

Shared rules for every check below:

- **Population** is every resource of the named types in every in scope account and enabled Region.
  Accounts, Regions and resources are listed into `connection_resources`; leaving one out needs a reason
  (AU-9), as for GitHub repositories.
- **Outcomes.** `error` when a call is denied or the service cannot be reached; `insufficient_information`
  when some accounts or Regions could not be read, paging was cut short or throttling stopped the run;
  `not_applicable` only when every account and Region was read and none holds the resource type.
- **Period.** Settings are read at each run. A Type 2 period is evidenced by the daily result history; a
  missed run is visible (rule 5 of `01-evidence-model.md`). Checks that read events state their window.
- **Thresholds** marked "setting" come from the connection settings (section 9) with the default shown.

### 5.1 Existing checks: feasibility on AWS

| Check | Feasible on AWS | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `cloud.encryption_at_rest` | Yes | S3 buckets, RDS instances and clusters, RDS and EBS snapshots, EBS volumes, EFS file systems, DynamoDB tables; plus EBS encryption by default per Region | Each store is encrypted at rest; EBS default encryption is on in each Region. S3 applies SSE-S3 to every new object since 5 January 2023 and it cannot be turned off, so a bucket passes on that alone but objects written before that date are not proven [S14]; buckets older than that date carry the note | pass: all encrypted; fail: list of unencrypted stores; error: denied; insufficient: an account or Region unread | daily | per store: type, id, encrypted, key id, key manager | NS-01 (existing: full; proposed: partial, see D-AWS-4: the standard, the key type per data class in NS-01.C and the "fixed and recorded" half of NS-01.D need people) |
| `cloud.tls_in_transit` | Yes, for AWS front doors | ALB and NLB listeners, CloudFront distributions, API Gateway custom domains (`securityPolicy` field [S31]; needs the `apigateway:GET` statement added to the custom policy on 2026-11-23, without it this part is `error`) | No HTTPS or TLS listener uses a policy that allows TLS 1.0 or 1.1; HTTP listeners only redirect to HTTPS; CloudFront minimum protocol TLS 1.2 or later; no API Gateway custom domain uses `TLS_1_0`. The API, CLI and CloudFormation default listener policy is `ELBSecurityPolicy-2016-08`, which allows TLS 1.0 and 1.1, so listeners built by code often fail; the console default is `ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09` [S15] | pass, fail with listener and policy, error, insufficient | daily | per listener: protocol, policy, policy protocols, redirect | NS-02 partial (as today). Internal traffic (NS-02.D) and HSTS (NS-02.C) are not visible |
| `cloud.default_deny_ingress` | Yes | Security groups attached to a network interface, NACLs | No inbound rule allows all protocols from `0.0.0.0/0` or `::/0`; no rule open to the internet except the ports named in the setting (default 80 and 443) on groups attached to a load balancer; the default security group of each VPC has no rules | pass, fail with rule list, error, insufficient | daily | every inbound rule with group, attachment, source, ports | NS-03 partial (as today). The register's owner and purpose (NS-03.B) and the review (NS-03.D) stay with people |
| `cloud.admin_ports_closed` | Yes | Security group rules and NACL entries; RDS instances | No rule opens 22, 3389 or a database port (setting, default 1433, 1521, 3306, 5432, 6379, 9200, 27017) to `0.0.0.0/0` or `::/0`; no RDS instance is publicly accessible. A rule with a recorded exception in Verity (reason, approver, expiry) is listed and passes until expiry | pass, fail with rules, error, insufficient | daily | rules open to public ranges, exceptions applied | NS-08 (existing: full; proposed: partial, D-AWS-4: NS-08.D alert on opening and the approved route are not shown), NS-03 partial |
| `cloud.hardening_baseline` | Yes, through Security Hub CSPM | Accounts and Regions in scope | The CIS AWS Foundations Benchmark standard (v5.0.0 recommended; v3.0.0, v1.4.0 and v1.2.0 also exist) is enabled in each account and Region, and has no FAILED active control findings except those with a recorded exception [S7] | pass; fail with failed controls; error: Security Hub CSPM or the standard off, or denied; insufficient | daily | enabled standards, failed controls per account and Region | NS-04 partial (as today). Server and container baselines are not covered. Phase question D-AWS-1 |
| `cloud.threat_detection` | Yes | Accounts and enabled Regions | A GuardDuty detector exists and is ENABLED in every in scope account and Region | pass, fail with gaps, error, insufficient | daily | detector id, status, features per Region | NS-05 partial (as today) |
| `cloud.key_rotation` | Yes | Customer managed KMS keys that are enabled, symmetric, with AWS generated material | Automatic rotation is on with a period no longer than the setting (default 365 days). AWS managed keys rotate yearly by AWS and are not counted. Asymmetric, HMAC and custom key store keys cannot rotate automatically and are listed as needing manual rotation records [S16] | pass; fail; not applicable when no such key exists; error; insufficient | daily | key id, spec, origin, rotation on, period, next date | NS-06 partial (as today) |
| `cloud.network_segmented` | Partly | VPCs, subnets and route tables holding RDS instances, ElastiCache (later) and instances tagged or marked production | Every database sits in subnets whose route tables have no route to an internet gateway, is not publicly accessible, and no production workload runs in a default VPC | pass, fail, error, insufficient | daily | route tables, subnet to resource map | NS-07 partial (as today). It is a configuration reading, not the segmentation test NS-07.D asks for |
| `cloud.secrets_managed` | Partly | Production accounts | A secrets manager is in use in each production account (at least one secret accessed in the last 90 days). Verity cannot show that no secret sits in configuration, because the APIs that would show it return the secret values (section 2.2). That half comes from `vcs.secret_scanning_enabled` and a person | pass, fail, error, insufficient | daily | secret names, tags, last accessed (no values) | NS-09 partial (as today) |
| `cloud.backups_enabled` | Yes | RDS instances and clusters, DynamoDB tables, EFS file systems and EBS volumes in production accounts | RDS retention is at least the setting (default 7 days; a DB instance allows 0 to 35 days, where 0 turns automated backups off, and a Multi-AZ DB cluster 1 to 35 [S36]); DynamoDB point in time recovery on; EFS and EBS covered by an AWS Backup plan selection with retention at least the setting | pass, fail, error, insufficient | daily | per store: method, retention, plan | BC-01 partial (as today) |
| `cloud.capacity_alarms` | Partly | RDS instances and clusters in production, EBS backed instances (later) | Each production database has an alarm on free storage and one on CPU, with actions enabled and at least one action | pass, fail, error, insufficient | daily | alarms, metrics, thresholds, actions | BC-04 partial (as today) |
| `cloud.audit_logging` | Yes | Accounts in scope | At least one multi Region trail (or an organization trail) is logging, records management read and write events, has log file validation on, delivered in the last 24 hours, and its bucket blocks public access and keeps logs at least the setting (default 365 days) by lifecycle or Lake retention | pass, fail, error, insufficient | daily | trails, status, selectors, bucket settings | LM-02 partial (as today) |
| `cloud.config_changes_recorded` | Yes for recording, partly for alerts | Accounts and Regions | AWS Config records all supported resource types in every Region (global types in one), with a working delivery channel, or an organization aggregator covers them; and an alarm exists on at least the security group, network ACL, IAM policy and trail change metric filters (the CIS metric filter set) | pass, fail, error, insufficient | daily | recorder status, aggregator, metric filters, alarms | LM-03 (existing: full; proposed: partial, D-AWS-4: investigation of each alert, LM-03.C, is a person's record) |
| `cloud.root_account_mfa` | Yes | Accounts in scope | The root user has MFA and no access keys; or the account has no root credentials under centralized root access management [S17]. A virtual device is noted; a hardware or passkey device is preferred (CIS). Whether central root management is on is read once, from the management account role, because `ListOrganizationsFeatures` fails in member accounts [S27]; that failure in a member account is expected and is not `error` | pass, fail, error, insufficient | daily | MFA on, keys present, device kind, central management on | IAM-03 partial (as today) |
| `cloud.least_privilege` | Yes | IAM users, groups, roles (except service linked roles) and Identity Center permission sets with account assignments | No principal holds `AdministratorAccess` or a policy allowing `*` on `*` unless it has a recorded need in Verity (owner, reason, review date). Break glass roles are allowed when recorded | pass, fail with principals, error, insufficient | daily | principal, policy, how granted, recorded need | IAM-08 partial, IAM-07 partial (as today) |
| `cloud.machine_credentials_rotated` | Yes | Active IAM access keys (all keys, not only the first two) | Each active key is younger than the setting (default 90 days) | pass, fail with keys and ages, error, insufficient | daily | user, key id suffix, created, last used | IAM-10 partial (as today) |
| `cloud.environments_separated` | Yes, needs the customer's account roles | Accounts in scope, with the role (production, staging, development, shared) the customer gives each in Verity | At least one account is production, and no account is marked both production and a lower environment | pass, fail, error: roles not set, insufficient | weekly | account list with roles and OU path | SD-12 (existing: full; proposed: partial, D-AWS-4: production access limits, SD-12.C, and the promotion order, SD-12.D, are not shown), DM-13 partial |
| `cloud.storage_versioned` | Yes | Buckets and ECR repositories the customer marks as build output (tag or selection) | Buckets have versioning Enabled; ECR repositories have immutable tags | pass, fail, error: none marked, insufficient | daily | bucket versioning, repository tag mutability | SD-07 partial (as today) |
| `cloud.storage_lifecycle` | Yes | Buckets and log groups the customer marks with a retention class | Each has a lifecycle expiration (or log retention) no longer than the class's period | pass, fail, error: none marked, insufficient | weekly | lifecycle rules, retention days | DM-16 partial (as today) |
| `assets.resources_registered` | Yes | Resources of the supported types (EC2 instances, RDS, S3, DynamoDB, EFS, load balancers, Lambda functions by name only, ECR, EKS clusters) found by Resource Explorer or by enumeration. Lambda functions come only from Resource Explorer, because the enumeration call `lambda:ListFunctions` returns environment values [S24]; with Resource Explorer off they are not seen and the result says so | Each discovered resource is in the Verity asset register (matched on ARN as `external_id`) or excluded with a reason | pass, fail with unregistered resources, error, insufficient | daily | discovered list, matched asset, exclusions | LM-01 partial (as today) |

### 5.2 New checks

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|
| `cloud.storage_public_access_blocked` | S3 account level block public access per account; each bucket; EBS snapshots and AMIs owned; RDS snapshots | Account level block public access has all four settings on (or each bucket does); no bucket policy status is public; snapshot and image block public access is on per Region, and no snapshot or image is shared with "all" | pass, fail with items, error, insufficient | daily | flags per account and bucket, public snapshots and images | NS-04 partial: one of the hardening items the CIS benchmark sets. LM-03 partial: shows the high risk regression "public storage" is absent today; the alerting on it is separate |
| `cloud.human_users_mfa` | IAM users with a console password. Identity Center users are not in the population: the Identity Store API has no MFA operation, and the only related IAM permission found, `sso-directory:ListMfaDevicesForUser`, has no published API operation (unverified that none exists; checked 2026-11-23 [S26]) | Every IAM user with `password_enabled` TRUE has `mfa_active` TRUE | pass, fail with users, error, insufficient | daily | user, password on, MFA on | IAM-03 partial: the cloud console side of "every user has a second factor"; the identity provider covers everyone else |
| `cloud.unused_credentials_disabled` | IAM users' passwords and active access keys | No password or active key went unused for longer than the setting (default 90 days; CIS uses 45) | pass, fail, error, insufficient | daily | last used dates | IAM-10 partial: inactive machine credentials are found (IAM-10.E). IAM-12 partial: leftover cloud accounts of leavers show up; matching them to the leaver list is separate |
| `cloud.access_list_exported` | IAM users, roles assumable by people, Identity Center users and assignments, per account | The full list was read for every in scope account (a population export, like `idp.access_list_exported`) | pass when complete; insufficient when any account was not read; error | weekly | the dated list | IAM-02 partial: the complete account list a review starts from (IAM-02.B); the review and sign off are people's |
| `cloud.flow_logs_enabled` | VPCs in production accounts that hold at least one network interface | Each has an active flow log (any destination) for ALL or REJECT traffic | pass, fail, error, insufficient | daily | VPC, flow log status, traffic type, destination | LM-02 partial: network traffic reaches a log store; review of it is separate |
| `cloud.backup_jobs_succeeding` | AWS Backup jobs in the last 30 days for in scope resources; RDS latest restorable time | Every failed, aborted or expired job was followed by a completed job for the same resource within the setting (default 48 hours), and each RDS database's latest restorable time is within 24 hours | pass, fail with resources, not applicable when AWS Backup is unused and no RDS exists, error, insufficient | daily | jobs by state, follow up job, restorable time | BC-01 partial: shows backups ran and failures were followed by a good backup (BC-01.B, part of BC-01.C); the alert, ticket and cause are a person's record |
| `cloud.backups_protected` | Backup vaults holding production recovery points | Each vault is locked or its plan copies to another account or Region | pass, fail, error, insufficient | daily | vault lock, minimum retention, copy actions | BC-01 partial: the separate, immutable copy of BC-01.D; restore rights review is separate |
| `cloud.restore_tested` | AWS Backup restore jobs and restore testing plans for production resources | At least one completed restore job, or a restore testing plan run, for each production data store type in the last 12 months. How far back `ListRestoreJobs` reaches is not documented (unverified; backup jobs are kept 30 days [S34]), so until Verity's own copy spans 12 months a fail may only mean the restore is older than what AWS still returns: report `insufficient` instead of `fail` while Verity's history is shorter than the window | pass, fail, not applicable when AWS Backup is unused, error, insufficient | weekly | restore jobs, dates, resource types | BC-02 partial: a restore happened in the period (BC-02.B); proving the data was complete (BC-02.C) and the times against targets (BC-02.D) stays with people |
| `cloud.secrets_rotated` | Secrets Manager secrets in production accounts | Each secret has rotation enabled, or was last changed within the setting (default 365 days) | pass, fail with secrets, not applicable when none, error, insufficient | daily | names, rotation, last rotated or changed (no values) | NS-09 partial: rotation on schedule (NS-09.C); secrets held elsewhere are not seen. IAM-10 partial: integration credentials kept as secrets rotate |
| `cloud.threat_findings_triaged` | GuardDuty findings at or above the severity setting (default high) that are not archived | None has stayed open (not archived) longer than the response time setting (default 7 days) | pass, fail with findings, not applicable when none, error, insufficient | daily | finding id, type, severity, first seen, archived | NS-05 partial: no high finding sat unhandled past the response time (supports NS-05.C); the triage decision and reason are a person's record |
| `cloud.tls_certificates_current` | ACM certificates in use | None has expired, and none in use expires within 14 days without being eligible for automatic renewal | pass, fail, not applicable, error, insufficient | daily | domain, not after, renewal eligibility, in use by | NS-02 partial: certificates on AWS front doors stay valid (NS-02.E); certificates outside ACM are not seen |
| `assets.retired_resources_closed` | Assets in the Verity register whose `source` is AWS | Each asset still exists in AWS, or is retired in Verity within 7 days of disappearing | pass, fail, error, insufficient | daily | asset, last seen in AWS, register status | LM-01 partial: keeps the register accurate as resources are removed (LM-01.D support); the quarterly review is a person's |

Definition fields for `checks.json` (for the reconciliation step; capabilities and implementations):

| Key | Name | Capabilities | Planned providers | Resource type | Remediation (product text) | Evidence kinds |
|---|---|---|---|---|---|---|
| `cloud.storage_public_access_blocked` | Storage is not public | cloud_infrastructure | aws | cloud_resource | Turn on block public access for the account and remove public sharing from the listed buckets, snapshots and images. | Block public access settings; Public snapshots and images |
| `cloud.human_users_mfa` | Cloud console users use two factor | cloud_infrastructure | aws | cloud_identity | Add a second factor for each listed user, or move them to single sign on and remove their password. | Credential report |
| `cloud.unused_credentials_disabled` | Unused cloud credentials are disabled | cloud_infrastructure | aws | cloud_identity | Disable or delete the listed passwords and keys. | Credential report |
| `cloud.access_list_exported` | Cloud access list is exported | cloud_infrastructure | aws | cloud_identity | Connect every account in scope so the list is complete. | Cloud account and access list |
| `cloud.flow_logs_enabled` | Network traffic is logged | cloud_infrastructure | aws | cloud_resource | Turn on flow logs for the listed networks. | Flow log settings |
| `cloud.backup_jobs_succeeding` | Backups succeed | cloud_infrastructure | aws | cloud_resource | Fix the failing backup and confirm the next one completes. | Backup job history |
| `cloud.backups_protected` | Backups are kept apart | cloud_infrastructure | aws | cloud_resource | Lock the vault or copy backups to another account or region. | Backup vault and copy settings |
| `cloud.restore_tested` | A restore was tested this year | cloud_infrastructure | aws | cloud_account | Run a restore test, or set up a restore testing plan. | Restore jobs |
| `cloud.secrets_rotated` | Stored secrets rotate | cloud_infrastructure | aws | cloud_resource | Turn on rotation, or rotate the listed secrets and record it. | Secret rotation dates |
| `cloud.threat_findings_triaged` | Threat findings are handled in time | cloud_infrastructure | aws | cloud_account | Investigate the listed findings and archive them with the outcome. | Threat findings |
| `cloud.tls_certificates_current` | Certificates are current | cloud_infrastructure | aws | cloud_resource | Renew or replace the listed certificates. | Certificate inventory |
| `assets.retired_resources_closed` | Removed systems are retired | asset_discovery | aws | asset | Retire the listed assets, or record why they stay. | Register compared with discovered resources |

Not proposed (YAGNI until a control asks): service control policy checks, IMDSv2, Inspector coverage
(that is `scanner.` and Phase 3), Macie, password policy (`idp.password_policy` covers people who sign
in through the identity provider; an IAM password policy matters only to customers who still give IAM
users passwords).

## 6. Artifacts and objectives it fills

"person" stays as a source on every artifact (rule 1 of `01-evidence-model.md`). A check fills `full`
only when it collects the artifact itself for the whole population.

| Artifact key (artifacts.json) | Objective codes | Control | Change |
|---|---|---|---|
| `data-store-encryption-settings` | NS-01.B, NS-01.C, NS-01.D | NS-01 | person -> person + `cloud.encryption_at_rest` (full for AWS stores: it is the dated export by store and key) |
| `public-endpoint-tls-scan` | NS-02.B, NS-02.E | NS-02 | person -> person + `cloud.tls_in_transit`, `cloud.tls_certificates_current` (partial: the listener side, not a scan of each domain; NS-02.C needs a scan) |
| `firewall-rule-register-with-owner-and` | NS-03.B, NS-03.C | NS-03 | person -> person + `cloud.default_deny_ingress` (partial: the rules, without owner and purpose) |
| `inbound-rules-export-admin-ports` | NS-08.B, NS-08.C | NS-08 | person -> person + `cloud.admin_ports_closed` (full for AWS: it is the export of every public rule) |
| `alerts-on-drift-that-were-investigated` | LM-03.B, NS-04.D, NS-05.B, NS-08.D | LM-03, NS-04, NS-05, NS-08 | person -> person + `cloud.config_changes_recorded`, `cloud.hardening_baseline`, `cloud.threat_detection` (partial: detection and alerting exist; the investigations are people's) |
| `sample-of-alerts-that-were-investigated` | NS-05.C, NS-05.D | NS-05 | person -> person + `cloud.threat_findings_triaged` (partial) |
| `key-rotation-records` | NS-06.D, NS-06.E | NS-06 | already lists `cloud.key_rotation`; AWS becomes its first implementation |
| `secret-store-rotation-list` | NS-09.B, NS-09.C, NS-09.D, SD-11.C | NS-09 | person -> person + `cloud.secrets_managed`, `cloud.secrets_rotated` (full for Secrets Manager: names and dates, no values) |
| `segmentation-test-results` | NS-07.B | NS-07 | person -> person + `cloud.network_segmented` (partial: configuration, not a test) |
| `cloud-accounts-and-production-access` | SD-12.B, SD-12.C, SD-12.E | SD-12 | person -> person + `cloud.environments_separated`, `cloud.access_list_exported` (partial) |
| `backup-failure-alerts-and-follow-up` | BC-01.B, BC-01.C | BC-01 | person -> person + `cloud.backups_enabled`, `cloud.backup_jobs_succeeding` (partial) |
| `restore-test-plan-and-results` | BC-02.B | BC-02 | person -> person + `cloud.restore_tested` (partial) |
| `capacity-review` | BC-04.C | BC-04 | person -> person + `cloud.capacity_alarms` (partial) |
| `evidence-logs-are-reviewed` | LM-02.B | LM-02 | person -> person + `cloud.audit_logging`, `cloud.flow_logs_enabled` (partial: sources reach a store; review is people's) |
| `second-factor-enforcement-and-enrolled-users` | IAM-03.B, IAM-03.C | IAM-03 | person -> person + `cloud.root_account_mfa`, `cloud.human_users_mfa` (partial: the AWS side only) |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, IAM-01.D, IAM-10.C, SD-12.C, SD-13.D, BC-01.D | IAM-07 | already lists `cloud.least_privilege`; AWS becomes its first implementation |
| `inventory-of-service-accounts-and-keys` | IAM-10.B, IAM-10.C, IAM-10.D, SD-13.D | IAM-10 | already lists `cloud.machine_credentials_rotated` |
| `records-of-rotation-or-review` | IAM-10.D, IAM-10.E | IAM-10 | already lists `cloud.machine_credentials_rotated`; add `cloud.unused_credentials_disabled` |
| `account-list-export` | IAM-02.B, IAM-10.B, IAM-12.E | IAM-02 | already lists `idp.access_list_exported`; add `cloud.access_list_exported` (full for the AWS accounts in scope) |
| `asset-inventory` | LM-01.B, LM-01.C and 18 objectives in other families | LM-01 | already lists `assets.resources_registered`; add `assets.retired_resources_closed` |
| `evidence-data-was-deleted-when-retention` | DM-16.D, SD-07.E | DM-08 | person -> person + `cloud.storage_lifecycle` (partial) |

Needs for reconciliation (no artifact names them today): `cloud.storage_versioned` has no artifact for
SD-07.D (durable, versioned storage) other than the design document; `cloud.storage_public_access_blocked`
has no artifact of its own and would sit under `alerts-on-drift-that-were-investigated` or a new
"public exposure export". Written as `NEED cloud_infrastructure: a dated export of storage versioning`
and `NEED cloud_infrastructure: a dated export of public storage settings`.

What AWS can never prove: NS-03.D, NS-07.C, NS-06.C (the reviews), NS-05.C (the triage decision), BC-02.C
(completeness of a restore), LM-03.C and LM-03.D (investigations and root causes), and every design
objective (`.A`), which is an approved document.

## 7. Framework reach

Through the controls above (NS-01 to NS-09, BC-01, BC-02, BC-04, LM-01 to LM-03, IAM-02, IAM-03,
IAM-07, IAM-08, IAM-10, IAM-12, SD-07, SD-12, DM-13, DM-16), using the shipped mappings in
`soc2/template_requirements.json` and `iso27001/template_requirements.json`:

- **SOC 2:** CC2.1, CC5.2, CC6.1, CC6.2, CC6.3, CC6.5, CC6.6, CC6.7, CC6.8, CC7.1, CC7.2, CC8.1, CC9.1,
  A1.1, A1.2, A1.3, C1.1, C1.2, PI1.5, P4.3.
- **ISO 27001:2022 Annex A:** A.5.9, A.5.14, A.5.15, A.5.16, A.5.17, A.5.18, A.5.23, A.5.28, A.5.29,
  A.5.30, A.5.33, A.7.10, A.7.14, A.8.2, A.8.3, A.8.4, A.8.5, A.8.6, A.8.9, A.8.10, A.8.13, A.8.15,
  A.8.16, A.8.18, A.8.19, A.8.20, A.8.21, A.8.22, A.8.24, A.8.31, A.8.33.

"Reached" means at least one objective of a mapped control gets machine evidence. No criterion is met
from AWS alone (CF-4), and the ISO mappings are still unreviewed by a second person (FW-5).

## 8. Limits and false assurance traps

- **One account is not the estate.** A customer who connects only the account they remember passes
  every check. The setup asks for the organization when one exists, and `cloud.access_list_exported` and
  the account list show which accounts were read. An Organizations member that has no Verity role is
  `insufficient_information` on every check, never ignored.
- **Regions.** Resources in a Region nobody looked at are invisible. Every enabled Region is read;
  disabled opt in Regions are listed as such.
- **S3 encryption always passes.** Since January 2023 every new object is encrypted with SSE-S3 [S14]. A
  pass says nothing about older objects or about customer managed keys a contract may require (NS-01.C).
- **Default TLS policy.** Listeners created through the API or CloudFormation without a policy get
  `ELBSecurityPolicy-2016-08`, which allows TLS 1.0 and 1.1 [S15]. Expect failures on code built stacks.
- **Security Hub CSPM is a second opinion, not Verity's.** Its controls depend on AWS Config recording
  and can take up to 18 hours to produce findings after a standard is enabled [S7]. A freshly enabled
  standard with no findings yet is `insufficient_information`, not a pass. CIS v5.0.0 leaves the CloudWatch
  metric filter items to manual checks [S7], which is why `cloud.config_changes_recorded` reads them
  itself. Security Hub (CSPM) was renamed when a new AWS Security Hub reached general availability in
  December 2025; the two are separate services and use different finding formats (ASFF and OCSF) [S18].
  Verity reads the CSPM API.
- **Secrets in configuration are out of reach by design.** The only APIs that show them return the
  values. Verity will not collect them, so `cloud.secrets_managed` stays partial (section 5.1).
- **Credential report gaps.** It lists only the first two access keys per user and no service specific
  credentials [S13]; Verity adds `ListAccessKeys`. Root keys for accounts with centralized root access
  have no credentials to report, which is a pass, not an empty population.
- **Tags are claims.** Production, build output and retention classes come from the customer's tags or
  choices in Verity. A wrong tag hides a resource from a check; the population and its source are printed
  on every result.
- **Exceptions.** A recorded exception (admin port, wildcard admin) passes only until its expiry and is
  printed on the result, so a clean result shows what it was clean over.
- **Services off.** GuardDuty off is a `fail` of `cloud.threat_detection`. Security Hub CSPM off is an
  `error` of `cloud.hardening_baseline` (the customer chose another source) unless the owner decides
  otherwise (D-AWS-1).

## 9. Product and UI

Connect form fields: role ARN (one account) or management account role ARN (organization); role name
used in member accounts (default `VerityAuditRole`); the workspace's external ID shown, copyable, not
editable. Scope selection after the first run: accounts (with OU path), Regions, and the role of each
account (production, staging, development, shared). Settings with defaults: allowed public ports (80,
443), database ports, key age (90 days), unused credential age (90), backup retention (7), log retention
(365), finding response time (7 days), severity threshold (high).

Health states: connected; role missing in N accounts; permission missing (named action and the checks it
blocks); service off (GuardDuty, Config, Security Hub CSPM) per account and Region; external ID not
enforced (refused, cannot save); throttled (run incomplete).

In product guide needed: yes. The customer must run a template in their own console, choose single
account or organization, and understand the management account exception. The guide is the text of
section 3 with screenshots of the quick create page.

## 10. Implementation notes

- **Auth flow.** Verity's own identity (D-AWS-2) is loaded by `config.LoadDefaultConfig`. For each
  account, `stscreds.NewAssumeRoleProvider(stsClient, roleArn, func(o *stscreds.AssumeRoleOptions){ o.ExternalID = aws.String(id); o.RoleSessionName = "verity-<run id>" })`
  wrapped in `aws.NewCredentialsCache`, which refreshes before expiry (names confirmed on the package docs:
  `AssumeRoleOptions` has `ExternalID *string`, `RoleSessionName string`, `Duration time.Duration`;
  `CredentialsCacheOptions.ExpiryWindow` sets how early it refreshes [S19]). Session name carries the run id so the customer's CloudTrail shows which
  Verity run made each call.
- **External ID test.** At connect time, call `AssumeRole` without the external ID and expect
  AccessDenied. If it succeeds, refuse the connection with "This role does not require your external ID"
  [S1].
- **Paging.** Use the SDK paginators (`New<Operation>Paginator`). Never call the unpaginated forms of the
  EC2 describes [S12].
- **Rate limits.** SDK retry mode `adaptive` per client, a per account and Region limiter in the Go
  runtime, and a run budget. Throttling past the budget marks the observation type `truncated`.
- **Concurrency.** Accounts in parallel (bounded), Regions in parallel within an account (bounded), one
  credential cache per account.
- **Error mapping.** `AccessDenied`, `UnauthorizedOperation`, `AccessDeniedException` -> `permission_missing`
  for that type, the check is `error`. `OptInRequired` or `UnrecognizedClientException` in a Region ->
  Region not enabled, listed. `NoSuchPublicAccessBlockConfiguration`, `NoSuchLifecycleConfiguration`,
  `ServerSideEncryptionConfigurationNotFoundError` -> the setting is absent (a real finding), never
  `error`. `NoSuchLifecycleConfiguration` is listed on the `GetBucketLifecycleConfiguration` page and
  `NoSuchPublicAccessBlockConfiguration` (HTTP 404) on the S3 Control `GetPublicAccessBlock` page, which
  also says the account answer may be inherited from an organization level policy [S37].
  `ServerSideEncryptionConfigurationNotFoundError` is unverified (the S3 error list page did not render
  for the reader); since every bucket has default encryption from January 2023 [S14] it should not occur.
- **Recorded fixtures.** Record HTTP with go-vcr per service, scrub account ids, keys and ARNs. One test
  account per scenario: single account, organization with a missing role, all services off.
- **Scope drift.** A role whose policy loses an action shows "missing permission" on the next run, only
  for the checks that need it. A new Verity check that needs a new action ships with a template version;
  the connection shows "update available" and the customer updates the stack.
- **Deletion semantics.** A resource that disappears is removed from `connection_resources` with
  `last_seen`; its earlier results stay. `assets.retired_resources_closed` asks a person to retire the
  asset.
- **Normalised observations.** `cloud.resource` and `cloud.principal`, `cloud.credential` as in
  `01-evidence-model.md` 1.4, with per type settings.

## 11. How comparable platforms do it

| Platform | Auth model | Policy | Setup | Organizations |
|---|---|---|---|---|
| Vanta | Cross account role (`vanta-auditor`) with external ID | AWS managed `SecurityAudit` plus a Vanta policy whose contents depend on the Vanta products enabled | CloudFormation recommended | Each member account needs the same role and policies, otherwise an "ASSUME_ROLE" warning [C1] |
| Drata | Cross account role with external ID from the Drata wizard; "Require MFA" left off | `SecurityAudit`, with some tests needing extra permissions | Manual role or template; organization connection asks for the root id (`r-...`) | StackSet methods do not create the role in the management account [C2] |
| Secureframe | IAM role managed by a CloudFormation stack (manual role allowed) | Not stated on the pages read | CloudFormation, any Region | Organization support stated; details not read [C3] |
| Sprinto | Read only role (`sprinto-auditor-role`) with a per account external ID | `SecurityAudit` among the attached policies | CloudFormation across an organization | Yes, by template [C4] |
| Scrut | Role with both `SecurityAudit` and `ReadOnlyAccess` (read on the page 2026-11-23) | Both | CloudFormation quick create link (`ScrutIntegrationRole` stack) | Each further account is connected separately; no organization flow on the page [C5] |

All of them use a role and `SecurityAudit`; all but Scrut, whose page does not mention one, say the role
carries an external ID. None that was read offers a custom least
privilege policy by default, which is the one place Verity can be stricter and say so (trust copy rule:
name what Verity really enforces).

## 12. Sources

- [S1] AWS IAM, Access to AWS accounts owned by third parties: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html
- [S2] AWS IAM and STS quotas: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html
- [S3] ReadOnlyAccess managed policy: https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html
- [S4] ViewOnlyAccess managed policy: https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ViewOnlyAccess.html
- [S5] SecurityAudit managed policy: https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SecurityAudit.html
- [S6] Lambda GetFunctionConfiguration: https://docs.aws.amazon.com/lambda/latest/api/API_GetFunctionConfiguration.html
- [S7] CIS AWS Foundations Benchmark in Security Hub CSPM: https://docs.aws.amazon.com/securityhub/latest/userguide/cis-aws-foundations-benchmark.html
- [S8] Setting up Resource Explorer: https://docs.aws.amazon.com/resource-explorer/latest/userguide/getting-started-setting-up.html
- [S9] CloudFormation quick create links: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stacks-quick-create-links.html
- [S10] StackSets automatic deployments: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-manage-auto-deployment.html
- [S11] StackSets with service managed permissions (management account not deployed to): https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-associate-stackset-with-org.html
- [S12] EC2 API request throttling: https://docs.aws.amazon.com/ec2/latest/devguide/ec2-api-throttling.html
- [S13] IAM credential reports: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_getting-report.html
- [S14] S3 default encryption FAQ: https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-encryption-faq.html
- [S15] Application Load Balancer security policies: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/describe-ssl-policies.html
- [S16] Rotate AWS KMS keys: https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html
- [S17] AWS account root user and centralized root access: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html
- [S18] Security Hub general availability and the CSPM rename: https://aws.amazon.com/blogs/aws/aws-security-hub-now-generally-available-with-near-real-time-analytics-and-risk-prioritization/ and https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
- [S19] AWS SDK for Go v2 (module path, Go 1.24 minimum): https://github.com/aws/aws-sdk-go-v2 ; stscreds package: https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/credentials/stscreds ; credentials cache: https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/aws
- [S20] What is IAM Roles Anywhere (trust anchors, profiles, same account and Region, account trust boundary): https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html
- [S21] IAM Roles Anywhere trust model (service principal, required STS actions, `aws:SourceArn`): https://docs.aws.amazon.com/rolesanywhere/latest/userguide/trust-model.html ; credential helper (PKCS#11 and TPM keys): https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html
- [S22] Role chaining limits a session to one hour: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_terms-and-concepts.html and https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
- [S23] ECS ContainerDefinition (`environment`, `secrets`): https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ContainerDefinition.html
- [S24] Lambda ListFunctions (items include `Environment.Variables`): https://docs.aws.amazon.com/lambda/latest/api/API_ListFunctions.html
- [S25] Data returning calls inside `SecurityAudit`: EC2 DescribeInstanceAttribute `userData` https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstanceAttribute.html ; launch template `userData` https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ResponseLaunchTemplateData.html ; CodeBuild `PLAINTEXT` environment variables https://docs.aws.amazon.com/codebuild/latest/APIReference/API_EnvironmentVariable.html ; RDS DownloadDBLogFilePortion `LogFileData` https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_DownloadDBLogFilePortion.html
- [S26] Service Authorization Reference, read through its machine readable form (every action in the custom policy and the deny statement checked 2026-11-23): https://docs.aws.amazon.com/service-authorization/latest/reference/service-reference.html , for example https://docs.aws.amazon.com/service-authorization/latest/reference/list_awsidentityandaccessmanagementiam.html and https://docs.aws.amazon.com/service-authorization/latest/reference/list_awsssodirectory.html
- [S27] IAM ListOrganizationsFeatures: https://docs.aws.amazon.com/IAM/latest/APIReference/API_ListOrganizationsFeatures.html
- [S28] IAM GetAccountAuthorizationDetails: https://docs.aws.amazon.com/IAM/latest/APIReference/API_GetAccountAuthorizationDetails.html
- [S29] IAM Identity Center delegated administration: https://docs.aws.amazon.com/singlesignon/latest/userguide/delegated-admin.html
- [S30] CloudFront ViewerCertificate and DistributionSummary: https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_ViewerCertificate.html and https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_DistributionSummary.html
- [S31] API Gateway DomainName `securityPolicy`: https://docs.aws.amazon.com/apigateway/latest/api/API_DomainName.html
- [S32] CloudTrail event history: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html
- [S33] GuardDuty quotas (finding retention): https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_limits.html
- [S34] AWS Backup ListBackupJobs (last 30 days) and ListRestoreJobs: https://docs.aws.amazon.com/aws-backup/latest/devguide/API_ListBackupJobs.html and https://docs.aws.amazon.com/aws-backup/latest/devguide/API_ListRestoreJobs.html
- [S35] Resource Explorer Search (first 1,000 results): https://docs.aws.amazon.com/resource-explorer/latest/apireference/API_Search.html
- [S36] RDS backup retention period: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html
- [S37] S3 errors: https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycleConfiguration.html and https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_GetPublicAccessBlock.html
- API references used for operation and field names (not each read in full this round): https://docs.aws.amazon.com/IAM/latest/APIReference/ , https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html , https://docs.aws.amazon.com/AmazonS3/latest/API/ , https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/ , https://docs.aws.amazon.com/AWSEC2/latest/APIReference/ , https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/ , https://docs.aws.amazon.com/config/latest/APIReference/ , https://docs.aws.amazon.com/guardduty/latest/APIReference/ , https://docs.aws.amazon.com/securityhub/1.0/APIReference/ , https://docs.aws.amazon.com/kms/latest/APIReference/ , https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_ListSecrets.html , https://docs.aws.amazon.com/aws-backup/latest/devguide/api-reference.html , https://docs.aws.amazon.com/elasticloadbalancing/latest/APIReference/ , https://docs.aws.amazon.com/acm/latest/APIReference/
- [C1] Vanta, connecting AWS: https://help.vanta.com/en/articles/11345630-connecting-vanta-aws-accounts and https://help.vanta.com/en/articles/11345623-connecting-aws-with-cloudformation and https://help.vanta.com/en/articles/11346027-how-to-fix-assume_role-warning-from-aws-organization
- [C2] Drata, AWS connection: https://help.drata.com/en/articles/5048935-aws-connection-details and https://help.drata.com/en/articles/13455825-understanding-aws-permissions-and-how-drata-integrates-with-aws-concept-guide and https://help.drata.com/en/articles/8981943-aws-organizational-units-connection
- [C3] Secureframe, AWS: https://support.secureframe.com/en/articles/15111520-amazon-web-services-aws
- [C4] Sprinto, AWS: https://docs.sprinto.com/integrations/overview/amazon-web-services-aws-integration
- [C5] Scrut, AWS: https://help.scrut.io/integrating-aws

## Decisions for the owner

- **D-AWS-1.** CIS hardening benchmarks are Phase 3.2 in the signed plan. Ship `cloud.hardening_baseline`
  (Security Hub CSPM read) in Phase 2 as part of "AWS core cloud", or hold it for Phase 3? Recommended:
  ship it in Phase 2 as a read of the customer's own Security Hub CSPM results, and say plainly that
  Verity does not run its own benchmark.
- **D-AWS-2.** Verity's own AWS identity for `AssumeRole`: an IAM user key in a Verity AWS account (simple,
  long lived secret to rotate) or IAM Roles Anywhere (no access key; needs a CA, which can be Verity's own
  CA certificate registered as an external trust anchor rather than a paid AWS Private CA; all of it lives
  in Verity's AWS account, customer roles are unchanged, each customer session is capped at one hour by
  role chaining, and the certificate's private key should sit in a TPM or PKCS#11 module, see 2.1).
  (Corrected 2026-11-23: was "needs a private CA".) Recommended: start with the key in the runtime secret
  store, rotated every 90 days, and plan Roles Anywhere.
- **D-AWS-3.** Default policy: the custom least privilege policy (recommended) or `SecurityAudit` plus the
  Deny statement.
- **D-AWS-4.** Four existing mappings claim `full` where people's records remain: `cloud.encryption_at_rest`
  to NS-01, `cloud.admin_ports_closed` to NS-08, `cloud.config_changes_recorded` to LM-03,
  `cloud.environments_separated` to SD-12. Recommended: change all four to `partial` (rule 5).
- **D-AWS-5.** One external ID per workspace (works with one StackSet parameter) or per account (AWS's
  stated preference for multi tenant services, harder with StackSets). Recommended: per workspace, with
  the role ARN and account checked on every assume.
