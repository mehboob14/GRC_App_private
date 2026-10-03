import { BrandMark } from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { useWorkspaceBranding } from "@/features/tenancy/use-branding";

/**
 * The head of the sidebar. A workspace the provider has branded shows its own
 * logo and name; anything else, including a workspace whose branding has not
 * loaded or could not be read, shows the Verity mark and name.
 */
export function WorkspaceBrand() {
  const { principal } = useAuth();
  const { branded, logo } = useWorkspaceBranding();
  const name = branded && principal?.tenant_name ? principal.tenant_name : "Verity";

  return (
    <div className="mb-4 flex items-center gap-2.5 px-2 pt-1">
      {logo ? (
        // Decorative: the name beside it says whose workspace this is.
        <img
          src={logo}
          alt=""
          className="h-8 w-auto max-w-[6.5rem] shrink-0 object-contain"
        />
      ) : (
        <BrandMark size={32} />
      )}
      <span className="min-w-0 truncate font-display text-heading-sm text-text-primary">
        {name}
      </span>
    </div>
  );
}
