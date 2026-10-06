import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icon,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import {
  fetchInbox,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api";
import type { Notification } from "../types";

const INBOX_KEY = ["notifications", "inbox"] as const;

/** Where a notice leads, by what it is about. A review notice carries its document, an
 *  acknowledgement reminder (and the "please acknowledge" notice) its campaign. */
const ROUTES = new Map<string, (id: string) => string>([
  ["task", (id) => `/tasks/${id}`],
  ["document", (id) => `/documents/${id}`],
  ["document_ack_campaign", (id) => `/documents/campaigns/${id}`],
]);

/** Compact "3m ago" / "2d ago"; falls back to a date past a week. */
function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function NotificationBell() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();

  const inboxQuery = useQuery({
    queryKey: INBOX_KEY,
    queryFn: () => fetchInbox(20),
    enabled: Boolean(principal),
    // The badge should feel live without a socket; a minute is plenty for
    // assignment / SLA alerts and cheap (one small query per open tab).
    refetchInterval: 60_000,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: INBOX_KEY });
  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidate,
    onError: (error) =>
      toast({ title: errorToast(error, "notification"), tone: "danger" }),
  });
  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
    onError: (error) =>
      toast({ title: errorToast(error, "notification"), tone: "danger" }),
  });

  const items = inboxQuery.data?.items ?? [];
  const unread = inboxQuery.data?.unread_count ?? 0;
  // A bell that fails silently is invisible: an empty popover would read as
  // "all caught up" when the inbox never loaded. Too small for an ErrorState,
  // so it says so in one line instead.
  const failure = inboxQuery.isError
    ? describeError(inboxQuery.error, "notification")
    : null;

  function open(notification: Notification) {
    if (!notification.read_at) readMutation.mutate(notification.id);
    const route = notification.object_type ? ROUTES.get(notification.object_type) : undefined;
    if (route && notification.object_id) navigate(route(notification.object_id));
  }

  return (
    <DropdownMenu>
      <Tooltip content="Notifications">
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative shrink-0 rounded-full data-[state=open]:bg-surface-hover"
            aria-label={
              unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
            }
          >
            <Icon name="bell" className="size-5" />
            {unread > 0 ? (
              <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-status-danger-base px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface-primary tabular">
                {unread > 9 ? "9+" : unread}
              </span>
            ) : null}
          </Button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-[360px] p-0">
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <span className="text-label-md font-bold text-text-primary">
            Notifications
          </span>
          {unread > 0 ? (
            <button
              type="button"
              onClick={() => readAllMutation.mutate()}
              disabled={readAllMutation.isPending}
              className="text-caption font-semibold text-action-accent hover:underline disabled:opacity-50"
            >
              Mark all read
            </button>
          ) : null}
        </div>

        {failure ? (
          <p className="px-3 py-4 text-body-sm text-status-danger-text">
            {failure.message}
          </p>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center px-4 pb-4 pt-3 text-center">
            <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover">
              <Icon name="bell" className="size-5 text-text-subtle" />
            </span>
            <p className="mt-2 font-display text-title-sm text-text-primary">
              You&rsquo;re all caught up
            </p>
            <p className="mt-1 text-body-sm text-text-subtle">
              Assignments, comments and SLA alerts show up here.
            </p>
          </div>
        ) : (
          <div className="max-h-[380px] overflow-y-auto py-1">
            {items.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                onSelect={() => open(notification)}
                className="h-auto items-start gap-2.5 py-2"
              >
                <span
                  className={cn(
                    "mt-1.5 size-2 shrink-0 rounded-full",
                    notification.read_at ? "bg-transparent" : "bg-action-accent",
                  )}
                  aria-hidden
                />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-body-sm font-semibold text-text-primary">
                    {notification.title}
                  </span>
                  {notification.body ? (
                    <span className="line-clamp-2 text-caption text-text-subtle">
                      {notification.body}
                    </span>
                  ) : null}
                  <span className="mt-0.5 text-caption text-text-subtle">
                    {relativeTime(notification.created_at)}
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
