import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ErrorBanner,
  ErrorState,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  TextField,
  useToast,
} from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { SmtpSettings } from "@/features/tenancy/smtp-settings";
import type { CompanyProfile } from "@/lib/api/types";

const INDUSTRIES = [
  "Financial Services",
  "Healthcare",
  "Technology",
  "Manufacturing",
  "Retail",
  "Energy",
  "Government",
  "Education",
  "Other",
];
const COMPANY_SIZES = ["1-50", "51-200", "201-500", "501-1000", "1000+"];

type FormValues = {
  legal_name: string;
  display_name: string;
  registration_number: string;
  industry: string;
  company_size: string;
  domain: string;
  website: string;
  headquarters: string;
  description: string;
  regulatory_scope: string;
  privacy_policy_url: string;
  terms_url: string;
};

const FIELDS = Object.keys({
  legal_name: 0,
  display_name: 0,
  registration_number: 0,
  industry: 0,
  company_size: 0,
  domain: 0,
  website: 0,
  headquarters: 0,
  description: 0,
  regulatory_scope: 0,
  privacy_policy_url: 0,
  terms_url: 0,
} satisfies Record<keyof FormValues, number>) as (keyof FormValues)[];

function toForm(profile: CompanyProfile): FormValues {
  return Object.fromEntries(
    FIELDS.map((key) => [key, profile[key] ?? ""]),
  ) as FormValues;
}

export function CompanyProfilePage() {
  const { principal } = useAuth();
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

  const industry = form.watch("industry");
  const companySize = form.watch("company_size");
  const textareaClass =
    "w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-md text-text-primary outline-none transition-colors placeholder:text-text-subtle focus:border-action-accent focus:ring-2 focus:ring-action-accent/15 disabled:cursor-not-allowed disabled:opacity-60";

  return (
    <div className="max-w-[820px]">
      <h2 className="font-display text-heading-sm text-text-primary">
        Company profile
      </h2>
      <p className="mb-5 mt-1 text-body-md text-text-secondary">
        Tell us about your organisation. These details feed reports, evidence
        and generated documents going forward.
      </p>

      <form
        onSubmit={(e) =>
          void form.handleSubmit((values) => mutation.mutate(values))(e)
        }
        className="rounded-lg border border-border bg-surface-primary p-5 sm:p-6"
      >
        {!canManage ? (
          <div className="mb-5 flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2.5 text-body-sm text-text-secondary">
            <Icon name="shield" className="size-4 shrink-0 text-text-subtle" />
            You have view-only access — ask an Admin to edit the company profile.
          </div>
        ) : null}

        {mutation.isError ? (
          <ErrorBanner ref={alertRef} className="mb-5" title="Couldn’t save">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : "The request didn’t reach the server — check your connection and try again."}
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
          <SelectField label="Industry" optional>
            <Select
              value={industry}
              onValueChange={(v) => form.setValue("industry", v)}
              disabled={!canManage}
            >
              <SelectTrigger aria-label="Industry" />
              <SelectContent>
                {INDUSTRIES.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <SelectField label="Company size" optional>
            <Select
              value={companySize}
              onValueChange={(v) => form.setValue("company_size", v)}
              disabled={!canManage}
            >
              <SelectTrigger aria-label="Company size" />
              <SelectContent>
                {COMPANY_SIZES.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option} employees
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <TextField
            label="Headquarters"
            optional
            placeholder="City, Country"
            {...form.register("headquarters")}
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
          <div className="sm:col-span-2">
            <label
              htmlFor="description"
              className="mb-1 block font-sans text-label-sm text-text-secondary"
            >
              What you do{" "}
              <span className="text-text-subtle">(optional)</span>
            </label>
            <textarea
              id="description"
              rows={3}
              className={textareaClass}
              placeholder="A short description of your business and what you sell."
              {...form.register("description")}
            />
          </div>
          <div className="sm:col-span-2">
            <TextField
              label="Frameworks in scope"
              optional
              placeholder="SOC 2, ISO 27001, GDPR"
              {...form.register("regulatory_scope")}
            />
          </div>
          <TextField
            label="Privacy policy URL"
            optional
            type="url"
            placeholder="https://acme.com/privacy"
            {...form.register("privacy_policy_url")}
          />
          <TextField
            label="Terms & conditions URL"
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
              Save profile
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
