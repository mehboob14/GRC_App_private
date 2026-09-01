/** Notification shapes, mirroring the backend `NotificationOut` / inbox response
 * one-to-one (snake_case, like the tasks module) so no mapper sits in between. */

export type NotificationKind =
  | "assigned"
  | "comment"
  | "status"
  | "sla_breach"
  | "sla_due"
  | "approval"
  | "recurrence";

export type Notification = {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  /** What it is about, for the deep-link. `"task"` today; null if not object-bound. */
  object_type: string | null;
  object_id: string | null;
  read_at: string | null;
  created_at: string;
};

export type NotificationInbox = {
  items: Notification[];
  /** May exceed `items.length` past the page limit — it drives the badge. */
  unread_count: number;
};
