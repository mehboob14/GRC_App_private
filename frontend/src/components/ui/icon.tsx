import {
  Activity,
  AlertTriangle,
  Bell,
  BookOpen,
  Box,
  Bug,
  Building2,
  Check,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  FileText,
  Gauge,
  Globe,
  Grid2X2,
  HelpCircle,
  Layers,
  Link2,
  Moon,
  MoreHorizontal,
  Plus,
  Plug,
  Puzzle,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sun,
  Target,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Maps Figma Icons page names (i-*) to Lucide glyphs that match the sheet.
 * Figma MCP returns fragmented path assets (7-day URLs); Lucide provides the
 * same stroke set as durable, recolorable icons for currentColor theming.
 */
const ICONS = {
  check: Check,
  chev: ChevronDown,
  chevr: ChevronRight,
  search: Search,
  bell: Bell,
  help: HelpCircle,
  grid: Grid2X2,
  shield: Shield,
  controls: ShieldCheck,
  doc: FileText,
  book: BookOpen,
  activity: Activity,
  alert: AlertTriangle,
  plug: Plug,
  risk: Target,
  layers: Layers,
  vendor: Building2,
  box: Box,
  bug: Bug,
  users: Users,
  audit: ClipboardCheck,
  globe: Globe,
  gear: Settings,
  puzzle: Puzzle,
  link: Link2,
  sun: Sun,
  moon: Moon,
  gauge: Gauge,
  plus: Plus,
  more: MoreHorizontal,
  x: X,
  arrowr: ChevronRight,
} as const;

export type IconName = keyof typeof ICONS;

type IconProps = {
  name: IconName;
  className?: string;
  strokeWidth?: number;
  "aria-hidden"?: boolean;
  "aria-label"?: string;
};

export function Icon({
  name,
  className,
  strokeWidth = 1.75,
  "aria-hidden": ariaHidden = true,
  "aria-label": ariaLabel,
}: IconProps) {
  const Glyph: LucideIcon = ICONS[name];
  return (
    <Glyph
      aria-hidden={ariaLabel ? undefined : ariaHidden}
      aria-label={ariaLabel}
      className={cn("size-[1em] shrink-0", className)}
      strokeWidth={strokeWidth}
    />
  );
}
