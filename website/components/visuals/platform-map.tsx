import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { moduleGroups, modules } from "@/content/catalog";
import { SampleNote } from "./ui-kit";

/** Every module at a glance: solid tiles are live, dashed tiles are coming soon. */
export function PlatformMap() {
  return (
    <figure data-animate className="mx-auto w-full max-w-[600px]">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {moduleGroups.map((group, column) => (
          <div key={group.id} className="flex flex-col gap-2">
            <p className="seq font-mono text-[10.5px] uppercase tracking-[0.12em] text-dim" style={{ ["--i" as string]: column } as CSSProperties}>{group.name}</p>
            {modules.filter((item) => item.group === group.id).map((item, row) => (
              <div
                key={item.slug}
                className={cn("seq flex items-center gap-2 rounded-lg border px-2.5 py-2 text-[12px] font-medium leading-tight", item.status === "live" ? "border-sky-200 bg-white text-ink shadow-card" : "border-dashed border-indigo-300 bg-indigo-50/50 text-indigo-900")}
                style={{ ["--i" as string]: column + row, ["--step" as string]: "90ms" } as CSSProperties}
              >
                <Icon name={item.icon} size={15} className={item.status === "live" ? "shrink-0 text-sky-600" : "shrink-0 text-indigo-500"} />
                <span className="min-w-0">{item.name}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
      <SampleNote className="mt-5">Solid: live today · Dashed: coming soon</SampleNote>
    </figure>
  );
}
