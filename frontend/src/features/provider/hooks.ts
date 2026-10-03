import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { tenantsApi } from "./api";
import type { TenantQuery } from "./types";

/**
 * Every provider query hangs off one root key, so signing out can drop all of
 * them at once and nothing from one operator's session is left for the next.
 */
export const providerKeys = {
  all: ["provider"] as const,
  tenants: (query: TenantQuery) => ["provider", "tenants", query] as const,
  tenantsRoot: ["provider", "tenants"] as const,
  tenant: (id: string) => ["provider", "tenant", id] as const,
  branding: (id: string) => ["provider", "tenant", id, "branding"] as const,
  logo: (id: string, ref: string | null) =>
    ["provider", "tenant", id, "logo", ref] as const,
  provisioning: (id: string) =>
    ["provider", "tenant", id, "provisioning"] as const,
};

/** A value that follows `value` after it has been still for `delayMs`. */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return settled;
}

export function useTenantsPage(query: TenantQuery) {
  return useQuery({
    queryKey: providerKeys.tenants(query),
    queryFn: () => tenantsApi.list(query),
    // Typing in the search box keeps the last page on screen until the next arrives.
    placeholderData: keepPreviousData,
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: providerKeys.tenant(id),
    queryFn: () => tenantsApi.get(id),
  });
}

export function useTenantBranding(id: string) {
  return useQuery({
    queryKey: providerKeys.branding(id),
    queryFn: () => tenantsApi.branding(id),
  });
}

/** The logo as a data URL, or null when there is none. Keyed on the stored ref, so
 *  a new upload fetches again and the old image is never shown against the new ref. */
export function useTenantLogo(id: string, logoRef: string | null) {
  return useQuery({
    queryKey: providerKeys.logo(id, logoRef),
    queryFn: () => tenantsApi.logo(id),
    enabled: logoRef !== null,
    staleTime: Infinity,
  });
}

export function useTenantProvisioning(id: string) {
  return useQuery({
    queryKey: providerKeys.provisioning(id),
    queryFn: () => tenantsApi.provisioning(id),
  });
}
