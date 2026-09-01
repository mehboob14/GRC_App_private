import { apiFetch } from "@/lib/api/client";
import type { NotificationInbox } from "./types";

/**
 * Data layer for notifications, wired straight to the real backend. With mocks
 * on, these routes have no MSW handler and MSW is configured to bypass, so the
 * calls fall through to the API just as documents and tasks do.
 */

export function fetchInbox(limit = 20): Promise<NotificationInbox> {
  return apiFetch<NotificationInbox>(`/notifications?limit=${limit}`);
}

export function markNotificationRead(id: string): Promise<void> {
  return apiFetch<void>(`/notifications/${id}/read`, { method: "POST" });
}

export function markAllNotificationsRead(): Promise<{ marked: number }> {
  return apiFetch<{ marked: number }>(`/notifications/read-all`, {
    method: "POST",
  });
}
