import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * The shell header is a single top bar shared by every module: the module title
 * (left) sits beside the global actions (right) on row 1, and the module's tab
 * strip renders on row 2. Rather than rewrite every page, `PageHeader` and
 * `TabStrip` publish into this context — the title as a string, the tabs through
 * a portal into a slot the Topbar owns. A page keeps calling `<PageHeader>` /
 * `<TabStrip>`; their output just lands at the top.
 */
type ShellHeader = {
  title: string | null;
  setTitle: (title: string | null) => void;
  /** The Topbar's row-2 element; TabStrip portals its tabs into it. */
  tabsSlot: HTMLElement | null;
  setTabsSlot: (el: HTMLElement | null) => void;
};

const ShellHeaderContext = createContext<ShellHeader | undefined>(undefined);

export function ShellHeaderProvider({ children }: { children: ReactNode }) {
  const [title, setTitle] = useState<string | null>(null);
  const [tabsSlot, setTabsSlot] = useState<HTMLElement | null>(null);
  return (
    <ShellHeaderContext.Provider value={{ title, setTitle, tabsSlot, setTabsSlot }}>
      {children}
    </ShellHeaderContext.Provider>
  );
}

/** Undefined when rendered outside the app shell (so components can fall back
 *  to their old inline layout). */
export function useShellHeader(): ShellHeader | undefined {
  return useContext(ShellHeaderContext);
}
