import {
  Activity,
  AlertTriangle,
  AppWindow,
  ArrowLeft,
  ArrowUp,
  Bell,
  BookOpen,
  Box,
  Briefcase,
  Bug,
  Building2,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Cloud,
  Database,
  Download,
  Bold,
  Italic,
  Strikethrough,
  List,
  ListOrdered,
  Quote,
  Image as ImageIcon,
  Undo2,
  Redo2,
  Palette,
  Type,
  Clock,
  DollarSign,
  FileSpreadsheet,
  FileText,
  Filter,
  Gauge,
  Globe,
  Grid2X2,
  HelpCircle,
  Info,
  Layers,
  Link2,
  Loader2,
  Monitor,
  Moon,
  MoreHorizontal,
  Plus,
  Plug,
  Puzzle,
  Search,
  Server,
  Settings,
  Upload,
  Shield,
  ShieldCheck,
  Sun,
  Target,
  Trash2,
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
  monitor: Monitor,
  gauge: Gauge,
  plus: Plus,
  more: MoreHorizontal,
  x: X,
  arrowr: ChevronRight,
  // `arrowl` is a ChevronLeft and Pagination depends on it being one. The real
  // left arrow is a separate key so the back control can be a true arrow.
  arrowl: ChevronLeft,
  arrowleft: ArrowLeft,
  arrowup: ArrowUp,
  clock: Clock,
  trash: Trash2,
  filter: Filter,
  info: Info,
  spinner: Loader2,
  download: Download,
  appWindow: AppWindow,
  server: Server,
  database: Database,
  cloud: Cloud,
  briefcase: Briefcase,
  dollar: DollarSign,
  spreadsheet: FileSpreadsheet,
  upload: Upload,
  bold: Bold,
  italic: Italic,
  strike: Strikethrough,
  list: List,
  listOrdered: ListOrdered,
  quote: Quote,
  image: ImageIcon,
  undo: Undo2,
  redo: Redo2,
  palette: Palette,
  type: Type,
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
