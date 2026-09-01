import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icon,
  Tooltip,
} from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { myPendingCampaigns } from "../api";

export const PENDING_CAMPAIGNS_KEY = ["documents", "campaigns", "pending"] as const;

/**
 * Top-bar indicator for documents awaiting the signed-in member's
 * acknowledgement. Mirrors the notification bell: a badge with the count, a
 * popover listing each pending campaign, each row opening its acknowledgement
 * page. Polls on the same cadence as the inbox so it feels live without a socket.
 */
export function AcknowledgementsBell() {
  const navigate = useNavigate();
  const { principal } = useAuth();

  const pendingQuery = useQuery({
    queryKey: PENDING_CAMPAIGNS_KEY,
    queryFn: () => myPendingCampaigns(),
    enabled: Boolean(principal),
    refetchInterval: 60_000,
  });

  const items = pendingQuery.data ?? [];
  const count = items.length;

  return (
    <DropdownMenu>
      <Tooltip content="Documents to acknowledge">
        <DropdownMenuTrigger asChild>
          <Button
            variant="secondary"
            size="icon"
            className="relative shrink-0"
            aria-label={count > 0 ? `Acknowledgements, ${count} pending` : "Acknowledgements"}
          >
            <Icon name="doc" className="size-4 text-text-secondary" />
            {count > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-action-accent px-1 text-[10px] font-bold leading-none text-white tabular">
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

        {count === 0 ? (
          <div className="flex flex-col items-center px-4 pb-4 pt-3 text-center">
            <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover">
              <Icon name="check" className="size-5 text-text-subtle" />
            </span>
            <p className="mt-2 font-display text-title-sm text-text-primary">Nothing pending</p>
            <p className="mt-1 text-body-sm text-text-subtle">
              Documents you&rsquo;re asked to read and sign appear here.
            </p>
          </div>
        ) : (
          <div className="max-h-[380px] overflow-y-auto py-1">
            {items.map((campaign) => (
              <DropdownMenuItem
                key={campaign.id}
                onSelect={() => navigate(`/documents/campaigns/${campaign.id}`)}
                className="h-auto items-start gap-2.5 py-2"
              >
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-sm bg-surface-hover">
                  <Icon name="doc" className="size-3.5 text-text-subtle" />
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-body-sm font-semibold text-text-primary">
                    {campaign.title}
                  </span>
                  <span className="truncate text-caption text-text-subtle">
                    <span className="font-mono">{campaign.document_code}</span> · asked by{" "}
                    {campaign.created_by_name}
                  </span>
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
