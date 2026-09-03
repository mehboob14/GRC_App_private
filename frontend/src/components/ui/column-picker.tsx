import { Button } from "./button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./dropdown-menu";
import { Icon } from "./icon";
import type { ColumnDef } from "./use-column-prefs";

/**
 * The "Columns" control every register shares. Pair it with `useColumnPrefs`,
 * whose whole return value spreads straight in:
 *
 *   const cols = useColumnPrefs("verity.assets.columns", ASSET_COLUMNS);
 *   <ColumnPicker {...cols} />
 *
 * Lives in the Toolbar's `actions` slot, immediately before the primary button.
 */
export function ColumnPicker<K extends string>({
  columns,
  visible,
  toggle,
  reset,
  hiddenCount,
}: {
  columns: readonly ColumnDef<K>[];
  visible: Record<K, boolean>;
  toggle: (key: K, next: boolean) => void;
  reset: () => void;
  hiddenCount: number;
  /** Accepted so useColumnPrefs' return value can be spread wholesale. */
  isVisible?: (key: K) => boolean;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" aria-label="Choose columns">
          <Icon name="layers" className="size-4" aria-hidden />
          Columns
          {hiddenCount > 0 ? (
            <span className="tabular text-caption text-text-subtle">
              {columns.length - hiddenCount}/{columns.length}
            </span>
          ) : null}
          <Icon name="chev" className="size-4" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {columns.map((col) => (
          <DropdownMenuCheckboxItem
            key={col.key}
            checked={visible[col.key] !== false}
            onCheckedChange={(next) => toggle(col.key, next)}
          >
            {col.label}
          </DropdownMenuCheckboxItem>
        ))}
        {hiddenCount > 0 ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={reset}>Show all columns</DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
