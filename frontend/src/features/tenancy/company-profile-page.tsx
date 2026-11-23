import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ErrorBanner,
  ErrorState,
  Icon,
  Skeleton,
  TextField,
  useToast,
} from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { ProfileQuestions } from "@/features/tenancy/profile-questions";
import { SmtpSettings } from "@/features/tenancy/smtp-settings";
import type { CompanyProfile } from "@/lib/api/types";

// Industry, size, headquarters and "frameworks in scope" moved to the typed questions below
// (guided onboarding PR-1). Their old free text values show there as hints until answered.
type FormValues = {
  legal_name: string;
  display_name: string;
  registration_number: string;
  registered_address: string;
  domain: string;
  website: string;
  privacy_policy_url: string;
  terms_url: string;
};

const FIELDS = Object.keys({
  legal_name: 0,
  display_name: 0,
  registration_number: 0,
  registered_address: 0,
  domain: 0,
  website: 0,
  privacy_policy_url: 0,
  terms_url: 0,
} satisfies Record<keyof FormValues, number>) as (keyof FormValues)[];

function toForm(profile: CompanyProfile): FormValues {
  return Object.fromEntries(
    FIELDS.map((key) => [key, profile[key] ?? ""]),
  ) as FormValues;
}

export function CompanyProfilePage() {
  const { principal, refreshPrincipal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = principal?.permissions.includes("tenant:manage");

  const query = useQuery({
    queryKey: ["company-profile", principal?.tenant_id],
    queryFn: () => tenantApi.getCompanyProfile(),
  });

  const form = useForm<FormValues>({
    // `values` re-syncs the form when the profile loads / refetches.
    values: query.data ? toForm(query.data) : undefined,
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => tenantApi.updateCompanyProfile(values),
    onSuccess: (updated) => {
      queryClient.setQueryData(
        ["company-profile", principal?.tenant_id],
        updated,
      );
      form.reset(toForm(updated));
      // The topbar reads the workspace name off the cached principal, which the
      // session token does not carry — without this it keeps the old name until
      // the next sign-in.
      void refreshPrincipal();
      toast({ title: "Company profile saved", tone: "success" });
    },
  });

  const alertRef = useAlertFocus(mutation.isError);

  if (query.isLoading) {
    return (
      <div className="max-w-[820px]">
        <Skeleton className="h-[420px] w-full rounded-lg" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="max-w-[820px]">
        <ErrorState
          title="Couldn’t load your company profile"
          description={
            query.error instanceof ApiError
              ? query.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-[820px]">
      <h2 className="font-display text-heading-sm text-text-primary">
        Company profile
      </h2>
      <p className="mb-5 mt-1 text-body-md text-text-secondary">
        Answer once. Your scope, documents and the rules we show you read from here.{" "}
        <Link to="/regulations" className="text-text-link">
          See which laws may apply
        </Link>
      </p>

      {query.data ? (
        <div className="mb-8">
          <ProfileQuestions profile={query.data} canManage={Boolean(canManage)} />
        </div>
      ) : null}

      <h3 className="mb-3 font-display text-title-md text-text-primary">Legal details</h3>

      <form
        onSubmit={(e) =>
          void form.handleSubmit((values) => mutation.mutate(values))(e)
        }
        className="rounded-lg border border-border bg-surface-primary p-5 sm:p-6"
      >
        {!canManage ? (
          <div className="mb-5 flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2.5 text-body-sm text-text-secondary">
            <Icon name="shield" className="size-4 shrink-0 text-text-subtle" />
            You have view-only access. Ask an Admin to edit the company profile.
          </div>
        ) : null}

        {mutation.isError ? (
          <ErrorBanner ref={alertRef} className="mb-5" title="Couldn’t save">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : "The request didn’t reach the server. Check your connection and try again."}
          </ErrorBanner>
        ) : null}

        <fieldset disabled={!canManage} className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Company name"
            placeholder="Acme Inc."
            {...form.register("display_name")}
          />
          <TextField
            label="Legal / registered name"
            placeholder="Acme Corporation Ltd."
            {...form.register("legal_name")}
          />
          <TextField
            label="Registration number"
            optional
            placeholder="e.g. 12345678"
            {...form.register("registration_number")}
          />
          <TextField
            label="Registered address"
            optional
            placeholder="Street, city, postcode, country"
            {...form.register("registered_address")}
          />
          <TextField
            label="Primary domain"
            optional
            placeholder="acme.com"
            {...form.register("domain")}
          />
          <TextField
            label="Website"
            optional
            type="url"
            placeholder="https://acme.com"
            {...form.register("website")}
          />
          <TextField
            label="Privacy policy URL"
            optional
            type="url"
            placeholder="https://acme.com/privacy"
            {...form.register("privacy_policy_url")}
          />
          <TextField
            label="Terms and conditions URL"
            optional
            type="url"
            placeholder="https://acme.com/terms"
            {...form.register("terms_url")}
          />
        </fieldset>

        {canManage ? (
          <div className="mt-6 flex justify-end">
            <Button
              type="submit"
              size="lg"
              loading={mutation.isPending}
              disabled={!form.formState.isDirty}
            >
              Save details
              <Icon name="check" className="size-4" />
            </Button>
          </div>
        ) : null}
      </form>

      <div className="mt-8">
        <SmtpSettings canManage={Boolean(canManage)} />
      </div>
    </div>
  );
}
