import { useState } from "react";
import { Outlet, useParams } from "react-router-dom";
import {
  Button,
  DetailHeader,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  TabStrip,
  type TabStripItem,
} from "@/components/ui";
import { describeProviderError } from "../errors";
import { useTenant } from "../hooks";
import { STATUS_META, formatDate, tenantName } from "../tokens";
import { InviteAdminDialog } from "./invite-admin-dialog";
import type { TenantOutlet } from "./tenant-outlet";

function tabsFor(id: string): TabStripItem[] {
  const base = `/provider/tenants/${id}`;
  return [
    { id: `${base}/profile`, label: "Profile" },
    { id: `${base}/branding`, label: "Branding" },
    { id: `${base}/provisioning`, label: "Provisioning" },
  ];
}

/** One tenant: who it is, what state it is in, and the three things to do to it. */
export function ProviderTenantLayout() {
  const { tenantId = "" } = useParams();
  const query = useTenant(tenantId);
  const [inviteOpen, setInviteOpen] = useState(false);

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-96 w-full rounded-lg" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    const failure = describeProviderError(query.error, "tenant");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const tenant = query.data;
  const meta = STATUS_META[tenant.status];

  return (
    <div>
      <DetailHeader
        backTo="/provider/tenants"
        backLabel="Tenants"
        icon="vendor"
        title={tenantName(tenant)}
        chips={<StatusPill status={meta.family} label={meta.label} />}
        meta={`${tenant.slug} · ${tenant.plan} · Registered ${formatDate(tenant.created_at)}`}
        actions={
          <Button onClick={() => setInviteOpen(true)}>
            <Icon name="mail" className="size-4" />
            {tenant.status === "provisioning" ? "Invite first admin" : "Invite admin"}
          </Button>
        }
      />
      <TabStrip inline label="Tenant sections" items={tabsFor(tenant.id)} className="mt-1" />
      <Outlet context={{ tenant } satisfies TenantOutlet} />
      <InviteAdminDialog
        tenant={tenant}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
      />
    </div>
  );
}
