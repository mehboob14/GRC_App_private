import { Icon, Tooltip, type IconName } from "@/components/ui";
import { useTheme, type ThemeMode } from "@/lib/theme";

const MODE_META: Record<ThemeMode, { icon: IconName; label: string }> = {
  light: { icon: "sun", label: "Light" },
  dark: { icon: "moon", label: "Dark" },
};

/**
 * Sidebar-footer control toggling light and dark (DS icon-only 28).
 *
 * "System" used to sit between the two, and an unset preference resolved to it,
 * so anyone whose laptop was in dark mode got a dark app without asking for one.
 * Light is the product default now and this is a straight two-way switch.
 */
export function ThemeToggle() {
  const { mode, setMode } = useTheme();
  const next: ThemeMode = mode === "dark" ? "light" : "dark";
  const label = `Switch to ${MODE_META[next].label.toLowerCase()} mode`;

  return (
    <Tooltip content={label} side="top">
      <button
        type="button"
        aria-label={label}
        onClick={() => setMode(next)}
        className="flex size-7 shrink-0 items-center justify-center rounded-sm text-text-secondary transition-colors duration-80 hover:bg-surface-hover hover:text-text-primary"
      >
        <Icon name={MODE_META[mode].icon} className="size-4" />
      </button>
    </Tooltip>
  );
}
