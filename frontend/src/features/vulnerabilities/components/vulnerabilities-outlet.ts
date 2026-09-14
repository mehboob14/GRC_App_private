import { useOutletContext } from "react-router-dom";
import type { VulnInstance } from "../types";

/** What the vulnerabilities layout hands the pages inside it. */
export type VulnerabilitiesOutlet = {
  openAddFinding: () => void;
  /** The register passes up the rows it shows, so the header Export saves
   *  exactly those. Null when the register is not on screen. */
  setExportRows: (rows: VulnInstance[] | null) => void;
};

export function useVulnerabilitiesOutlet(): VulnerabilitiesOutlet {
  return useOutletContext<VulnerabilitiesOutlet>();
}
