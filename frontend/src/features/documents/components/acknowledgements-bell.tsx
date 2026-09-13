import { useQuery } from "@tanstack/react-query";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icon,
  Tooltip,
} from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { myPendingApprovals, myPendingCampaigns } from "../api";

export const PENDING_CAMPAIGNS_KEY = ["documents", "campaigns", "pending"] as const;
export const PENDING_APPROVALS_KEY = ["documents", "approvals", "pending"] as const;

type PendingItem = {
  key: string;
  icon: IconName;
  title: string;
  subtitle: string;
  url: string;
};

/**
 * Top-bar indicator for things waiting on the signed-in member: documents to
 * acknowledge, and review tiers to approve or reject. Mirrors the
 * notification bell: a badge with the combined count, a popover listing each
 * pending item, each row opening its own page in a new tab. Polls on the same
 * cadence as the inbox so it feels live without a socket.
 */
export function AcknowledgementsBell() {
  const { principal } = useAuth();

  const campaignsQuery = useQuery({
    queryKey: PENDING_CAMPAIGNS_KEY,
    queryFn: () => myPendingCampaigns(),
    enabled: Boolean(principal),
    refetchInterval: 60_000,
  });
  const approvalsQuery = useQuery({
    queryKey: PENDING_APPROVALS_KEY,
    queryFn: () => myPendingApprovals(),
    enabled: Boolean(principal),
    refetchInterval: 60_000,
  });

  const hasError = campaignsQuery.isError || approvalsQuery.isError;
  const items: PendingItem[] = [
    ...(campaignsQuery.data ?? []).map(
      (c): PendingItem => ({
        key: `campaign:${c.id}`,
        icon: "doc",
        title: c.title,
        subtitle: `${c.document_code} · asked by ${c.created_by_name}`,
        url: `/documents/campaigns/${c.id}`,
      }),
    ),
    ...(approvalsQuery.data ?? []).map(
      (a): PendingItem => ({
        key: `approval:${a.document_id}:${a.tier}`,
        icon: "shield",
        title: a.document_title,
        subtitle: `${a.document_code} · tier ${a.tier} review`,
        url: `/documents/${a.document_id}/approvals/${a.tier}`,
      }),
    ),
  ];
  const count = items.length;

  return (
    <DropdownMenu>
      <Tooltip content="Documents to acknowledge">
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative shrink-0 rounded-full data-[state=open]:bg-surface-hover"
            aria-label={count > 0 ? `Acknowledgements, ${count} pending` : "Acknowledgements"}
          >
            <Icon name="doc" className="size-5" />
            {count > 0 ? (
              <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-status-danger-base px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface-primary tabular">
                {count > 9 ? "9+" : count}
              </span>
            ) : null}
          </Button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-[360px] p-0">
        <div className="border-b border-border px-3 py-2">
          <span className="text-label-md font-bold text-text-primary">To acknowledge</span>
        </div>

        {hasError ? (
          <p className="px-3 py-4 text-body-sm text-status-danger-text">
            {describeError(
              (campaignsQuery.error ?? approvalsQuery.error) as unknown,
              "list",
            ).message}
          </p>
        ) : count === 0 ? (
          <div className="flex flex-col items-center px-4 pb-4 pt-3 text-center">
            <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover">
              <Icon name="check" className="size-5 text-text-subtle" />
            </span>
            <p className="mt-2 font-display text-title-sm text-text-primary">Nothing pending</p>
            <p className="mt-1 text-body-sm text-text-subtle">
              Documents to acknowledge or review appear here.
            </p>
          </div>
        ) : (
          <div className="max-h-[380px] overflow-y-auto py-1">
            {items.map((item) => (
              <DropdownMenuItem
                key={item.key}
                // Opens in its own tab: signing off is a read-then-attest task, and
                // the reader is usually part-way through something else when the
                // bell catches them. noopener so the new tab cannot reach back.
                onSelect={() => window.open(item.url, "_blank", "noopener,noreferrer")}
                className="h-auto items-start gap-2.5 py-2"
              >
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-sm bg-surface-hover">
                  <Icon name={item.icon} className="size-3.5 text-text-subtle" />
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-body-sm font-semibold text-text-primary">
                    {item.title}
                  </span>
                  <span className="truncate text-caption text-text-subtle">{item.subtitle}</span>
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
