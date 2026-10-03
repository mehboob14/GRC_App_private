import { Link, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { BrandMark, Button, Icon } from "@/components/ui";
import {
  clearProviderSession,
  getProviderAdmin,
} from "@/lib/provider/session";
import { providerKeys } from "../hooks";

/**
 * The platform console's shell: a top bar and a page, nothing else. No workspace
 * sidebar and no workspace branding, because an operator is never inside a tenant.
 */
export function ProviderLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const admin = getProviderAdmin();

  function signOut() {
    clearProviderSession();
    // Nothing the operator saw stays in memory for whoever signs in next.
    queryClient.removeQueries({ queryKey: providerKeys.all });
    navigate("/provider/login", { replace: true });
  }

  return (
    <div className="flex min-h-full flex-col bg-surface-page">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-primary px-5">
        <Link
          to="/provider/tenants"
          className="flex items-center gap-2.5 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-action-accent"
        >
          <BrandMark size={28} />
          <span className="font-display text-heading-sm text-text-primary">
            Verity platform
          </span>
        </Link>
        <span className="ml-auto min-w-0 truncate text-body-sm text-text-secondary">
          {admin?.email}
        </span>
        <Button variant="ghost" size="sm" onClick={signOut}>
          <Icon name="signout" className="size-4" />
          Sign out
        </Button>
      </header>
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-5 py-6">
        <Outlet />
      </main>
    </div>
  );
}
