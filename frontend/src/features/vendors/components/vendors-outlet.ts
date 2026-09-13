import { useOutletContext } from "react-router-dom";

/** What the vendors layout hands the pages inside it. */
export type VendorsOutlet = { addVendor: () => void };

/** For a page inside the module that offers "Add vendor" in its own empty state. */
export function useVendorsOutlet(): VendorsOutlet {
  return useOutletContext<VendorsOutlet>();
}
