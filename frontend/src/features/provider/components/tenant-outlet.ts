import { useOutletContext } from "react-router-dom";
import type { Tenant } from "../types";

/** What the tenant page hands the tab inside it. */
export type TenantOutlet = { tenant: Tenant };

export function useTenantOutlet(): TenantOutlet {
  return useOutletContext<TenantOutlet>();
}
