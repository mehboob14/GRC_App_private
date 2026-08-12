import { Icon, Tooltip, type IconName } from "@/components/ui";
import { useTheme, type ThemeMode } from "@/lib/theme";

const CYCLE: readonly ThemeMode[] = ["light", "system", "dark"];

const MODE_META: Record<ThemeMode, { icon: IconName; label: string }> = {
  light: { icon: "sun", label: "Light" },
  system: { icon: "monitor", label: "System" },
  dark: { icon: "moon", label: "Dark" },
};

/** Sidebar-footer control cycling light → system → dark (DS icon-only 28). */
export function ThemeToggle() {
  const { mode, setMode } = useTheme();
  const next = CYCLE[(CYCLE.indexOf(mode) + 1) % CYCLE.length] ?? "system";
  const label = `Theme: ${MODE_META[mode].label.toLowerCase()} — switch to ${MODE_META[next].label.toLowerCase()}`;

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
