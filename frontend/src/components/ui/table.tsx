import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode, ThHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div
      className={cn(
        "w-full overflow-x-auto rounded-lg border border-border bg-surface-primary",
        className,
      )}
    >
      <table className="w-full border-collapse text-left" {...props} />
    </div>
  );
}

export function THead({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn("border-b border-border", className)}
      {...props}
    />
  );
}

export function TBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-border", className)} {...props} />;
}

export function TR({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("hover:bg-surface-hover/60", className)} {...props} />;
}

export function TH({
  className,
  sortable,
  sorted,
  onSort,
  children,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement> & {
  sortable?: boolean;
  sorted?: "asc" | "desc" | false;
  onSort?: () => void;
}) {
  const content = (
    <span className="inline-flex items-center gap-1 type-overline text-text-subtle">
      {children}
      {sortable ? (
        <Icon
          name="chev"
          className={cn(
            "size-3 opacity-50",
            sorted === "asc" && "rotate-180 opacity-100",
            sorted === "desc" && "opacity-100",
          )}
        />
      ) : null}
    </span>
  );

  if (sortable) {
    return (
      <th className={cn("px-4 py-3", className)} {...props}>
        <button
          type="button"
          onClick={onSort}
          className="inline-flex items-center gap-1 hover:text-text-primary"
        >
          {content}
        </button>
      </th>
    );
  }

  return (
    <th className={cn("px-4 py-3", className)} {...props}>
      {content}
    </th>
  );
}

export function TD({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("px-4 py-3.5 align-middle text-body-md text-text-primary", className)}
      {...props}
    />
  );
}

export function TableIconButton({
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-sm text-text-subtle hover:bg-surface-hover hover:text-text-primary",
        className,
      )}
      {...props}
    />
  );
}

export function TableEmpty({ children }: { children: ReactNode }) {
  return (
    <tr>
      <td colSpan={99} className="px-4 py-12 text-center text-body-md text-text-secondary">
        {children}
      </td>
    </tr>
  );
}
