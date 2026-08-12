import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type SearchInputProps = {
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  shortcut?: string;
  className?: string;
  onChange?: (value: string) => void;
  onFocus?: () => void;
  "aria-label"?: string;
  readOnly?: boolean;
};

export function SearchInput({
  value,
  defaultValue,
  placeholder = "Search…",
  shortcut,
  className,
  onChange,
  onFocus,
  "aria-label": ariaLabel = "Search",
  readOnly,
}: SearchInputProps) {
  return (
    <label
      className={cn(
        "flex h-9 w-full items-center gap-2.5 rounded-md border border-border bg-surface-sunken px-2.5",
        "focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-action-accent",
        className,
      )}
    >
      <Icon name="search" className="size-4 text-text-subtle" aria-hidden />
      <input
        type="search"
        value={value}
        defaultValue={defaultValue}
        readOnly={readOnly}
        aria-label={ariaLabel}
        placeholder={placeholder}
        onFocus={onFocus}
        onChange={(event) => onChange?.(event.target.value)}
        className="min-w-0 flex-1 bg-transparent font-sans text-body-md text-text-primary placeholder:text-text-subtle outline-none"
      />
      {shortcut ? (
        <kbd className="rounded-xs border border-border bg-surface-primary px-1.5 py-0.5 font-sans text-[11px] font-semibold text-text-subtle">
          {shortcut}
        </kbd>
      ) : null}
    </label>
  );
}
