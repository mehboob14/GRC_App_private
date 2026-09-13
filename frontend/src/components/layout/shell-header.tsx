import { createContext, useContext, useState, type ReactNode } from "react";
import type { IconName } from "@/components/ui/icon";

/**
 * The shell header is a single top bar shared by every module: the module title
 * (left) sits beside the global actions (right) on row 1, and the module's tab
 * strip renders on row 2. Rather than rewrite every page, `PageHeader` and
 * `TabStrip` publish into this context: the heading as data, the tabs and the
 * module's own actions through portals into slots the Topbar owns. A page keeps
 * calling `<PageHeader>` / `<TabStrip>`; their output just lands at the top.
 */
export type ShellHeading = {
  title: string;
  /** Module icon, shown in a tile beside the title. */
  icon?: IconName;
  /** One short line under the title. */
  subtitle?: string;
};

type ShellHeader = {
  heading: ShellHeading | null;
  setHeading: (heading: ShellHeading | null) => void;
  /** The Topbar's row-2 element; TabStrip portals its tabs into it. */
  tabsSlot: HTMLElement | null;
  setTabsSlot: (el: HTMLElement | null) => void;
  /** Row 1, left of the global actions; PageHeader portals `actions` into it. */
  actionsSlot: HTMLElement | null;
  setActionsSlot: (el: HTMLElement | null) => void;
};

const ShellHeaderContext = createContext<ShellHeader | undefined>(undefined);

export function ShellHeaderProvider({ children }: { children: ReactNode }) {
  const [heading, setHeading] = useState<ShellHeading | null>(null);
  const [tabsSlot, setTabsSlot] = useState<HTMLElement | null>(null);
  const [actionsSlot, setActionsSlot] = useState<HTMLElement | null>(null);
  return (
    <ShellHeaderContext.Provider
      value={{ heading, setHeading, tabsSlot, setTabsSlot, actionsSlot, setActionsSlot }}
    >
      {children}
    </ShellHeaderContext.Provider>
  );
}

/** Undefined when rendered outside the app shell (so components can fall back
 *  to their old inline layout). */
export function useShellHeader(): ShellHeader | undefined {
  return useContext(ShellHeaderContext);
}
