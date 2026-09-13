import type { IconWeight, Icon as PhosphorIcon } from "@phosphor-icons/react";
import { AppWindow } from "@phosphor-icons/react/AppWindow";
import { ArrowClockwise } from "@phosphor-icons/react/ArrowClockwise";
import { ArrowCounterClockwise } from "@phosphor-icons/react/ArrowCounterClockwise";
import { ArrowLeft } from "@phosphor-icons/react/ArrowLeft";
import { ArrowUp } from "@phosphor-icons/react/ArrowUp";
import { Bell } from "@phosphor-icons/react/Bell";
import { BookOpen } from "@phosphor-icons/react/BookOpen";
import { Briefcase } from "@phosphor-icons/react/Briefcase";
import { Bug } from "@phosphor-icons/react/Bug";
import { Buildings } from "@phosphor-icons/react/Buildings";
import { CaretDown } from "@phosphor-icons/react/CaretDown";
import { CaretLeft } from "@phosphor-icons/react/CaretLeft";
import { CaretRight } from "@phosphor-icons/react/CaretRight";
import { Check } from "@phosphor-icons/react/Check";
import { CircleNotch } from "@phosphor-icons/react/CircleNotch";
import { ClipboardText } from "@phosphor-icons/react/ClipboardText";
import { Clock } from "@phosphor-icons/react/Clock";
import { Cloud } from "@phosphor-icons/react/Cloud";
import { Cube } from "@phosphor-icons/react/Cube";
import { CurrencyDollar } from "@phosphor-icons/react/CurrencyDollar";
import { Database } from "@phosphor-icons/react/Database";
import { DotsThree } from "@phosphor-icons/react/DotsThree";
import { DownloadSimple } from "@phosphor-icons/react/DownloadSimple";
import { Export } from "@phosphor-icons/react/Export";
import { FileCsv } from "@phosphor-icons/react/FileCsv";
import { FileText } from "@phosphor-icons/react/FileText";
import { Funnel } from "@phosphor-icons/react/Funnel";
import { Gauge } from "@phosphor-icons/react/Gauge";
import { Gear } from "@phosphor-icons/react/Gear";
import { Globe } from "@phosphor-icons/react/Globe";
import { HardDrives } from "@phosphor-icons/react/HardDrives";
import { Image } from "@phosphor-icons/react/Image";
import { Info } from "@phosphor-icons/react/Info";
import { Link } from "@phosphor-icons/react/Link";
import { ListBullets } from "@phosphor-icons/react/ListBullets";
import { ListNumbers } from "@phosphor-icons/react/ListNumbers";
import { Lock } from "@phosphor-icons/react/Lock";
import { MagnifyingGlass } from "@phosphor-icons/react/MagnifyingGlass";
import { Monitor } from "@phosphor-icons/react/Monitor";
import { Moon } from "@phosphor-icons/react/Moon";
import { Palette } from "@phosphor-icons/react/Palette";
import { PencilSimple } from "@phosphor-icons/react/PencilSimple";
import { Plug } from "@phosphor-icons/react/Plug";
import { Plus } from "@phosphor-icons/react/Plus";
import { Pulse } from "@phosphor-icons/react/Pulse";
import { PuzzlePiece } from "@phosphor-icons/react/PuzzlePiece";
import { Question } from "@phosphor-icons/react/Question";
import { Quotes } from "@phosphor-icons/react/Quotes";
import { Shield } from "@phosphor-icons/react/Shield";
import { ShieldCheck } from "@phosphor-icons/react/ShieldCheck";
import { SignOut } from "@phosphor-icons/react/SignOut";
import { SquaresFour } from "@phosphor-icons/react/SquaresFour";
import { Stack } from "@phosphor-icons/react/Stack";
import { Sun } from "@phosphor-icons/react/Sun";
import { Target } from "@phosphor-icons/react/Target";
import { TextB } from "@phosphor-icons/react/TextB";
import { TextItalic } from "@phosphor-icons/react/TextItalic";
import { TextStrikethrough } from "@phosphor-icons/react/TextStrikethrough";
import { TextT } from "@phosphor-icons/react/TextT";
import { Trash } from "@phosphor-icons/react/Trash";
import { UploadSimple } from "@phosphor-icons/react/UploadSimple";
import { UserCircle } from "@phosphor-icons/react/UserCircle";
import { Users } from "@phosphor-icons/react/Users";
import { Warning } from "@phosphor-icons/react/Warning";
import { X } from "@phosphor-icons/react/X";
import { cn } from "@/lib/cn";

/**
 * Every icon in the product, solid.
 *
 * Shapes (bell, shield, document, gear) use Phosphor's `fill` weight. Bare
 * glyphs (check, close, plus, the text-format marks) use `bold` instead: their
 * `fill` variant is the glyph knocked out of a filled square, which reads as a
 * checkbox or a button rather than as the mark itself.
 *
 * One file owns the mapping, so a key keeps its meaning wherever it is used
 * and swapping a glyph never touches a call site.
 */
const ICONS = {
  check: [Check, "bold"],
  chev: [CaretDown, "fill"],
  chevr: [CaretRight, "fill"],
  search: [MagnifyingGlass, "bold"],
  bell: [Bell, "fill"],
  help: [Question, "fill"],
  grid: [SquaresFour, "fill"],
  shield: [Shield, "fill"],
  controls: [ShieldCheck, "fill"],
  doc: [FileText, "fill"],
  book: [BookOpen, "fill"],
  activity: [Pulse, "bold"],
  alert: [Warning, "fill"],
  plug: [Plug, "fill"],
  risk: [Target, "fill"],
  layers: [Stack, "fill"],
  vendor: [Buildings, "fill"],
  box: [Cube, "fill"],
  bug: [Bug, "fill"],
  users: [Users, "fill"],
  user: [UserCircle, "fill"],
  audit: [ClipboardText, "fill"],
  globe: [Globe, "fill"],
  gear: [Gear, "fill"],
  puzzle: [PuzzlePiece, "fill"],
  link: [Link, "bold"],
  sun: [Sun, "fill"],
  moon: [Moon, "fill"],
  monitor: [Monitor, "fill"],
  gauge: [Gauge, "fill"],
  plus: [Plus, "bold"],
  more: [DotsThree, "bold"],
  x: [X, "bold"],
  arrowr: [CaretRight, "fill"],
  // `arrowl` is a left caret and Pagination depends on it being one. The real
  // left arrow is a separate key so the back control can be a true arrow.
  arrowl: [CaretLeft, "fill"],
  arrowleft: [ArrowLeft, "bold"],
  arrowup: [ArrowUp, "bold"],
  clock: [Clock, "fill"],
  trash: [Trash, "fill"],
  filter: [Funnel, "fill"],
  info: [Info, "fill"],
  spinner: [CircleNotch, "bold"],
  download: [DownloadSimple, "bold"],
  upload: [UploadSimple, "bold"],
  export: [Export, "fill"],
  edit: [PencilSimple, "fill"],
  lock: [Lock, "fill"],
  signout: [SignOut, "bold"],
  appWindow: [AppWindow, "fill"],
  server: [HardDrives, "fill"],
  database: [Database, "fill"],
  cloud: [Cloud, "fill"],
  briefcase: [Briefcase, "fill"],
  dollar: [CurrencyDollar, "bold"],
  spreadsheet: [FileCsv, "fill"],
  bold: [TextB, "bold"],
  italic: [TextItalic, "bold"],
  strike: [TextStrikethrough, "bold"],
  list: [ListBullets, "bold"],
  listOrdered: [ListNumbers, "bold"],
  quote: [Quotes, "fill"],
  image: [Image, "fill"],
  undo: [ArrowCounterClockwise, "bold"],
  redo: [ArrowClockwise, "bold"],
  palette: [Palette, "fill"],
  type: [TextT, "bold"],
} as const satisfies Record<string, readonly [PhosphorIcon, IconWeight]>;

export type IconName = keyof typeof ICONS;

type IconProps = {
  name: IconName;
  className?: string;
  "aria-hidden"?: boolean;
  "aria-label"?: string;
};

export function Icon({
  name,
  className,
  "aria-hidden": ariaHidden = true,
  "aria-label": ariaLabel,
}: IconProps) {
  const [Glyph, weight] = ICONS[name];
  return (
    <Glyph
      weight={weight}
      aria-hidden={ariaLabel ? undefined : ariaHidden}
      aria-label={ariaLabel}
      className={cn("size-[1em] shrink-0", className)}
    />
  );
}
