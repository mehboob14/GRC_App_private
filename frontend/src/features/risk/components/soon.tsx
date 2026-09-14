import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui";

export type SoonItem = { icon: IconName; title: string; text: string };

/** A later-phase capability, visible for orientation and plainly not live yet. */
export function SoonCard({ icon, title, text, className }: SoonItem & { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-border bg-surface-primary p-4",
        className,
      )}
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-subtle">
        <Icon name={icon} className="size-4" />
      </span>
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-label-md text-text-primary">
          {title}
          <SoonBadge />
        </p>
        <p className="mt-0.5 text-body-sm text-text-subtle">{text}</p>
      </div>
    </div>
  );
}

export function SoonBadge() {
  return (
    <span className="rounded-full bg-action-accent-tint px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-action-accent">
      Soon
    </span>
  );
}

/** A whole tab that belongs to a later phase: what it will do, in a few cards. */
export function SoonSection({
  icon,
  title,
  text,
  items,
}: {
  icon: IconName;
  title: string;
  text: string;
  items: SoonItem[];
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-primary p-5">
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
          <Icon name={icon} className="size-5" />
        </span>
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 font-display text-title-md text-text-primary">
            {title}
            <SoonBadge />
          </h2>
          <p className="mt-0.5 text-body-sm text-text-subtle">{text}</p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <SoonCard key={item.title} {...item} />
        ))}
      </div>
    </div>
  );
}
